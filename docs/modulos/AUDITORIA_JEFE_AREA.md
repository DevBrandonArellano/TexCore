# Auditoría y Mejoras del Rol Jefe de Área

**Fecha:** 2026-07-20
**Versión:** 1.0
**Autor:** Claude Code (Sonnet 5)

---

## Resumen Ejecutivo

Se auditó el rol **Jefe de Área** (`jefe_area`) comparándolo con la práctica industrial del
*Production/Line Supervisor* (ISA-95 Nivel 3 / MES, KPIs de manufactura, Lean/Andon, ISO 9001,
TPM). De la auditoría se implementaron las correcciones de mayor impacto y bajo riesgo (P0), y
se corrigió un bug crítico descubierto en la acción `reetiquetar`:

- ✅ **R1** — Bug de rechazo de lote: el frontend no enviaba la justificación que el backend exige.
- ✅ **R2** — KPI real: se reemplazó el `rendimiento_yield` fijo en `1.0` por Rendimiento (Yield),
  First Pass Yield (FPY) y distribución por calidad, calculados con datos reales.
- ✅ **R3** — Corrección de comentario de permisos desalineado en `OrdenProduccionViewSet`.
- ✅ **Bug `reetiquetar`** — La verificación de supervisor usaba un atributo `role` inexistente
  en `CustomUser` y faltaba `lote = self.get_object()`; se corrigió usando grupos de Django.

Las brechas mayores (P1/P2) que requieren modelos nuevos quedan documentadas como trabajo futuro.

---

## Fundamento Industrial (base de la auditoría)

- **KPIs de supervisión:** un supervisor rastrea 5–8 KPIs; los núcleo son **OEE** (Disponibilidad ×
  Rendimiento × Calidad), **First Pass Yield / Right First Time**, downtime y schedule attainment.
  El componente "Calidad" de OEE equivale al FPY. El retrabajo cuesta 2–3× el costo original.
- **ISO 9001 (no-conformidad):** toda acción de rechazo/corrección debe tener causa trazable
  (quién, cuándo, por qué). Justifica el motivo obligatorio en el rechazo de lote.
- **Andon / escalamiento, TPM / mantenimiento autónomo, shift handover:** responsabilidades núcleo
  del supervisor que hoy TexCore no cubre (ver "Trabajo futuro").

Fuentes: ver la sección "Fuentes" al final.

---

## Correcciones Implementadas

### R1 — Bug de rechazo de lote (motivo obligatorio)

**Problema:** `handleRechazarLote` en `JefeAreaDashboard.tsx` hacía `POST /lotes-produccion/{id}/rechazar/`
**sin cuerpo**, pero el backend (`LoteProduccionViewSet.rechazar`) exige `justificacion` no vacía
→ todo rechazo desde el dashboard fallaba con `400`.

**Solución:** el frontend ahora solicita el motivo (`window.prompt`) y envía
`{ justificacion }`. Si el usuario cancela o deja el motivo vacío, la acción se aborta con aviso.

- Archivo: `frontend/src/components/jefe-area/JefeAreaDashboard.tsx` (`handleRechazarLote`).
- Tests: `JefeAreaDashboard.test.tsx` — 4 casos (envía justificación, cancela, motivo vacío, error).

### R2 — KPI real de rendimiento y calidad

**Problema:** `KPIAreaView` devolvía `rendimiento_yield: 1.0` (placeholder), pese a que los datos
para calcularlo ya existían en `LoteProduccion` (`peso_neto_producido`, `peso_merma`,
`clasificacion_calidad`).

**Solución:** `KPIAreaView` (`gestion/views/kpi_views.py`) calcula con un único `aggregate`:

| KPI | Fórmula | Fundamento |
|-----|---------|-----------|
| `rendimiento_yield` | neto / (neto + merma) | Yield = salida buena / entrada |
| `first_pass_yield` | neto de primera calidad / neto total | Componente "Calidad" de OEE |
| `distribucion_calidad` | Σ neto por primera/segunda/saldo (kg) | Visibilidad de retrabajo/degradación |
| `total_merma_kg` | Σ merma | Insumo del Yield |

Borde: sin producción, `yield`/`FPY` retornan `0.0` (sin división por cero). El frontend muestra
el FPY junto al Yield en la tarjeta "Rendimiento".

- Archivos: `gestion/views/kpi_views.py`, `frontend/src/lib/types.ts` (interfaz `KPIArea`),
  `frontend/src/components/jefe-area/JefeAreaDashboard.tsx`.
- Tests: `gestion/tests/test_kpi_views.py::KPIAreaCalidadRendimientoTestCase` (4) +
  `JefeAreaDashboard.test.tsx` (FPY visible).

### R3 — Comentario de permisos corregido

`OrdenProduccionViewSet.get_permissions` decía "Solo Jefe de Planta, Admin Sistemas o Admin Sede
pueden crear", pero el permiso real (`IsJefeAreaOrAdmin`) **sí** incluye `jefe_area` (coherente con
que el dashboard ofrece "Nueva Orden"). Se corrigió el comentario para reflejar el comportamiento real.

### Bug crítico en `reetiquetar` (RBAC por grupos)

**Problema:** la acción `reetiquetar` verificaba `getattr(request.user, 'role', None) in supervisor_roles`,
pero **`CustomUser` no tiene atributo `role`** — todo el RBAC del proyecto se basa en **grupos de
Django**. Resultado: `is_supervisor` siempre era falso y hasta un Jefe de Área con sesión activa era
forzado al flujo de usuario+contraseña in-situ (`403`). Además, una refactorización previa había
eliminado la línea `lote = self.get_object()`, causando `NameError` → `500` en el camino feliz.

**Solución:** se introdujo un helper `es_supervisor(u)` que consulta los grupos de Django
(consistente con `IsJefeAreaOrAdmin`), aplicado tanto al usuario de sesión como al supervisor
autenticado in-situ; y se restauró `lote = self.get_object()`.

- Archivo: `gestion/views/production_views.py` (`LoteProduccionViewSet.reetiquetar`).
- Tests: `gestion/tests/test_production_views.py::LoteProduccionReetiquetarTestCase` (5, en verde).

---

## RBAC del rol (confirmado en código)

| Capacidad | jefe_area | Aislamiento |
|-----------|-----------|-------------|
| Crear/asignar Órdenes de Producción | ✅ | Solo su área (`IsJefeAreaOrAdmin` + `area=user.area`) |
| Rechazar lote (motivo obligatorio) | ✅ | Solo su área |
| Reetiquetar lote (motivo obligatorio) | ✅ | Grupos supervisor (`jefe_area`/`jefe_planta`/`admin_*`) |
| Gestión de máquinas y líneas de producción | ✅ | Solo su área + sede |
| Transformaciones y trazabilidad | ✅ | Solo su área + sede |
| KPIs de área | ✅ (lectura) | Solo su propia área si no es admin |
| Crear transferencias inter-área | ❌ | Reservado a `jefe_planta`/admin |

---

## Verificación

Harness local (sin SQL Server): `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local` +
`pytest --no-migrations` (SQLite en memoria; `--no-migrations` evita el stored procedure MSSQL de
`inventory/migrations/0020`).

- **Backend (alcance tocado):** `test_kpi_views.py` + `test_production_views.py` +
  `test_evento_etiqueta.py` → **76/76 en verde**.
- **Frontend:** `JefeAreaDashboard.test.tsx` → **54/54 en verde** (Vitest).

> Nota: la suite completa de `gestion` presenta 10 fallos **preexistentes** en archivos no
> modificados (`test_lineas_produccion`, `test_sales_views_extra`, `OrdenProduccionCreate`-sede),
> atribuibles a diferencias del entorno local SQLite/`--no-migrations` frente al CI con MSSQL —
> no son regresiones de estas correcciones.

---

## Brechas pendientes (roadmap de la auditoría)

Requieren **modelos nuevos** y se dejan como trabajo futuro (ver detalle en la auditoría original):

- **R4 — OEE completo:** captura de downtime con *reason codes* para calcular la Disponibilidad y
  componer OEE = Disponibilidad × Rendimiento × Calidad (FPY).
- **R5 — Gestión de no-conformidad (CAPA):** entidad de no-conformidad con dueño, estado
  (abierto→en curso→cerrado), causa raíz y acción correctiva, sobre el rechazo actual (ISO 9001 / Andon).
- **R6 — Shift handover log:** entrega de turno digital (pendientes, incidencias, estado de máquinas).
- **R7–R9:** escalamiento cronometrado de alertas (Andon), mantenimiento autónomo (TPM),
  schedule attainment / OTIF.

---

## Fuentes (industria)

- [Production Supervisor Job Description — Indeed](https://www.indeed.com/hire/job-description/production-supervisor)
- [Exploring ISA-95 Standards in Manufacturing — EMQ](https://www.emqx.com/en/blog/exploring-isa95-standards-in-manufacturing)
- [Manufacturing KPIs: 25 Metrics That Matter (OEE, FPY) — iFactory](https://ifactoryapp.com/analytics-reporting/manufacturing-kpis-25-metrics-that-matter-2026)
- [What is Andon and why is line-stop authority the core of it — TEEPTRAK](https://teeptrak.com/en/andon-2026/)
- [ISO 9001 Nonconformity: Major and Minor — ComplianceQuest](https://www.compliancequest.com/bloglet/iso-9001-nonconformity/)
- [Total Productive Maintenance (TPM) — Lean Production](https://www.leanproduction.com/tpm/)
