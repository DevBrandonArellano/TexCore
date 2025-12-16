# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables to make Python run better inside Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy and make wait-for-it.sh executable
COPY wait-for-it.sh /usr/local/bin/wait-for-it.sh
RUN chmod +x /usr/local/bin/wait-for-it.sh

# Install system dependencies required for mssql-django
# First, add Microsoft's official repository for the ODBC driver
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg
RUN curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Install the ODBC driver itself and related tools
# The 'ACCEPT_EULA' is required for unattended installation
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18
# Install the unixodbc developer package, which provides headers for compiling mssql-django
RUN apt-get install -y unixodbc-dev

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory and file with appropriate permissions
RUN mkdir -p /app/logs && touch /app/logs/backend.log && chmod -R 775 /app/logs

# Copy the rest of the backend application's code into the container
COPY . .
