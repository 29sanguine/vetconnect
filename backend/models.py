"""Modelos SQLAlchemy 2.0. La regla anti-solapamiento vive en la BD (EXCLUDE + GiST)."""
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN','RECEPCIONISTA','VETERINARIO','TUTOR')", name="ck_user_role"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    specialty: Mapped[str] = mapped_column(String(100))
    box_number: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    user: Mapped[User] = relationship(lazy="joined")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("status IN ('CONFIRMED','CANCELLED')", name="ck_appointment_status"),
        CheckConstraint("end_time > start_time", name="ck_appointment_range"),
        # Mismo doctor + rangos que se superponen (&&) + estado CONFIRMED => violación.
        # Las citas CANCELLED quedan fuera (WHERE), así el bloque se puede volver a reservar.
        ExcludeConstraint(
            ("doctor_id", "="),
            (text("tsrange(start_time, end_time)"), "&&"),
            using="gist",
            where=text("status = 'CONFIRMED'"),
            name="no_overlapping_confirmed_appointments",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="CONFIRMED", server_default="CONFIRMED")
    # TIMESTAMP sin zona: se guarda la hora local de la clínica (America/Santiago).
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False))
    end_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False))
