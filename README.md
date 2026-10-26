# VetConnect Maule · Módulo de agendamiento y autenticación

Backend FastAPI + PostgreSQL 15 y frontend Angular 17+ con Tailwind. Las colisiones de horario
se impiden **en la base de datos** con una restricción `EXCLUDE USING gist` sobre
`tsrange(start_time, end_time)`: aunque dos reservas lleguen al mismo milisegundo, PostgreSQL
acepta una y rechaza la otra, y la API responde `409 Conflict`.

## Requisitos
Python 3.11+, Node 18.13+ (o 20), Angular CLI 17+ (`npm i -g @angular/cli`), Docker (o un PostgreSQL 15 propio).

## 1. Base de datos
```bash
docker compose up -d          # PostgreSQL 15 en localhost:5432 (db: vetconnect)
```
Sin Docker: crea la base `vetconnect` y ajusta `DATABASE_URL` (ver `backend/.env.example`).
La extensión `btree_gist` y las tablas se crean al iniciar la API; `backend/schema.sql` es el
equivalente en SQL puro. El usuario de PostgreSQL necesita permiso para crear extensiones.

## 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vetconnect
export SECRET_KEY=una-clave-larga-y-aleatoria
python seed.py                                       # usuarios y médicos iniciales
uvicorn main:app --reload --port 8000
```
Documentación interactiva: http://localhost:8000/docs

| Usuario | Contraseña | Rol |
|---|---|---|
| admin@vetconnect.cl | Admin123! | ADMIN |
| tutor@vetconnect.cl | Tutor123! | TUTOR |
| vet@vetconnect.cl | Vet123! | VETERINARIO |

(`vet2@vetconnect.cl` se agrega para tener dos médicos en el selector.) **Cambia estas claves antes de producción.**

## 3. Frontend
Se crea el proyecto con el CLI y luego se copian los archivos de esta carpeta:
```bash
# desde la raíz del proyecto (donde está /backend)
ng new vetconnect-web --standalone --routing --style=css --ssr=false --skip-git
cd vetconnect-web
npm install -D tailwindcss@3 postcss autoprefixer

# copia los archivos entregados, sobrescribiendo los generados
cp -r ../frontend/src/* src/
cp ../frontend/tailwind.config.js .
rm -f src/app/app.component.html src/app/app.component.css src/app/app.component.spec.ts

ng serve                                            # http://localhost:4200
```
Si tu CLI genera `app.config.ts`/`app.routes.ts` distintos, los archivos copiados los reemplazan.
Si cambias la URL del backend, edita `src/app/api.config.ts`.

## 4. Prueba de concurrencia
Con la API levantada y el seed ejecutado:
```bash
cd backend
python test_concurrency.py --n 5
```
Lanza 5 reservas simultáneas del mismo bloque y verifica: exactamente un `201`, el resto `409`,
y tiempo total ≤ 3 s. Elige un bloque libre cada vez, así que se puede repetir.

## Notas de diseño
- **Sin "SELECT y luego INSERT"**: esa verificación tendría una condición de carrera. Se inserta directo y se captura `IntegrityError` (SQLSTATE `23P01`).
- **Bloques contiguos**: `tsrange` usa límites `[)`, por lo que 09:00–09:30 y 09:30–10:00 no chocan.
- **Citas canceladas** quedan fuera de la restricción (`WHERE status = 'CONFIRMED'`) y el bloque vuelve a estar disponible.
- **Horas**: se guardan como `TIMESTAMP` sin zona en hora de la clínica (America/Santiago).
- **Box**: la restricción cubre al médico. Si cada box lo comparten varios médicos, se agrega una segunda `EXCLUDE` sobre `box_number` (requiere guardar el box en `appointments`).
- **JWT en `localStorage`** cumple lo pedido, pero es accesible a scripts; para producción conviene una cookie `HttpOnly`.
