#!/usr/bin/env bash
# Envoltorio para evidencia_sprints.py --python-backend: corre "python -m pytest ..." dentro de la
# imagen con ODBC 18 contra un SQL Server 2022 desechable (mismo esquema que run_backend_tests.sh).
set -euo pipefail
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; cd "$P"
NET=texcore-test-net; SQL=texcore-sqltest; PW='CI_Pass1234!'
_k() { grep "^$1=" .env.test | cut -d= -f2- | sed 's/^"//; s/"$//'; }
docker network inspect $NET >/dev/null 2>&1 || docker network create $NET >/dev/null
docker rm -f $SQL >/dev/null 2>&1 || true
docker run -d --name $SQL --network $NET -e ACCEPT_EULA=Y -e "MSSQL_SA_PASSWORD=$PW" -e MSSQL_PID=Developer mcr.microsoft.com/mssql/server:2022-latest >/dev/null
trap 'docker rm -f $SQL >/dev/null 2>&1 || true' EXIT
ARGS=$(printf '%q ' "$@")
docker run --rm --network $NET -v "$P":"$P" -w "$P" \
  -e DJANGO_SETTINGS_MODULE=TexCore.settings_test -e DEBUG=0 \
  -e SECRET_KEY=ci-only-secret-key-not-for-production-xxxxxxxxxxxxxxxx \
  -e CORS_ALLOWED_ORIGINS=http://localhost:3000 -e CSRF_TRUSTED_ORIGINS=http://localhost:3000 \
  -e DB_ENGINE=mssql -e DB_NAME=texcore_ci -e DB_USER=sa -e "DB_PASSWORD=$PW" -e DB_HOST=$SQL -e DB_PORT=1433 \
  -e "DB_DRIVER=ODBC Driver 18 for SQL Server" \
  -e "INTERNAL_JWT_PRIVATE_KEY=$(_k INTERNAL_JWT_PRIVATE_KEY)" -e "INTERNAL_JWT_PUBLIC_KEY=$(_k INTERNAL_JWT_PUBLIC_KEY)" \
  -e REPORTING_SERVICE_URL=http://reporting-excel-test:8002 \
  texcore-django-test bash -c "
    set -e; pip install -q -r requirements.txt pytest pytest-django
    for i in \$(seq 1 40); do python3 -c \"import pyodbc,os; pyodbc.connect('DRIVER=ODBC Driver 18 for SQL Server;SERVER='+os.environ['DB_HOST']+',1433;UID=sa;PWD='+os.environ['DB_PASSWORD']+';Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=3').close()\" 2>/dev/null && break; sleep 3; done
    python $ARGS"
