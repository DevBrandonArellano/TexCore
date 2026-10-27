# Dockerfile para reporting_excel. Solo formatea a Excel/CSV las filas que le envía el
# backend: no se conecta a la base de datos, así que no lleva driver ODBC.
FROM python:3.12.15-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

# Usuario sin privilegios (UID fijo para que los volúmenes conserven el dueño).
# /data guarda la auditoría local (AUDIT_DB_PATH=/data/logs.db).
RUN useradd --uid 10001 --create-home appuser && mkdir -p /data && chown appuser:appuser /data

WORKDIR /app

COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copiamos código y pruebas. pytest.ini es necesario incluso en la imagen de
# runtime: sin él, "asyncio_mode = auto" no se aplica y pytest falla a
# recolectar todos los tests async con "async def functions are not natively
# supported" (encontrado corriendo la suite dentro del contenedor durante la
# auditoría de performance 2026-08-31).
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser tests/ ./tests/
COPY --chown=appuser:appuser pytest.ini .

ENV PYTHONPATH=/app

USER appuser

EXPOSE 8002

# Salud: /health responde 200 aunque Django no esté («degraded»): el servicio
# solo formatea archivos y no depende del backend para estar vivo.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=4).status == 200 else 1)"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
