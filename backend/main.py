"""VetConnect Maule · API de agendamiento.  Ejecutar: uvicorn main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import models  # noqa: F401  (registra las tablas en Base.metadata)
from database import Base, engine
from routers import appointment_router, auth_router, doctor_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        # Necesaria para mezclar "=" (entero) con "&&" (rango) en un índice GiST.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await conn.run_sync(Base.metadata.create_all)
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


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
