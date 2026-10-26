from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Doctor
from schemas import DoctorOut

router = APIRouter(prefix="/api/v1/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorOut])
async def list_doctors(db: AsyncSession = Depends(get_db)):
    """Médicos veterinarios activos con especialidad y número de box."""
    rows = (
        (await db.execute(select(Doctor).where(Doctor.is_active.is_(True)).order_by(Doctor.id)))
        .unique()
        .scalars()
        .all()
    )
    return [
        DoctorOut(
            id=d.id, full_name=d.user.full_name, specialty=d.specialty, box_number=d.box_number
        )
        for d in rows
    ]
