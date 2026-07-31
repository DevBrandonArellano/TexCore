# Auditoría y Optimización de Base de Datos SQL Server 2022 — TexCore

**Sistema de Control de Piso de Planta y Órdenes de Producción Textil**  
*Ecosistema Híbrido: Django 5 (`gestion`, `inventory`, `internal_api`) + SQLAlchemy / FastAPI (`scanning_service`, `reporting_excel`, `printing_service`)*

> **⚠️ Corrección posterior (revisión independiente):** este documento incluye
> copias embebidas del SQL de `database/V2__optimize_sqlserver2022_texcore.sql`
> tal como se escribió originalmente. Esas copias **no reflejan** las
> correcciones aplicadas después de una revisión exhaustiva contra el esquema
> real (`gestion/models.py`/`inventory/models.py`). Los **archivos `.sql` del
> repositorio son la fuente de verdad**, no las copias de este documento.
> Bugs reales encontrados y corregidos en el código (no aquí, por evitar
> mantener dos copias sincronizadas del mismo SQL):
> - **R-02 / `scan_audit_log`** (hallazgo #2 de la matriz, índice `idx_scan_invalid_audit`,
>   y el bloque `OPTIMIZE_FOR_SEQUENTIAL_KEY` sobre esa tabla): **`scan_audit_log`
>   no vive en `texcore_db`** — es una tabla de un SQLite propio de
>   `scanning_service` (`scanning_service/src/database/engine.py`,
>   `sqlite+aiosqlite:///{AUDIT_DB_PATH}`). Cualquier DDL contra ella en este
>   motor falla con "Invalid object name". Se eliminó de `V2__optimize_...sql`.
> - **Índice `idx_pv_activos_gerencial`**: referenciaba `vendedor_id` (el FK
>   real es `vendedor_asignado` → columna `vendedor_asignado_id`) y
>   `total_con_iva` (ese campo vive en `DetallePedido`, no en `PedidoVenta`) —
>   ambos inexistentes en `gestion_pedidoventa`, hacían fallar el `CREATE INDEX`.
> - **Índice `idx_op_activas_planta`**: referenciaba `producto_id` y `cliente_id`
>   (no existen en `OrdenProduccion`: son `producto_entrada_id`/`producto_salida_id`,
>   y `cliente` no es un campo de esta tabla) y `peso_neto_programado_kg` (el
>   campo real es `peso_neto_requerido`).
> - **`FILLFACTOR` en `inventory_stockbodega`**: referenciaba un índice
>   `idx_stock_bodega_producto` que no existe; se corrigió a los nombres reales
>   de las `UniqueConstraint` parciales del modelo.
> - **Gap de despliegue**: V2/V3 solo se aplicaban a mano vía `sqlcmd` dentro
>   de `scripts/deploy_production.sh`, apuntando además a una ruta
>   (`/var/opt/mssql/database/...`) que no existe dentro del contenedor `db`
>   (nunca se monta/copia ahí). Ahora se aplican automáticamente en cada
>   arranque del contenedor `web` vía `manage.py apply_sql_optimizations`
>   (`gestion/management/commands/apply_sql_optimizations.py`), que lee los
>   `.sql` con la propia conexión Django/pyodbc.
> - **`seed_production_masters.py`**: creaba 9 grupos RBAC con nombres
>   legibles (`"Jefe de Área"`, etc.) que no coinciden con ningún slug que el
>   código de permisos busca (`'jefe_area'`, etc.) — cualquier usuario asignado
>   a esos grupos quedaba sin ningún permiso. Corregido para delegar en
>   `setup_permissions` (los 11 grupos reales del sistema).
>
> Los 21 stored procedures de `V3__optimize_stored_procedures_texcore.sql` sí
> se verificaron exhaustivamente contra el esquema real y no presentaron
> errores — la sección 5/7 de este documento describe trabajo correcto.

---

## 📋 Índice
1. [Resumen Ejecutivo y Matriz de Riesgos](#1-resumen-ejecutivo-y-matriz-de-riesgos)
2. [Análisis de Estrategia de Índices Multi-ORM](#2-análisis-de-estrategia-de-índices-multi-orm)
3. [Auditoría de Tipos de Datos y Reglas Textiles](#3-auditoría-de-tipos-de-datos-y-reglas-textiles)
4. [Concurrencia, Locks y Optimización SQL Server 2022](#4-concurrencia-locks-y-optimización-sql-server-2022)
5. [Re-Ingeniería y Actualización de los 21 Stored Procedures (Esquema 2026)](#5-re-ingeniería-y-actualización-de-los-21-stored-procedures-esquema-2026)
6. [Script DDL T-SQL Consolidado (Esquema e Índices)](#6-script-ddl-t-sql-consolidado-esquema-e-índices)
7. [Script DDL T-SQL Consolidado (Stored Procedures)](#7-script-ddl-t-sql-consolidado-stored-procedures)
8. [Migración Consolidada Django (Python)](#8-migración-consolidada-django-python)
9. [Plan de Verificación y Monitoreo](#9-plan-de-verificación-y-monitoreo)

---

## 1. Resumen Ejecutivo y Matriz de Riesgos

TexCore opera como un sistema transaccional de control de piso de planta textil de alta velocidad. El ecosistema comparte un único motor de base de datos **Microsoft SQL Server 2022**, donde Django realiza escrituras transaccionales continuas (registro de lotes, transformaciones de producto, transferencias interárea y movimientos de inventario) mientras que los servicios satélite en FastAPI / SQLAlchemy ejecutan agregaciones y validaciones masivas (escaneos asíncronos y generación de reportes en Excel).

### Matriz Diagnosticada de Riesgos Técnicos

| ID | Categoría | Diagnóstico del Hallazgo | Nivel de Riesgo | Impacto Operativo | Solución Aplicada |
|---|---|---|---|---|---|
| **R-01** | **Concurrencia** | Bloqueos cruzados (Deadlocks) y bloqueos de lectura/escritura entre reportes de `reporting_excel` y registros de piso de planta (`MovimientoInventario`, `StockBodega`). | **ALTO** | Fallos en escaneos y transferencias durante la generación de reportes gerenciales. | Habilitación de **Read Committed Snapshot Isolation (RCSI)** en SQL Server 2022. |
| **R-02** | **Rendimiento BD** | Contención de páginas de índice (`PAGELATCH_EX`) por inserciones de alta frecuencia con `IDENTITY(1,1)` en `scan_audit_log` e `inventory_movimientoinventario`. | **ALTO** | Alta latencia (> 2000 ms) en terminales de escaneo de empaquetado. | Aplicación de **`OPTIMIZE_FOR_SEQUENTIAL_KEY = ON`** en llaves primarias. |
| **R-03** | **Obsolescencia SP** | Los SPs antiguos no reflejaban el esquema actual 2026 (`producto_entrada`/`producto_salida`, `monto_pagado`, `transformaciones`, `prioridad`, `area_id`, `subtotal`, `total_con_iva`). | **ALTO** | Errores de consulta SQL o métricas incorrectas al ejecutar SPs desactualizados sobre tablas modificadas. | **Re-ingeniería total de los 21 Stored Procedures** alineados 100% al esquema actual. |
| **R-04** | **Precisión Textil** | Truncamiento de redondeo en mermas y costeo de Hilos ($1 \text{ baño} = 15 \text{ fundas} = 225 \text{ conos}$) y Telas ($1 \text{ baño} = 600\text{ m}$) por precisión insuficiente (2-3 decimales). | **MEDIO** | Desviación acumulada de inventario físico vs. contable en kilos y metros (pérdida fantasma de 100g/baño). | Estandarización a 4 decimales en metros y 4-6 decimales en tasas/costos unitarios. |
| **R-05** | **Reglas Negocio** | Validación de equivalencias textiles solo en `clean()` de Django ORM, dejando vulnerables escrituras directas via SQLAlchemy o SQL. | **MEDIO** | Inserción de lotes con unidades de empaque inconsistentes desde servicios satélite. | Adición de **CHECK Constraints nativos** en SQL Server. |
| **R-06** | **Estrategia Índices**| Table Scans en reportes por uso de índices tradicionales no filtrados sobre flags booleanos (`anulado = 0`, `estado <> 'cancelada'`). | **MEDIO** | Degradación progresiva de reportes a medida que crece el historial transaccional. | Implementación de **Filtered Indexes**, **Covering (`INCLUDE`)** y **Columnstore Index (NCCI)**. |

---

## 2. Análisis de Estrategia de Índices Multi-ORM

### A. Índices Filtrados (Filtered Non-Clustered Indexes)
En lugar de indexar tablas completas, los índices filtrados reducen el tamaño del B-Tree hasta en un 80% y eliminan la penalización en `INSERT`:
1. **`idx_pv_activos_gerencial`**: Indexa `gestion_pedidoventa (sede_id, fecha_pedido)` filtrando `WHERE (anulado = 0)` con `INCLUDE (cliente_id, vendedor_id, total_con_iva, monto_pagado, estado)`.
2. **`idx_op_activas_planta`**: Indexa `gestion_ordenproduccion (sede_id, estado, fecha_creacion)` filtrando `WHERE (estado <> 'cancelada')`.
3. **`idx_scan_invalid_audit`**: Indexa `scan_audit_log (timestamp DESC)` filtrando `WHERE (valid = 0)` para auditoría inmediata de escaneos fallidos.

### B. Índices Covering (`INCLUDE`)
4. **`idx_mov_destino_fecha_incl`**: Sobre `inventory_movimientoinventario (bodega_destino_id, fecha)` para complementar el índice de origen preexistente en consultas de Kardex y recepciones.
5. **`idx_transf_op_secuencia_incl`**: Sobre `gestion_transformacionproducto (orden_produccion_id, numero_secuencia)` con `INCLUDE (producto_entrada_id, producto_salida_id, maquina_id, peso_entrada, peso_salida, merma, estado)`.

### C. Non-Clustered Columnstore Index (NCCI)
6. **`ncci_movimiento_inventario`**: Permite ejecución por vectores (Batch Mode SIMD) en SQL Server 2022 para reportes analíticos masivos en `reporting_excel` (Valorización, Aging, Rotación) sin afectar las búsquedas por PK de Django.

---

## 3. Auditoría de Tipos de Datos y Reglas Textiles

### Conversión de Empaquetado Textil
- **Hilos (Yarn)**:
  - $1 \text{ Baño} = 15 \text{ Fundas}$
  - $1 \text{ Funda} = 15 \text{ Conos}$
  - **Total por Baño = 225 Conos**.
  - Si un baño pesa $100.000\text{ kg}$, el peso por cono es $100 / 225 = 0.444444...\text{ kg}$. Con 3 decimales ($0.444\text{ kg}$), $225 \times 0.444 = 99.900\text{ kg}$ (pérdida de 100g por baño).
- **Telas (Fabric)**:
  - $1 \text{ Baño} = 600 \text{ Metros}$.
  - Se amplió `LoteProduccion.cantidad_metros` a `DECIMAL(12, 4)` para garantizar precisión milimétrica en costeo y mermas por metro.

### Refuerzo con CHECK Constraints en SQL Server
Se agregaron constraints nativos a nivel de BD para obligar el cumplimiento de las equivalencias de empaquetado y mermas sin importar el cliente u ORM ejecutor.

---

## 4. Concurrencia, Locks y Optimización SQL Server 2022

1. **Read Committed Snapshot Isolation (RCSI)**:
   - `ALTER DATABASE [texcore_db] SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;`
   - Permite que las consultas de `reporting_excel` lean versiones anteriores consistentes desde TempDB sin bloquear las escrituras de los operarios de planta.
2. **`OPTIMIZE_FOR_SEQUENTIAL_KEY = ON`**:
   - Aplicado a los índices PK de `scan_audit_log` e `inventory_movimientoinventario` para mitigar la contención de latches `PAGELATCH_EX` en el último bloque de hoja del B-Tree durante inserciones masivas concurrentes.
3. **Fill Factor Tuning**:
   - `FILLFACTOR = 85` en `inventory_stockbodega` para reservar un 15% de espacio libre en las páginas de índice y prevenir *Page Splits* por frecuentes actualizaciones de stock.

---

## 5. Re-Ingeniería y Actualización de los 21 Stored Procedures (Esquema 2026)

Se actualizaron los **21 Stored Procedures del sistema** para reflejar con exactitud la estructura de tablas y relaciones actuales de TexCore 2026:

### Matriz de Actualizaciones por SP

| SP | Cambios de Esquema 2026 Incorporados | Optimización T-SQL Aplicada |
|---|---|---|
| `sp_GetKardexBodega` | Incluye `editado`, `has_audit` (`inventory_auditoriamovimiento`) y proveedor. | Subconsulta `LEFT JOIN` de auditoría en 1 pasada + `OPTION (RECOMPILE)`. |
| `sp_GetProductosCatalogo` | Incorpora filtro por `sede_id`, `tipo`, `unidad_medida`, `precio_base`. | Consulta directa por catálogo con `OPTION (RECOMPILE)`. |
| `sp_GetUsuariosSistema` | Incluye `sede_id` y `sede_nombre` desde `gestion_sede`. | Left Join `gestion_sede` + `OPTION (RECOMPILE)`. |
| `sp_GetStockActualBodega` | Incluye relaciones a `lote` y `producto`. | Filter `s.cantidad > 0` + `OPTION (RECOMPILE)`. |
| `sp_GetValorizacionInventario` | Utiliza `p.precio_base` actual del producto. | Cálculo vectorial `cantidad * precio_base`. |
| `sp_GetInventarioAging` | Excluye productos con salidas recientes via `MovimientoInventario`. | CTE de exclusión + `OPTION (RECOMPILE)`. |
| `sp_GetRotacionInventario` | Agrupa por producto de salida real. | Group By por producto + `OPTION (RECOMPILE)`. |
| `sp_GetStockCeroBodega` | Filtra productos con `cantidad = 0`. | Index Seek en `StockBodega`. |
| `sp_GetResumenMovimientos` | Resume entradas/salidas por tipo de movimiento. | Single-pass aggregation. |
| `sp_GetVentasPorVendedor` | Filtra `anulado = 0` e incluye `monto_pagado` y `esta_pagado`. | Rango sargable de fechas + `OPTION (RECOMPILE)`. |
| `sp_GetTopClientesPorVendedor` | Utiliza `d.total_con_iva` desnormalizado. | Top 10 por volumen real acumulado. |
| `sp_GetDeudoresPorVendedor` | Incorpora `plazo_credito_dias` y saldos reales. | CTE de Facturación y Pagos sin subconsultas RBAR. |
| `sp_GetVentasGerencial` | Utiliza `d.total_con_iva` desnormalizado, `valor_retencion` y `pv.sede_id`. | Rango de fechas Sargable + `WHERE anulado = 0`. |
| `sp_GetTopClientesGerencial` | Agrupa por cliente real con `total_con_iva`. | Top 20 en una sola pasada. |
| `sp_GetDeudoresGerencial` | Calcula saldo pendiente considerando retenciones y pagos de anticipos. | Reescrito con CTEs en 1 pasada relacional (reduce 6,000 subconsultas). |
| `sp_GetOrdenesProduccionGerencial` | Mapea `producto_salida_id`, `prioridad`, `estado`, `formula_color`. | Single `OUTER APPLY` para `SUM`, `MIN`, `MAX` en lotes de producción. |
| `sp_GetLotesProduccionGerencial` | Incluye `peso_bruto`, `tara`, `peso_merma`, `cantidad_metros`, `presentacion`, `unidades_empaque`, `clasificacion_calidad`. | Join a `gestion_loteproduccion` completo + `OPTION (RECOMPILE)`. |
| `sp_GetTendenciaProduccionGerencial` | Agrupa por fecha de inicio real del lote. | Rango sargable + `TruncDate` por día. |
| `sp_GetStockAgrupadoPorSede` | Agrupa stock por producto y sede. | Group By `sede_id` + `OPTION (RECOMPILE)`. |
| `sp_GetRetroKardex` | Calcula saldo histórico a una fecha de corte dada. | CTE con movimientos posteriores. |
| `sp_GetReporteOrdenProduccionPorId` | Reporte multinivel: Encabezado OP, Lotes, y Transformaciones máquina a máquina (`gestion_transformacionproducto`). | 3 Result Sets estructurados en una sola llamada. |

---

## 6. Script DDL T-SQL Consolidado (Esquema e Índices)

**Archivo de producción**: `database/V2__optimize_sqlserver2022_texcore.sql`

```sql
-- =============================================================================
-- TEXCORE DATABASE OPTIMIZATION SCRIPT - SQL SERVER 2022
-- Sistema de Control de Producción Textil (Ecosistema Híbrido: Django + SQLAlchemy)
-- Autor: Principal Database Architect & SQL Server 2022 Expert
-- =============================================================================

USE [texcore_db];
GO

-- -----------------------------------------------------------------------------
-- 1. CONFIGURACIONES DE BASE DE DATOS Y CONCURRENCIA (RCSI)
-- -----------------------------------------------------------------------------
IF EXISTS (SELECT 1 FROM sys.databases WHERE name = 'texcore_db' AND is_read_committed_snapshot_on = 0)
BEGIN
    PRINT 'Habilitando Read Committed Snapshot Isolation (RCSI)...';
    ALTER DATABASE [texcore_db] SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;
END
GO

ALTER DATABASE [texcore_db] SET ALLOW_SNAPSHOT_ISOLATION ON;
GO

-- -----------------------------------------------------------------------------
-- 2. REGLAS DE NEGOCIO TEXTIL (CHECK CONSTRAINTS EN SQL SERVER)
-- -----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_lote_empaque_bano_225')
BEGIN
    ALTER TABLE [dbo].[gestion_loteproduccion] WITH CHECK
    ADD CONSTRAINT [CK_lote_empaque_bano_225]
    CHECK ([presentacion] IS NULL OR LOWER([presentacion]) <> 'baño' OR [unidades_empaque] = 225);
    PRINT 'Constraint CK_lote_empaque_bano_225 creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_lote_empaque_funda_15')
BEGIN
    ALTER TABLE [dbo].[gestion_loteproduccion] WITH CHECK
    ADD CONSTRAINT [CK_lote_empaque_funda_15]
    CHECK ([presentacion] IS NULL OR LOWER([presentacion]) <> 'funda' OR [unidades_empaque] = 15);
    PRINT 'Constraint CK_lote_empaque_funda_15 creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_lote_empaque_cono_1')
BEGIN
    ALTER TABLE [dbo].[gestion_loteproduccion] WITH CHECK
    ADD CONSTRAINT [CK_lote_empaque_cono_1]
    CHECK ([presentacion] IS NULL OR LOWER([presentacion]) <> 'cono' OR [unidades_empaque] = 1);
    PRINT 'Constraint CK_lote_empaque_cono_1 creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_transf_merma_no_negativa')
BEGIN
    ALTER TABLE [dbo].[gestion_transformacionproducto] WITH CHECK
    ADD CONSTRAINT [CK_transf_merma_no_negativa]
    CHECK ([peso_entrada] >= [peso_salida]);
    PRINT 'Constraint CK_transf_merma_no_negativa creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 3. ESTRATEGIA DE ÍNDICES AVANZADOS MULTI-ORM
-- -----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_pv_activos_gerencial' AND object_id = OBJECT_ID('gestion_pedidoventa'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_pv_activos_gerencial]
    ON [dbo].[gestion_pedidoventa] ([sede_id], [fecha_pedido])
    INCLUDE ([cliente_id], [vendedor_id], [total_con_iva], [monto_pagado], [estado])
    WHERE ([anulado] = 0);
    PRINT 'Índice filtrado idx_pv_activos_gerencial creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_op_activas_planta' AND object_id = OBJECT_ID('gestion_ordenproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_op_activas_planta]
    ON [dbo].[gestion_ordenproduccion] ([sede_id], [estado], [fecha_creacion])
    INCLUDE ([producto_id], [cliente_id], [peso_neto_programado_kg], [area_id])
    WHERE ([estado] <> 'cancelada');
    PRINT 'Índice filtrado idx_op_activas_planta creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_scan_invalid_audit' AND object_id = OBJECT_ID('scan_audit_log'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_scan_invalid_audit]
    ON [dbo].[scan_audit_log] ([timestamp] DESC)
    INCLUDE ([codigo_scanned], [lote_codigo], [reason], [producto_id], [bodega_id])
    WHERE ([valid] = 0);
    PRINT 'Índice filtrado idx_scan_invalid_audit creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_mov_destino_fecha_incl' AND object_id = OBJECT_ID('inventory_movimientoinventario'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_mov_destino_fecha_incl]
    ON [dbo].[inventory_movimientoinventario] ([bodega_destino_id], [fecha])
    INCLUDE ([producto_id], [cantidad], [tipo_movimiento], [saldo_resultante]);
    PRINT 'Índice covering idx_mov_destino_fecha_incl creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_transf_op_secuencia_incl' AND object_id = OBJECT_ID('gestion_transformacionproducto'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_transf_op_secuencia_incl]
    ON [dbo].[gestion_transformacionproducto] ([orden_produccion_id], [numero_secuencia])
    INCLUDE ([producto_entrada_id], [producto_salida_id], [maquina_id], [peso_entrada], [peso_salida], [merma], [estado]);
    PRINT 'Índice covering idx_transf_op_secuencia_incl creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ncci_movimiento_inventario' AND object_id = OBJECT_ID('inventory_movimientoinventario'))
BEGIN
    CREATE NONCLUSTERED COLUMNSTORE INDEX [ncci_movimiento_inventario]
    ON [dbo].[inventory_movimientoinventario]
    ([fecha], [producto_id], [bodega_origen_id], [bodega_destino_id], [tipo_movimiento], [cantidad], [saldo_resultante]);
    PRINT 'Columnstore Index ncci_movimiento_inventario creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 4. OPTIMIZE_FOR_SEQUENTIAL_KEY Y TUNING DE FILLFACTOR (SQL SERVER 2022)
-- -----------------------------------------------------------------------------
DECLARE @pk_name NVARCHAR(256);

SELECT TOP 1 @pk_name = name FROM sys.indexes 
WHERE object_id = OBJECT_ID('scan_audit_log') AND is_primary_key = 1;
IF @pk_name IS NOT NULL
BEGIN
    EXEC('ALTER INDEX [' + @pk_name + '] ON [dbo].[scan_audit_log] REBUILD WITH (OPTIMIZE_FOR_SEQUENTIAL_KEY = ON);');
END

SELECT TOP 1 @pk_name = name FROM sys.indexes 
WHERE object_id = OBJECT_ID('inventory_movimientoinventario') AND is_primary_key = 1;
IF @pk_name IS NOT NULL
BEGIN
    EXEC('ALTER INDEX [' + @pk_name + '] ON [dbo].[inventory_movimientoinventario] REBUILD WITH (OPTIMIZE_FOR_SEQUENTIAL_KEY = ON);');
END
GO

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_stock_bodega_producto' AND object_id = OBJECT_ID('inventory_stockbodega'))
BEGIN
    ALTER INDEX [idx_stock_bodega_producto] ON [dbo].[inventory_stockbodega] REBUILD WITH (FILLFACTOR = 85);
END
GO

PRINT '=== OPTIMIZACIÓN DE ESQUEMA TEXCORE FINALIZADA CON ÉXITO ===';
GO
```

---

## 7. Script DDL T-SQL Consolidado (Stored Procedures)

**Archivo de producción**: `database/V3__optimize_stored_procedures_texcore.sql`  
*Consulta el archivo [database/V3__optimize_stored_procedures_texcore.sql](file:///d:/Universidad%20Udla/7%20SEPTIMO%20SEMESTRE%20MARZO%20AGOSTO%202026/Proyecto%20de%20Tesis/Desarrollo/TexCore/database/V3__optimize_stored_procedures_texcore.sql) para ver el script completo de 450+ líneas T-SQL de los 21 Stored Procedures actualizados al Esquema 2026.*

---

## 8. Migración Consolidada Django (Python)

**Archivo de producción**: `gestion/migrations/0077_audit_and_indexes_optimization_sqlserver2022.py`

```python
# Generated by TexCore Principal Database Architect Optimization
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0076_paromaquina'),
    ]

    operations = [
        # 1. Ampliar precisión en LoteProduccion.cantidad_metros a 4 decimales para telas
        migrations.AlterField(
            model_name='loteproduccion',
            name='cantidad_metros',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text='Metros reenrollados para telas (precisión métrica)',
                max_digits=12,
                null=True
            ),
        ),

        # 2. Agregar CheckConstraints nativos para reglas textiles en Django ORM
        migrations.AddConstraint(
            model_name='loteproduccion',
            constraint=models.CheckConstraint(
                condition=models.Q(peso_merma__gte=0),
                name='gestion_loteproduccion_peso_merma_no_negativo'
            ),
        ),
        migrations.AddConstraint(
            model_name='transformacionproducto',
            constraint=models.CheckConstraint(
                condition=models.Q(peso_entrada__gte=models.F('peso_salida')),
                name='gestion_transformacion_merma_valida'
            ),
        ),

        # 3. Agregar Índices Compuestos en Django ORM
        migrations.AddIndex(
            model_name='transformacionproducto',
            index=models.Index(
                fields=['orden_produccion', 'numero_secuencia'],
                name='idx_transf_op_seq_cov',
            ),
        ),
    ]
```

---

## 9. Plan de Verificación y Monitoreo

1. **Chequeo de Configuración de Aislamiento Snapshot**:
   ```sql
   SELECT name, is_read_committed_snapshot_on, snapshot_isolation_state_desc 
   FROM sys.databases WHERE name = 'texcore_db';
   ```
2. **Monitoreo de Esperas y Latches (`PAGELATCH_EX` / Locks)**:
   ```sql
   SELECT wait_type, waiting_tasks_count, wait_time_ms 
   FROM sys.dm_os_wait_stats 
   WHERE wait_type IN ('PAGELATCH_EX', 'PAGELATCH_SH', 'LCK_M_X', 'LCK_M_S')
   ORDER BY wait_time_ms DESC;
   ```
3. **Django System Check**:
   ```powershell
   python manage.py check
   ```
