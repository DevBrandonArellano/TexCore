FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

# Bibliotecas que WeasyPrint necesita para renderizar PDF (Pango, Cairo, GDK-Pixbuf)
# y fuentes. Todas las dependencias de Python llegan como wheels: sin compiladores.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-dejavu-core \
    fontconfig \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios (UID fijo para que los volúmenes conserven el dueño).
# /data guarda la auditoría local (AUDIT_DB_PATH=/data/logs.db).
RUN useradd --uid 10001 --create-home appuser && mkdir -p /data && chown appuser:appuser /data

WORKDIR /app

COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8001

# Salud: /health responde 503 si faltan las plantillas de etiquetas.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4).status == 200 else 1)"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
