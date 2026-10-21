# Usa la imagen oficial de Microsoft SQL Server como base
FROM mcr.microsoft.com/mssql/server:2022-CU27-GDR1-ubuntu-22.04@sha256:cf8f0ab2ebe61feec2eed2629061a07d247f791c2a8ddda74a4ac9f06a291718

# Cambia al usuario root para instalar paquetes
USER root

# Instala las dependencias del sistema necesarias para el driver ODBC y las herramientas
RUN apt-get update && apt-get install -y curl gnupg

# Añade el repositorio oficial de Microsoft para el driver ODBC
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg
RUN curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Instala el paquete mssql-tools18
# 'ACCEPT_EULA' es obligatorio para la instalación desatendida
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y mssql-tools18

# Vuelve al usuario mssql por defecto
USER mssql
