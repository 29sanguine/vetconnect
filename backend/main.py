"""VetConnect Maule · API de agendamiento.  Ejecutar: uvicorn main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import models  # noqa: F401  (registra las tablas en Base.metadata)
from database import Base, engine, get_db
from routers import appointment_router, auth_router, doctor_router, medical_record_router
from auth import require_role
from models import User, Doctor, Appointment, MedicalRecord


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await conn.run_sync(Base.metadata.create_all)
        # Actualización segura del constraint de estado sin comillas conflictivas
        try:
            await conn.execute(text(
                "ALTER TABLE appointments DROP CONSTRAINT IF EXISTS ck_appointment_status"
            ))
            await conn.execute(text(
                "ALTER TABLE appointments ADD CONSTRAINT ck_appointment_status CHECK (status IN ('CONFIRMED', 'ARRIVED', 'COMPLETED', 'CANCELLED'))"
            ))
            await conn.commit()
        except Exception:
            pass # Si ya existe o la tabla se crea limpia, continúa sin problemas
    yield
    await engine.dispose()


app = FastAPI(title="VetConnect Maule", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(doctor_router.router)
app.include_router(appointment_router.router)
app.include_router(medical_record_router.router)


@app.get("/api/v1/medical-records/{appointment_id}/pdf", status_code=200)
async def generate_prescription_pdf(
    appointment_id: int,
    user: User = Depends(require_role("VETERINARIO", "TUTOR", "ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Genera PDF de receta médica para una cita (VETERINARIO, TUTOR o ADMIN pueden acceder)."""
    from fpdf import FPDF
    from io import BytesIO
    
    # Obtener la ficha clínica
    medical_record = await db.execute(
        select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
    ).scalar_one_or_none()
    
    if medical_record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay ficha clínica para esta cita.")
    
    # Obtener datos de la cita
    appointment = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    ).scalar_one_or_none()
    
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cita no encontrada.")
    
    # Obtener datos del veterinario
    doctor = await db.execute(
        select(Doctor).where(Doctor.id == appointment.doctor_id)
    ).scalar_one_or_none()
    
    if doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor no encontrado.")
    
    # Obtener datos del tutor
    tutor = await db.execute(
        select(User).where(User.id == appointment.tutor_id)
    ).scalar_one_or_none()
    
    if tutor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor no encontrado.")
    
    # Generar PDF usando fpdf2
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "CLÍNICA VETERINARIA SAN FRANCISCO", 0, 1, "C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, "Talca - Receta Médica Veterinaria", 0, 1, "C")
    pdf.ln(10)
    
    # Número de receta
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 5, f"Receta #{appointment_id:06d} - {appointment.start_time.strftime('%Y-%m-%d %H:%M')}", 0, 1, "R")
    pdf.ln(5)
    
    # Información del paciente
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DATOS DEL PACIENTE:", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Nombre: {medical_record.pet_name}", 0, 1)
    pdf.cell(0, 6, f"Especie: {medical_record.species}", 0, 1)
    pdf.cell(0, 6, f"Peso: {medical_record.weight_kg} kg", 0, 1)
    pdf.ln(5)
    
    # Información del veterinario
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "VETERINARIO:", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Dr(a). {doctor.user.full_name}", 0, 1)
    pdf.cell(0, 6, f"Especialidad: {doctor.specialty}", 0, 1)
    pdf.cell(0, 6, f"Box: {doctor.box_number}", 0, 1)
    pdf.ln(5)
    
    # Información del tutor
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "TUTOR:", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Sr(a). {tutor.full_name}", 0, 1)
    pdf.cell(0, 6, f"Email: {tutor.email}", 0, 1)
    pdf.ln(5)
    
    # Historia clínica
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "HISTORIA CLÍNICA:", 0, 1)
    pdf.set_font("Arial", "", 11)
    
    # Antecedentes
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Antecedentes:", 0, 1)
    pdf.set_font("Arial", "", 10)
    antecedentes_lines = pdf.multi_cell(0, 5, medical_record.antecedents, border=0, ln=2)
    
    # Vacunas
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Vacunas:", 0, 1)
    pdf.set_font("Arial", "", 10)
    vacunas_lines = pdf.multi_cell(0, 5, medical_record.vaccines, border=0, ln=2)
    
    # Diagnóstico
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Diagnóstico:", 0, 1)
    pdf.set_font("Arial", "", 10)
    diagnostico_lines = pdf.multi_cell(0, 5, medical_record.diagnosis, border=0, ln=2)
    
    # Tratamiento
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Tratamiento:", 0, 1)
    pdf.set_font("Arial", "", 10)
    tratamiento_lines = pdf.multi_cell(0, 5, medical_record.treatment, border=0, ln=2)
    
    # Prescripción
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "PRESCRIPCIÓN:", 0, 1)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, medical_record.prescription)
    pdf.ln(5)
    
    # Pie de página
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 5, "Esta receta es válida por 30 días desde su emisión.", 0, 1, "C")
    pdf.cell(0, 5, "Generado electrónicamente - Clínica Veterinaria San Francisco", 0, 1, "C")
    
    # Obtener bytes del PDF
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    
    # Devolver como respuesta con headers apropiados
    response = Response(content=pdf_bytes, media_type="application/pdf")
    response.headers["Content-Disposition"] = f"inline; filename=receta_cita_{appointment_id}.pdf"
    
    return response


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
