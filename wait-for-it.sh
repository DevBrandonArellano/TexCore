#!/usr/bin/env bash
set -e
host="$DB_HOST"
user="$DB_USER"
password="$DB_PASSWORD"
port="$DB_PORT"

while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--" ]]; then
    shift
    break
  fi
  shift
done

until /opt/mssql-tools18/bin/sqlcmd -S "$host,$port" -U "$user" -P "$password" -C -N -Q 'SELECT 1' > /dev/null 2>&1; do
  >&2 echo "SQL Server is unavailable - sleeping"
  sleep 1
done

>&2 echo "SQL Server is up - executing command"
if [[ $# -gt 0 ]]; then
  exec "$@"
fi