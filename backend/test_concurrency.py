"""
Prueba de concurrencia: N tutores intentan reservar EXACTAMENTE el mismo bloque a la vez.
Esperado: 1 respuesta 201 y (N-1) respuestas 409, todo en <= 3 s.

Requisitos: API levantada y `python seed.py` ejecutado.
Uso:  python test_concurrency.py [--base-url http://localhost:8000] [--n 5]
"""
import argparse
import asyncio
import sys
import time
from datetime import date, timedelta

import httpx

LIMIT_SECONDS = 3.0


async def find_free_slot(client: httpx.AsyncClient, doctor_id: int) -> dict:
    """Busca el primer bloque libre en los próximos días hábiles (así el test es repetible)."""
    day = date.today()
    for _ in range(14):
        day += timedelta(days=1)
        if day.weekday() >= 5:
            continue
        r = await client.get("/api/v1/appointments/available-slots",
                             params={"doctor_id": doctor_id, "date": day.isoformat()})
        r.raise_for_status()
        if r.json():
            return r.json()[0]
    sys.exit("No hay bloques libres en los próximos 14 días.")


async def main(base_url: str, n: int) -> int:
    async with httpx.AsyncClient(base_url=base_url, timeout=15) as client:
        login = await client.post("/api/v1/auth/login",
                                  json={"email": "tutor@vetconnect.cl", "password": "Tutor123!"})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        doctors = (await client.get("/api/v1/doctors")).json()
        doctor_id = doctors[0]["id"]
        slot = await find_free_slot(client, doctor_id)
        payload = {"doctor_id": doctor_id, "start_time": slot["start_time"],
                   "end_time": slot["end_time"]}
        print(f"Médico {doctor_id} · bloque {slot['start_time']} → {slot['end_time']}")
        print(f"Lanzando {n} reservas simultáneas...\n")

        async def attempt(i: int):
            t0 = time.perf_counter()
            r = await client.post("/api/v1/appointments/reserve", json=payload, headers=headers)
            return i, r.status_code, time.perf_counter() - t0

        start = time.perf_counter()
        results = await asyncio.gather(*(attempt(i) for i in range(1, n + 1)))
        total = time.perf_counter() - start

    for i, code, dt in results:
        print(f"  petición #{i}: HTTP {code} en {dt * 1000:.0f} ms")
    codes = [c for _, c, _ in results]
    created, conflicts = codes.count(201), codes.count(409)

    print(f"\nTiempo total: {total:.3f} s (límite {LIMIT_SECONDS} s)")
    ok = created == 1 and conflicts == n - 1 and total <= LIMIT_SECONDS
    print(f"201 Created: {created} (esperado 1) · 409 Conflict: {conflicts} (esperado {n - 1})")
    print("RESULTADO: OK ✔" if ok else "RESULTADO: FALLÓ ✘")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--n", type=int, default=5, help="peticiones simultáneas (>= 2)")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.base_url, max(2, args.n))))
