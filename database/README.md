# Base de Datos TexCore (Microsoft SQL Server 2022)

Contiene la infraestructura, contenedor Docker y scripts SQL de optimización y mantenimiento para el motor de base de datos **Microsoft SQL Server 2022**.

---

## 📁 Contenido del Directorio

### 🐳 Docker & Configuración
- `Dockerfile`: Imagen personalizada Linux (`mcr.microsoft.com/mssql/server:2022-latest`) con `mssql-tools18` (`sqlcmd`) preinstalado.
- `Dockerfile.windows`: Imagen alternativa para entornos Windows Server.

### 📜 Scripts SQL Consolidados
- `V2__optimize_sqlserver2022_texcore.sql`: **Script DDL de Optimización de Esquema e Índices (SQL Server 2022)**.
  - Activación de Read Committed Snapshot Isolation (`RCSI`).
  - Reglas de negocio textil nativas (`CHECK Constraints` para fundas, conos, baños y mermas).
  - Estrategia de Índices Filtrados, Covering (`INCLUDE`) y Columnstore Index (`ncci_movimiento_inventario`).
  - Mitigación de contención de latches `PAGELATCH_EX` (`OPTIMIZE_FOR_SEQUENTIAL_KEY = ON`).
  - Tuning de Fill Factor (`FILLFACTOR = 85`) en `inventory_stockbodega`.
- `V3__optimize_stored_procedures_texcore.sql`: **Script DDL de Optimización de Stored Procedures**.
  - Rango de fechas Sargables (`fecha_pedido >= @FechaInicio AND fecha_pedido < DATEADD(...)`) sin funciones `CAST`.
  - Eliminación de subconsultas correlacionadas redundantes en `sp_GetDeudoresGerencial` (patrón CTE en una sola pasada).
  - Consolidación de agregaciones `MIN`, `MAX` y `SUM` en `OUTER APPLY` para `sp_GetOrdenesProduccionGerencial`.
  - Filtrado estricto `pv.anulado = 0` en SPs de ventas y cartera.
  - Inserción de `OPTION (RECOMPILE)` para resolver Parameter Sniffing en consultas con parámetros opcionales.
- `reset_db_identities.sql`: **Script de Limpieza y Mantenimiento**.
  - Truncado/limpieza de datos y reseteo de semillas de identidad (`DBCC CHECKIDENT`) para entornos de desarrollo y pruebas.

---

## 🚀 Ejecución de los Scripts de Optimización

`V2__optimize_sqlserver2022_texcore.sql` y `V3__optimize_stored_procedures_texcore.sql`
se aplican **automáticamente** en cada arranque del contenedor `web`, vía
`infrastructure/docker/entrypoint.sh` → `python manage.py apply_sql_optimizations`
(justo después de `manage.py migrate`). Ese comando lee los archivos con la
propia conexión Django/pyodbc y los ejecuta lote por lote (separados por `GO`)
— no depende de `sqlcmd` ni de que estos `.sql` existan dentro del contenedor
`db` (el contenedor `db` **no** tiene estos archivos montados ni copiados; un
`sqlcmd -i /var/opt/mssql/database/...` ejecutado ahí falla con "Cannot open
file"). Ambos scripts están escritos de forma idempotente (`CREATE OR ALTER`,
`IF NOT EXISTS`), así que repetir la aplicación en cada arranque es seguro.

Para forzar una re-aplicación manual (por ejemplo tras editar uno de los
`.sql` sin reiniciar el contenedor):

```bash
docker compose exec -T web python manage.py apply_sql_optimizations
```

Si el motor configurado no es SQL Server (p. ej. `settings_test_local` con
sqlite), el comando se omite solo, sin error.

Documentación completa de arquitectura y auditoría: [docs/arquitectura/AUDITORIA_Y_OPTIMIZACION_BD_SQLSERVER2022.md](../docs/arquitectura/AUDITORIA_Y_OPTIMIZACION_BD_SQLSERVER2022.md).
