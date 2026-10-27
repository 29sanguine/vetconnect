from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_role
from database import get_db
from models import Appointment, MedicalRecord, User, Doctor
from schemas import MedicalRecordUpsert, MedicalRecordOut

router = APIRouter(prefix="/api/v1/medical-records", tags=["medical-records"])


@router.get("/{appointment_id}", response_model=MedicalRecordOut)
async def get_medical_record(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("VETERINARIO", "ADMIN")),
):
    """Obtiene la ficha clínica de una cita específica (VETERINARIO o ADMIN)."""
    medical_record = await db.execute(
        select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
    ).scalar_one_or_none()
    
    if medical_record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ficha clínica no encontrada para esta cita.")
    
    return medical_record


@router.put("/{appointment_id}", response_model=MedicalRecordOut)
async def upsert_medical_record(
    appointment_id: int,
    data: MedicalRecordUpsert,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("VETERINARIO")),
):
    """Crea o actualiza la ficha clínica de una cita (VETERINARIO solo puede modificar citas de sus pacientes)."""
    appointment = await db.execute(
        select(Appointment)
        .join(User, Appointment.tutor_id == User.id)
        .where(Appointment.id == appointment_id)
    ).scalar_one_or_none()
    
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")
    
    doctor = await db.execute(
        select(User).join(Doctor, Appointment.doctor_id == Doctor.id)
        .where(Appointment.id == appointment_id)
    ).scalar_one_or_none()
    
    if doctor is None or doctor.id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes modificar esta ficha clínica.")
    
    # Buscar ficha clínica existente
    medical_record = await db.execute(
        select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
    ).scalar_one_or_none()
    
    if medical_record is None:
        medical_record = MedicalRecord(appointment_id=appointment_id, **data.model_dump())
        db.add(medical_record)
    else:
        # Actualizar campos existentes
        for key, value in data.model_dump().items():
            setattr(medical_record, key, value)
    
    # Actualizar estado de la cita a COMPLETED si estaba CONFIRMED o ARRIVED
    if appointment.status in ["CONFIRMED", "ARRIVED"]:
        appointment.status = "COMPLETED"
    
    await db.commit()
    await db.refresh(medical_record)
    
    return medical_record