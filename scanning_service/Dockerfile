# --- Stage 1: Build wheel files ---
# Sin driver ODBC: el servicio valida lotes por la Internal API de Django, no por la base.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# --- Stage 2: Final production image ---
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user and set the working directory
RUN useradd --create-home appuser && mkdir -p /data
WORKDIR /home/appuser/app

# Copy wheel files from the builder stage
COPY --from=builder /app/wheels /wheels

# Copy the application code
COPY . .

# Set ownership
RUN chown -R appuser:appuser /home/appuser/app /wheels /data

# Switch to the non-root user
USER appuser


# Install dependencies from wheels
RUN pip install --no-cache --user /wheels/*

# Add the user's local bin directory to the PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Expose the port
EXPOSE 8000

# Salud: /health responde 503 si la Internal API de Django no contesta; el
# escaneo no funciona sin ella. start-period cubre las migraciones del backend.
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --start-interval=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
