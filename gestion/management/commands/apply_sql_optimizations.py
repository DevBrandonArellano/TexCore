"""
Aplica las optimizaciones DDL de SQL Server (RCSI, índices, CHECK constraints)
y los stored procedures de reporting (database/V2_*.sql, database/V3_*.sql)
usando la propia conexión de Django (pyodbc/mssql-django) en vez de `sqlcmd`.

Por qué existe: antes, V2/V3 solo se aplicaban a mano dentro de
scripts/deploy_production.sh vía `sqlcmd` — un binario que NO está instalado
en la imagen final del contenedor `web` (infrastructure/docker/Dockerfile.prod
solo instala el driver ODBC, no mssql-tools18). Cualquier despliegue que no
fuera exactamente ese script manual (un `docker-compose up` normal, CI, un
entorno nuevo) se quedaba sin las 21 stored procedures y las optimizaciones
de índices/RCSI. Este comando corre en cada arranque del contenedor
(entrypoint.sh, justo después de `migrate`), igual que las migraciones.

Ambos archivos SQL ya están escritos de forma idempotente (CREATE OR ALTER,
IF NOT EXISTS) — correr esto en cada arranque es seguro.

Usage: python manage.py apply_sql_optimizations
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

SQL_FILES = [
    'database/V2__optimize_sqlserver2022_texcore.sql',
    'database/V3__optimize_stored_procedures_texcore.sql',
    'database/V4__indices_reportes_carga_concurrente.sql',
]

# Separador de lotes T-SQL: 'GO' solo en su propia línea (case-insensitive),
# con espacio en blanco opcional alrededor — pyodbc no entiende 'GO', hay que
# partir el script y ejecutar cada lote por separado.
_GO_SEPARATOR = re.compile(r'^\s*GO\s*$', re.IGNORECASE | re.MULTILINE)


class Command(BaseCommand):
    help = 'Aplica optimizaciones DDL y stored procedures de SQL Server (database/V2_*.sql, V3_*.sql).'

    def handle(self, *args, **options):
        if connection.vendor != 'microsoft':
            self.stdout.write(
                f'Motor de BD "{connection.vendor}" no es SQL Server — '
                f'se omiten las optimizaciones DDL/stored procedures (no aplican en este entorno).'
            )
            return

        base_dir = Path(settings.BASE_DIR)
        for rel_path in SQL_FILES:
            sql_path = base_dir / rel_path
            if not sql_path.exists():
                raise CommandError(f'No se encontró el archivo SQL: {sql_path}')

            self.stdout.write(f'Aplicando {rel_path}...')
            sql_text = sql_path.read_text(encoding='utf-8')
            batches = [b.strip() for b in _GO_SEPARATOR.split(sql_text) if b.strip()]

            with connection.cursor() as cursor:
                for batch in batches:
                    cursor.execute(batch)

            self.stdout.write(self.style.SUCCESS(f'{rel_path} aplicado correctamente ({len(batches)} lotes).'))

        self.stdout.write(self.style.SUCCESS('=== OPTIMIZACIONES DE BASE DE DATOS APLICADAS ==='))
