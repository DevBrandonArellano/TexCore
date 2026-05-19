"""
RUP — Artefacto: Migración de corrección
=========================================
Caso de Uso    : Fix infraestructura de tests en SQL Server
Patrón         : RunSQL con SQL dinámico para eliminar constraint auto-generado

Problema:
    La migración token_blacklist.0008_migrate_to_bigautofield intenta
    alterar la columna `id` de `token_blacklist_blacklistedtoken`.
    SQL Server genera automáticamente un unique constraint sobre `token_id`
    (OneToOneField → UQ__token_bl__CB3C9E16...) cuyo nombre varía por entorno.
    El driver mssql no puede alterar la columna mientras el constraint existe.

Solución:
    Eliminar el constraint dinámicamente antes de que corra 0008,
    y dejar que la migración lo recree correctamente.
"""
from django.db import migrations


DROP_UQ_TOKEN_ID = """
DECLARE @constraint_name NVARCHAR(256);
SELECT @constraint_name = kc.name
FROM sys.key_constraints kc
JOIN sys.tables t ON kc.parent_object_id = t.object_id
JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id
    AND kc.unique_index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id
    AND ic.column_id = c.column_id
WHERE t.name = 'token_blacklist_blacklistedtoken'
  AND c.name = 'token_id'
  AND kc.type = 'UQ';

IF @constraint_name IS NOT NULL
BEGIN
    EXEC('ALTER TABLE [token_blacklist_blacklistedtoken] DROP CONSTRAINT [' + @constraint_name + ']');
END
"""


class Migration(migrations.Migration):
    """
    Debe correr ANTES de token_blacklist.0008 para evitar el error:
    'The object UQ__token_bl__... is dependent on column token_id'
    """

    dependencies = [
        ("gestion", "0050_ordenproduccion_peso_neto_positivo"),
        ("token_blacklist", "0007_auto_20171017_2214"),
    ]

    # Esta migración es la nueva dependencia de 0008
    run_before = [
        ("token_blacklist", "0008_migrate_to_bigautofield"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_UQ_TOKEN_ID,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
