#!/usr/bin/env bash
# =============================================================================
# TexCore — Harness reproducible de pruebas backend (Django + SQL Server)
#
# Resuelve los problemas detectados al correr tests fuera de CI:
#   1. Host sin driver ODBC / pyodbc no compilable  -> imagen Docker dedicada
#      (texcore-django-test: python:3.12-bookworm + msodbcsql18 + unixodbc-dev).
#   2. Conectividad de red: el contenedor de tests y el de SQL Server comparten
#      red Docker; el contenedor SQL se referencia por alias, no por 127.0.0.1.
#
# Uso:
#   bash scripts/run_backend_tests.sh                 # toda la suite + cobertura
#   bash scripts/run_backend_tests.sh gestion.tests   # subconjunto de tests
#
# Variables sobreescribibles por entorno:
#   DB_PASSWORD (def. CI_Pass1234!), DB_NAME (def. texcore_ci),
#   KEEP_DB=1 para conservar el contenedor SQL al terminar.
# =============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
IMAGE="texcore-django-test"
DOCKERFILE="docker/Dockerfile.django-test"
SQL_CONTAINER="texcore-sqltest"
NETWORK="texcore-test-net"
DB_PASSWORD="${DB_PASSWORD:-CI_Pass1234!}"
DB_NAME="${DB_NAME:-texcore_ci}"
TEST_LABELS="${*:-gestion inventory internal_api}"

# Claves RSA internas (JWT servicio-a-servicio) — requeridas por reporting_proxy
# y el internal_api. Se leen de .env.test (valor en una línea con '\n' literales).
_extract_env() { grep "^$1=" .env.test 2>/dev/null | cut -d= -f2- | sed 's/^"//; s/"$//'; }
INTERNAL_JWT_PRIVATE_KEY="$(_extract_env INTERNAL_JWT_PRIVATE_KEY)"
INTERNAL_JWT_PUBLIC_KEY="$(_extract_env INTERNAL_JWT_PUBLIC_KEY)"

echo "==> TexCore backend tests"
echo "    Proyecto:   $PROJECT_DIR"
echo "    Labels:     $TEST_LABELS"

# ---------------------------------------------------------------------------
# 1. Imagen de test con ODBC (build idempotente)
# ---------------------------------------------------------------------------
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "==> Construyendo imagen $IMAGE ..."
  docker build -f "$DOCKERFILE" -t "$IMAGE" .
fi

# ---------------------------------------------------------------------------
# 2. Red dedicada
# ---------------------------------------------------------------------------
docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK" >/dev/null

# ---------------------------------------------------------------------------
# 3. SQL Server de test
# ---------------------------------------------------------------------------
if ! docker ps --format '{{.Names}}' | grep -q "^${SQL_CONTAINER}$"; then
  echo "==> Levantando SQL Server de test ($SQL_CONTAINER) ..."
  docker rm -f "$SQL_CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$SQL_CONTAINER" --network "$NETWORK" \
    -e "ACCEPT_EULA=Y" \
    -e "MSSQL_SA_PASSWORD=${DB_PASSWORD}" \
    -e "MSSQL_PID=Developer" \
    mcr.microsoft.com/mssql/server:2022-latest >/dev/null
else
  # Garantiza que esté en la red correcta
  docker network connect "$NETWORK" "$SQL_CONTAINER" >/dev/null 2>&1 || true
fi

cleanup() {
  if [ "${KEEP_DB:-0}" != "1" ]; then
    echo "==> Limpiando contenedor SQL de test ..."
    docker rm -f "$SQL_CONTAINER" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 4. Ejecutar tests + cobertura dentro del contenedor de test
# ---------------------------------------------------------------------------
echo "==> Ejecutando suite ..."
docker run --rm --network "$NETWORK" \
  -v "$PROJECT_DIR":/app -w /app \
  -e DJANGO_SETTINGS_MODULE="TexCore.settings_test" \
  -e DEBUG="0" \
  -e SECRET_KEY="ci-only-secret-key-not-for-production-xxxxxxxxxxxxxxxx" \
  -e CORS_ALLOWED_ORIGINS="http://localhost:3000" \
  -e CSRF_TRUSTED_ORIGINS="http://localhost:3000" \
  -e DB_ENGINE="mssql" \
  -e DB_NAME="$DB_NAME" \
  -e DB_USER="sa" \
  -e DB_PASSWORD="$DB_PASSWORD" \
  -e DB_HOST="$SQL_CONTAINER" \
  -e DB_PORT="1433" \
  -e DB_DRIVER="ODBC Driver 18 for SQL Server" \
  -e INTERNAL_JWT_PRIVATE_KEY="$INTERNAL_JWT_PRIVATE_KEY" \
  -e INTERNAL_JWT_PUBLIC_KEY="$INTERNAL_JWT_PUBLIC_KEY" \
  -e REPORTING_SERVICE_URL="http://reporting-excel-test:8002" \
  "$IMAGE" bash -c '
    set -e
    pip install -q -r requirements.txt
    echo "--- Esperando a que SQL Server acepte conexiones ---"
    for i in $(seq 1 40); do
      if python3 -c "import pyodbc,os; pyodbc.connect(\"DRIVER=ODBC Driver 18 for SQL Server;SERVER=\"+os.environ[\"DB_HOST\"]+\",1433;UID=sa;PWD=\"+os.environ[\"DB_PASSWORD\"]+\";Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=3\").close()" 2>/dev/null; then
        echo "SQL Server listo (intento $i)"; break
      fi
      [ "$i" -eq 40 ] && { echo "ERROR: SQL Server no respondió"; exit 1; }
      sleep 3
    done
    echo "--- coverage run manage.py test '"$TEST_LABELS"' ---"
    TEST_RC=0
    coverage run --rcfile=.coveragerc manage.py test '"$TEST_LABELS"' --verbosity=2 || TEST_RC=$?
    echo "--- coverage report ---"
    coverage report --rcfile=.coveragerc || true
    coverage html --rcfile=.coveragerc || true
    exit $TEST_RC
  '
