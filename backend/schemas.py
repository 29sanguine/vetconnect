"""Esquemas Pydantic v2."""
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

CLINIC_TZ = ZoneInfo("America/Santiago")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    specialty: str
    box_number: int


class SlotOut(BaseModel):
    start_time: datetime
    end_time: datetime


class ReserveRequest(BaseModel):
    doctor_id: int
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time")
    @classmethod
    def to_clinic_naive(cls, v: datetime) -> datetime:
        """Si llega con zona horaria, se convierte a hora de la clínica y se descarta la zona."""
        if v.tzinfo is not None:
            v = v.astimezone(CLINIC_TZ).replace(tzinfo=None)
        return v


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_id: int
    tutor_id: int
    status: str
    start_time: datetime
    end_time: datetime
