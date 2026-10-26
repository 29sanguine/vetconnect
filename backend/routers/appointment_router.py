from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_role
from database import get_db
from models import Appointment, Doctor, User
from schemas import CLINIC_TZ, AppointmentOut, ReserveRequest, SlotOut

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

DAY_START = time(9, 0)
DAY_END = time(18, 0)
SLOT = timedelta(minutes=30)
CONFLICT_MSG = "El bloque horario seleccionado ya fue reservado por otro usuario."
EXCLUSION_VIOLATION = "23P01"  # SQLSTATE de PostgreSQL para EXCLUDE constraint


def _now_local() -> datetime:
    return datetime.now(CLINIC_TZ).replace(tzinfo=None)


@router.get("/available-slots", response_model=list[SlotOut])
async def available_slots(
    doctor_id: int = Query(...),
    date_: date = Query(..., alias="date", description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """Bloques de 30 min (09:00-18:00) que NO se solapan con citas confirmadas."""
    day_start = datetime.combine(date_, DAY_START)
    day_end = datetime.combine(date_, DAY_END)

    booked = (
        await db.execute(
            select(Appointment.start_time, Appointment.end_time).where(
                Appointment.doctor_id == doctor_id,
                Appointment.status == "CONFIRMED",
                Appointment.start_time < day_end,
                Appointment.end_time > day_start,
            )
        )
    ).all()

    now = _now_local()
    slots: list[SlotOut] = []
    cursor = day_start
    while cursor + SLOT <= day_end:
        slot_end = cursor + SLOT
        overlaps = any(cursor < b_end and slot_end > b_start for b_start, b_end in booked)
        if not overlaps and cursor > now:  # tampoco se ofrecen horas que ya pasaron
            slots.append(SlotOut(start_time=cursor, end_time=slot_end))
        cursor = slot_end
    return slots


@router.post("/reserve", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def reserve(
    data: ReserveRequest,
    db: AsyncSession = Depends(get_db),
    tutor: User = Depends(require_role("TUTOR")),
):
    # --- Validaciones de forma (400) ---
    if data.end_time <= data.start_time:
        raise HTTPException(400, "La hora de término debe ser posterior a la de inicio.")
    duration = data.end_time - data.start_time
    if duration % SLOT != timedelta(0) or data.start_time.minute not in (0, 30):
        raise HTTPException(400, "Las reservas deben ser en bloques de 30 minutos.")
    if (
        data.start_time.date() != data.end_time.date()
        or data.start_time.time() < DAY_START
        or data.end_time.time() > DAY_END
    ):
        raise HTTPException(400, "El horario de atención es de 09:00 a 18:00.")
    if data.start_time <= _now_local():
        raise HTTPException(400, "No se pueden reservar horas en el pasado.")

    doctor = await db.get(Doctor, data.doctor_id)
    if doctor is None or not doctor.is_active:
        raise HTTPException(404, "El médico veterinario no existe o no está activo.")

    # --- Inserción: la BD decide si hay colisión ---
    # No hacemos "SELECT y luego INSERT": eso tendría una carrera entre ambos pasos.
    # Se inserta directo y se deja que la restricción EXCLUDE sea la única fuente de verdad.
    appointment = Appointment(
        doctor_id=data.doctor_id,
        tutor_id=tutor.id,
        status="CONFIRMED",
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(appointment)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
        if sqlstate == EXCLUSION_VIOLATION or "no_overlapping_confirmed_appointments" in str(exc):
            raise HTTPException(status.HTTP_409_CONFLICT, CONFLICT_MSG)
        raise HTTPException(400, "No se pudo registrar la reserva.")
    return appointment
