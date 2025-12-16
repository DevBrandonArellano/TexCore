#!/usr/bin/env bash
# wait-for-it.sh - Waits for SQL Server to be available

set -e

# Use the healthcheck command from docker-compose.prod.yml db service
# host, user, password from env variables in the backend service
host="$DB_HOST"
user="$DB_USER"
password="$DB_PASSWORD"
port="$DB_PORT"

shift
cmd="$@"

# Using sqlcmd similar to how the healthcheck is defined
until /opt/mssql-tools18/bin/sqlcmd -S "$host,$port" -U "$user" -P "$password" -C -N -Q 'SELECT 1' > /dev/null 2>&1; do
  >&2 echo "SQL Server is unavailable - sleeping"
  sleep 1
done

>&2 echo "SQL Server is up - executing command"
exec "$@"