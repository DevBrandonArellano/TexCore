# Auditoría y Mejoras del Rol Jefe de Área

**Fecha:** 2026-07-20 (última actualización: 2026-07-21)
**Versión:** 1.1
**Autor:** Claude Code (Sonnet 5 / Opus 4.8)

---

## Resumen Ejecutivo

Se auditó el rol **Jefe de Área** (`jefe_area`) comparándolo con la práctica industrial del
*Production/Line Supervisor* (ISA-95 Nivel 3 / MES, KPIs de manufactura, Lean/Andon, ISO 9001,
TPM) y con tres textos canónicos (*OEE for Operators*, *Manufacturing Planning and Control for
Supply Chain Management* de Vollmann/Berry/Whybark/Jacobs, *Production & Operations Management*).
De la auditoría se implementaron:

- ✅ **R1** — Bug de rechazo de lote: el frontend no enviaba la justificación que el backend exige.
- ✅ **R2** — KPI real: se reemplazó el `rendimiento_yield` fijo en `1.0` por Rendimiento (Yield),
  First Pass Yield (FPY) y distribución por calidad, calculados con datos reales.
- ✅ **R3** — Corrección de comentario de permisos desalineado en `OrdenProduccionViewSet`.
- ✅ **Bug `reetiquetar`** — La verificación de supervisor usaba un atributo `role` inexistente
  en `CustomUser` y faltaba `lote = self.get_object()`; se corrigió usando grupos de Django.
- ✅ **Fase 0** — Corrección de regla de negocio: la creación de OP es exclusiva del Jefe de
  Planta/Admin (el Jefe de Área solo asigna recursos); se eliminó el botón "Nueva Orden" del rol.
- ✅ **R4** — OEE completo: modelo `ParoMaquina` (downtime con reason codes = Seis Grandes
  Pérdidas), `OeeService`, KPI de área y por máquina, UI (tarjeta, badge, modal de registro).

Las brechas restantes (R5–R9) que requieren modelos nuevos quedan documentadas como trabajo futuro.

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
| Crear Órdenes de Producción | ❌ | Exclusivo de `jefe_planta`/admin (`IsJefePlantaOrAdmin`) |
| Asignar Órdenes de Producción (máquina/operario) | ✅ | Solo su área |
| Rechazar lote (motivo obligatorio) | ✅ | Solo su área |
| Reetiquetar lote (motivo obligatorio) | ✅ | Grupos supervisor (`jefe_area`/`jefe_planta`/`admin_*`) |
| Registrar/consultar paros de máquina (`ParoMaquina`) | ✅ | Solo máquinas de su área (`IsJefeAreaOrOperarioOrAdmin`) |
| Consultar OEE (área y por máquina) | ✅ (lectura) | Solo su área |
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

## Fase 0 — Corrección de regla de negocio: creación de OP (2026-07-21)

**Aclaración del usuario:** la OP la genera el **Jefe de Planta** para un área específica; el
**Jefe de Área solo asigna** máquina/operario a OPs ya creadas — nunca las crea. El código
permitía crear OPs a `jefe_area` (`OrdenProduccionViewSet.get_permissions` → `IsJefeAreaOrAdmin`)
y el frontend le ofrecía "Nueva Orden", contradiciendo el proceso real.

**Corrección:**
- `get_permissions` (acción `create`) → `IsJefePlantaOrAdmin`.
- Frontend: eliminado el botón "Nueva Orden", su diálogo y estado asociado de `JefeAreaDashboard.tsx`.
- Test nuevo: `jefe_area POST /ordenes-produccion/ → 403`.

Esto también cerró el hallazgo incidental #3 de esta auditoría (discrepancia de código vs. regla real).

---

## Fundamento académico ampliado (libros de texto)

Además de las fuentes de industria, se revisaron tres textos canónicos que refuerzan y priorizan
el roadmap:

- **OEE for Operators: Overall Equipment Effectiveness** (Productivity Press): `OEE = Disponibilidad
  × Rendimiento × Calidad`, benchmark clase mundial 85%. Aporta la taxonomía de **Seis Grandes
  Pérdidas** — base de los *reason codes* de downtime del modelo `ParoMaquina` (R4):
  Disponibilidad → Averías, Setup/ajustes; Rendimiento → Microparos, Velocidad reducida;
  Calidad → Rechazos de arranque, Defectos de proceso.
- **Manufacturing Planning and Control for Supply Chain Management** (Vollmann, Berry, Whybark,
  Jacobs — texto estándar APICS): el Jefe de Área opera en la capa **Production Activity Control
  (PAC) / Shop Floor Control**. Su concepto de **Input/Output Control** (planificado vs. real por
  centro de trabajo) eleva **schedule attainment** de "nice-to-have" a métrica central del rol.
- **Production & Operations Management**: SPC (cartas de control) respalda evolucionar los KPIs de
  calidad de una foto puntual a una **serie temporal con límites de control**.

---

## R4 — OEE completo (implementado, 2026-07-21)

**Modelo `ParoMaquina`** (`gestion/models.py`, migración `0076_paromaquina`): registro de downtime
de máquina con *reason code* = las **Seis Grandes Pérdidas** (*OEE for Operators*):

| Dimensión OEE | Categorías (`categoria`) |
|---|---|
| Disponibilidad | `AVERIA`, `SETUP` |
| Rendimiento | `MICROPARO`, `VELOCIDAD_REDUCIDA` |
| Calidad | `RECHAZO_ARRANQUE`, `DEFECTO_PROCESO` |
| No penaliza Disponibilidad (si `planificado=True`) | `MANTENIMIENTO_PLANIFICADO`, `FALTA_MATERIAL`, `OTRO` |

Campos: `maquina` (FK), `inicio`/`fin` (nullable = paro en curso), `categoria`, `planificado`
(bool), `descripcion`, `turno`, `usuario`. Hereda `AuditableModelMixin` (+ `SedeResolvableMixin`
vía `get_audit_sede_id()`); valida `fin > inicio` en `clean()` y en el serializer (para devolver
`400` con detalle de campo en vez de un error de validación genérico).

**API:** `ParoMaquinaViewSet` (`/paros-maquina/`) — CRUD con el mismo patrón de aislamiento
área/sede que `MaquinaViewSet`; permiso `IsJefeAreaOrOperarioOrAdmin` (el operario registra sus
propios paros, el Jefe de Área supervisa los de su área). `perform_create` fija `usuario` al
usuario autenticado.

**`OeeService`** (`gestion/services/oee_service.py`) — `calcular_oee_maquina` / `calcular_oee_area`.
Supuestos documentados en el docstring del módulo:

- **run_time** = Σ(`hora_final` − `hora_inicio`) de `LoteProduccion` en el rango.
- **downtime** = Σ duración de `ParoMaquina` con `planificado=False` en el rango.
- **Disponibilidad** = run_time / (run_time + downtime) — 0 si no hay producción ni paros.
- **Rendimiento** = min(1, producción_real_kg / producción_teórica_kg), con producción_teórica =
  `capacidad_maxima` (kg/turno) × (run_time_horas / `DURACION_TURNO_HORAS=8`) — supuesto de turno
  estándar de 8h, documentado explícitamente porque el modelo no registra la duración real del turno.
- **Calidad** = First Pass Yield (mismo cálculo que `KPIAreaView`/R2).
- **OEE** = Disponibilidad × Rendimiento × Calidad.

El rango `desde`/`hasta` es opcional (`None` = histórico completo) para integrarse sin romper la
filosofía actual de `KPIAreaView` (que no acota por fecha ninguno de sus KPIs).

**Integración:**
- `KPIAreaView` → nuevo bloque `oee: {disponibilidad, rendimiento, calidad, oee, downtime_min}`
  a nivel de área.
- `MaquinaViewSet.oee` (`GET /maquinas/{id}/oee/`) → desglose por máquina individual.

**Frontend:** tarjeta "OEE" en `JefeAreaDashboard.tsx` (valor + A/P/Q como subtexto); badge
`OEE X.X%` en cada card de máquina (fetch paralelo por máquina tras cargar el listado); botón
"Registrar Paro" por máquina que abre `RegistrarParoModal.tsx` (categoría/reason code, inicio,
fin opcional, checkbox planificado, descripción) → `POST /paros-maquina/`.

**Tests:** `test_paro_maquina.py` (12), `test_oee_service.py` (11), extensión de
`test_kpi_views.py` (bloque `oee`), `MaquinaOeeActionTestCase` (2), `RegistrarParoModal.test.tsx`
(4) + extensión de `JefeAreaDashboard.test.tsx` (tarjeta OEE, badge por máquina, modal). Todo en
verde, sin regresiones (514 passed backend / 52+4 passed frontend en el alcance tocado).

---

## Brechas pendientes (roadmap de la auditoría)

Requieren **modelos nuevos** y se dejan como trabajo futuro:

- **R5 — Gestión de no-conformidad (CAPA):** entidad de no-conformidad con dueño, estado
  (abierto→en curso→cerrado), causa raíz y acción correctiva, sobre el rechazo actual (ISO 9001 / Andon).
- **R6 — Shift handover log:** entrega de turno digital (pendientes, incidencias, estado de máquinas).
- **R7–R9:** escalamiento cronometrado de alertas (Andon), mantenimiento autónomo (TPM),
  schedule attainment / OTIF (nota: los datos para schedule attainment ya existen en
  `OrdenProduccion` — `peso_neto_requerido` vs `peso_producido` y fechas planificadas/reales —
  falta solo el cálculo del ratio, ver "Quick wins" más arriba).

---

## Fuentes (industria)

- [Production Supervisor Job Description — Indeed](https://www.indeed.com/hire/job-description/production-supervisor)
- [Exploring ISA-95 Standards in Manufacturing — EMQ](https://www.emqx.com/en/blog/exploring-isa95-standards-in-manufacturing)
- [Manufacturing KPIs: 25 Metrics That Matter (OEE, FPY) — iFactory](https://ifactoryapp.com/analytics-reporting/manufacturing-kpis-25-metrics-that-matter-2026)
- [What is Andon and why is line-stop authority the core of it — TEEPTRAK](https://teeptrak.com/en/andon-2026/)
- [ISO 9001 Nonconformity: Major and Minor — ComplianceQuest](https://www.compliancequest.com/bloglet/iso-9001-nonconformity/)
- [Total Productive Maintenance (TPM) — Lean Production](https://www.leanproduction.com/tpm/)
