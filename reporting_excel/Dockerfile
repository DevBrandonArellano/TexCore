# Dockerfile para reporting_excel
FROM python:3.12-slim

# Instalar dependencias del sistema y driver de SQL Server
RUN apt-get update && \
    apt-get install -y curl apt-transport-https gnupg build-essential unixodbc-dev && \
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg && \
    curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copiamos código y pruebas. pytest.ini es necesario incluso en la imagen de
# runtime: sin él, "asyncio_mode = auto" no se aplica y pytest falla a
# recolectar todos los tests async con "async def functions are not natively
# supported" (encontrado corriendo la suite dentro del contenedor durante la
# auditoría de performance 2026-08-31).
COPY src/ ./src/
COPY tests/ ./tests/
COPY pytest.ini .

ENV PYTHONPATH=/app

EXPOSE 8002

# Salud: /health responde 200 aunque Django no esté («degraded»): el servicio
# solo formatea archivos y no depende del backend para estar vivo.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=4).status == 200 else 1)"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
