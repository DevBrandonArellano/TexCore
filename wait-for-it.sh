#!/usr/bin/env bash
# wait-for-it.sh - Waits for SQL Server to be available

set -e

# Use the healthcheck command from docker-compose.prod.yml db service
# host, user, password from env variables in the backend service
host="$DB_HOST"
user="$DB_USER"
password="$DB_PASSWORD"
port="$DB_PORT"

# Using python to check if the port is open
until python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1); s.connect(('$host', int($port))); s.close()" > /dev/null 2>&1; do
  >&2 echo "SQL Server is unavailable - sleeping"
  sleep 2
done

>&2 echo "SQL Server is up - proceeding with entrypoint script."