# Usa una imagen oficial de Python como imagen base
FROM python:3.12-slim

# Define variables de entorno para que Python funcione mejor dentro de Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala las dependencias del sistema necesarias para mssql-django
# Primero, añade el repositorio oficial de Microsoft para el driver ODBC
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg
RUN curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Instala el driver ODBC y las herramientas relacionadas
# 'ACCEPT_EULA' es obligatorio para la instalación desatendida
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18
# Instala el paquete de desarrollo unixodbc, que aporta las cabeceras para compilar mssql-django
RUN apt-get install -y unixodbc-dev

# Copia el archivo de requisitos para aprovechar la caché de capas de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el script de entrada y lo hace ejecutable
COPY ./infrastructure/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
