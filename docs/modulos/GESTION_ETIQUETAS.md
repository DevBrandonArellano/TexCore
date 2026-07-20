# Documentación: Gestión de Etiquetas (Reetiquetado, Búsqueda por Fechas e Impresión Real)

**Fecha:** 2026-07-20
**Versión:** 1.0
**Autor:** Claude Code (Sonnet 4.6 / Sonnet 5)

---

## Resumen Ejecutivo

Se implementó un módulo de etiquetado gobernado y trazable para la Estación de Empaque, en
cinco fases incrementales (F1–F5):

- ✅ **F1** — Modelo `EventoEtiqueta`: historial inmutable de cada evento de etiqueta por lote.
- ✅ **F2** — Reimpresión idéntica gobernada (`reimprimir/`) con motivo obligatorio y auditoría
  extendida en `printing_service`.
- ✅ **F3** — Buscador dedicado por fecha/turno/código/máquina/calidad, con paginación opt-in.
- ✅ **F4** — Reetiquetado con cambio de datos (`reetiquetar/`), RBAC de supervisor, versionado
  y anulación de la etiqueta previa, con ajuste de stock reutilizando la lógica existente.
- ✅ **F5** — Impresión real: Zebra Browser Print (ZPL nativo) con fallback a PDF universal
  (cualquier impresora) y portapapeles como último recurso.

**Regla de trazabilidad invariante:** el `codigo_lote` y el QR de trazabilidad
(`trazabilidad/{codigo_lote}`) **nunca cambian**, ni siquiera al reetiquetar — solo cambian
datos secundarios (peso, calidad, presentación) y la versión de la etiqueta.

---

## Fundamento Industrial

- **Reimpresión ≠ Reetiquetado.** *Reimpresión* = copia idéntica (etiqueta dañada, perdida,
  atasco de impresora). *Reetiquetado* = los datos cambian (reclasificación de calidad,
  re-pesaje) → se anula/supersede la etiqueta anterior y se emite una nueva versión.
- **Gobernanza de reimpresión/reetiquetado**: motivo obligatorio siempre; el reetiquetado con
  cambio de datos requiere autorización de supervisor (jefe_area/jefe_planta/admin). Toda
  acción queda en auditoría inmutable (usuario, motivo, timestamp).
- **GS1 AI 10 (Batch/Lot Number)**: el número de lote es el ancla de trazabilidad — debe
  preservarse aunque se reetiquete.
- Fuentes: ver el plan original de este trabajo (`Tulip — Manufacturing Labeling`, `SG Systems —
  Label Printer Integration / MMR reprint reason codes`, `GS1 Logistic Label Guideline`).

---

## Arquitectura Implementada

### Principios SOLID Aplicados

| Principio | Implementación |
|-----------|---|
| **SRP** | `EventoEtiquetaService` solo gestiona numeración/creación de eventos de etiqueta; `RegistroLoteService` solo orquesta el registro del lote y delega el snapshot ORIGINAL. |
| **OCP** | `/pdf/etiqueta` reutiliza `PdfOutputStrategy` existente sin modificarla — el tamaño de etiqueta se controla por CSS del template, no por una clase nueva. |
| **LSP** | `EventoEtiqueta` es intercambiable en cualquier consulta de historial (`lote.etiquetas`) sin romper invariantes de unicidad. |
| **ISP** | Endpoints separados: `reimprimir/` (cualquier rol con acceso al lote) vs `reetiquetar/` (solo supervisor). |
| **DIP** | `LoteProduccionViewSet._ajustar_stock_por_cambio_peso` es reutilizado tanto por `perform_update` (PATCH directo) como por `reetiquetar/`, sin duplicar la lógica de ajuste de inventario. |

### Patrones de Diseño

| Patrón | Aplicación |
|--------|-----------|
| **Service Layer** | `gestion/services/evento_etiqueta_service.py` — numeración y creación de eventos fuera de las vistas. |
| **Strategy** | `output_strategy.py` del `printing_service` (ya existente) — `ZplOutputStrategy` / `PdfOutputStrategy`, reutilizada para el nuevo endpoint `/pdf/etiqueta`. |
| **Template Method** | `_ajustar_stock_por_cambio_peso` — mismo algoritmo de ajuste de stock invocado desde dos flujos distintos (PATCH y `reetiquetar/`). |
| **Entity + Audit Trail** | `EventoEtiqueta` es inmutable — cada fila representa un evento físico de impresión; nunca se actualiza, solo se marca `anulada=True`. |

---

## Módulos Implementados

### 1. Backend — Modelo (`gestion/models.py`)

#### Nuevo Modelo: `EventoEtiqueta`

- **Propósito:** registro inmutable del ciclo de vida de cada etiqueta física impresa.
- **Campos clave:**
  - `lote` (FK a `LoteProduccion`, `related_name='etiquetas'`)
  - `tipo_evento`: `ORIGINAL` / `REIMPRESION` / `REETIQUETADO`
  - `secuencia`: identificador de cada evento físico de impresión — **siempre creciente por
    lote** (garantiza unicidad de fila incluso entre reimpresiones idénticas).
  - `version`: versión de los **datos** de la etiqueta — se mantiene igual entre reimpresiones
    idénticas y solo se incrementa cuando un `REETIQUETADO` cambia datos.
  - `motivo` (choices: `DANIADA`, `PERDIDA`, `ATASCO`, `CORRECCION_PESO`, `RECLASIFICACION`,
    `REEMPAQUE`, `OTRO`) + `detalle_motivo` (texto libre) — obligatorio salvo `ORIGINAL`.
  - `usuario` (FK `CustomUser`, `SET_NULL`), `timestamp` (`auto_now_add`).
  - `datos_snapshot` (`JSONField`) — copia de los datos del lote en el momento de la impresión.
  - `formato`: `ZPL` | `PDF`.
  - `anula_a` (self-FK nullable) + `anulada` (bool) — cadena de versiones.
- **Constraint:** `unique_together = ('lote', 'secuencia')` — **no** sobre `version`, porque
  varias reimpresiones idénticas comparten la misma `version` de datos.
- **Índices:** `(timestamp)`, `(lote, secuencia)`.

**Migración:** `gestion/migrations/0075_evento_etiqueta.py`

> **Por qué `secuencia` y `version` son campos distintos:** si `unique_together` fuera solo
> `('lote', 'version')`, dos reimpresiones idénticas de la misma versión de datos violarían la
> constraint (ambas tendrían `version=1`). `secuencia` resuelve la unicidad del evento físico de
> impresión sin forzar a la reimpresión a "inventar" un cambio de versión que no existe.

---

### 2. Backend — Service Layer (`gestion/services/evento_etiqueta_service.py`)

#### `EventoEtiquetaService`

**Método: `registrar_original(lote, user) -> EventoEtiqueta`**
- Crea el evento `ORIGINAL` con `secuencia=1`, `version=1`.
- Invocado automáticamente por `RegistroLoteService.registrar_lote()` al crear un lote nuevo.

**Método: `registrar_reimpresion(lote, user, motivo, detalle_motivo='', formato='ZPL') -> EventoEtiqueta`**
- Copia idéntica: toma la `version` vigente del último evento y solo avanza `secuencia`.
- **Transaccional** (`@transaction.atomic`), con `select_for_update()` sobre el último evento.

**Método: `registrar_reetiquetado(lote, user, motivo, detalle_motivo='', formato='ZPL') -> EventoEtiqueta`**
- Marca `anulada=True` en el último evento vigente y crea uno nuevo con `version+1`,
  `anula_a=<evento previo>`.
- **Transaccional**, mismo patrón de `select_for_update()`.

---

### 3. Backend — Views (`gestion/views/production_views.py`, `LoteProduccionViewSet`)

**`get_queryset()` (F3 — búsqueda)**
- Filtros añadidos vía query params: `fecha_desde`/`fecha_hasta` (sobre `hora_final`, validados
  con `django.utils.dateparse.parse_date`, `400` si formato inválido o `fecha_desde > fecha_hasta`),
  `turno` (icontains), `codigo_lote` (icontains), `maquina` (id exacto), `clasificacion_calidad`
  (exacto), `presentacion` (icontains).
- `ordering_fields` incluye ahora `codigo_lote`.

**`LotesProduccionPagination` (F3 — paginación opt-in)**
- `PageNumberPagination` que **solo pagina si el cliente envía `?page=`** — preserva
  compatibilidad con "Historial Reciente" (que espera un array plano sin paginar).

**`_build_zpl_payload(lote)` / `_build_zpl_fallback(data, sello=None)`**
- Extraídos de `generate_zpl` para reutilizarse en `reimprimir/` y `reetiquetar/`.

**`@action generate_zpl`** *(sin cambios de contrato, refactorizado internamente)*
- GET `/lotes-produccion/{id}/generate_zpl/` — imprime la etiqueta con los datos actuales.

**`@action generate_pdf_label` (F5)**
- GET `/lotes-produccion/{id}/generate-pdf-label/` — passthrough a `/pdf/etiqueta` del
  microservicio. `503` si el microservicio no responde.

**`@action etiquetas`**
- GET `/lotes-produccion/{id}/etiquetas/` — historial completo de eventos del lote
  (`secuencia`, `version`, `tipo_evento`, `motivo`, `usuario`, `anulada`, `anula_a`).

**`@action reimprimir` (F2)**
- POST `/lotes-produccion/{id}/reimprimir/` — body `{motivo (requerido), detalle_motivo?, formato?}`.
- `400` si falta `motivo`. Llama a `EventoEtiquetaService.registrar_reimpresion`, reenvía al
  microservicio con `tipo_evento='REIMPRESION'` para el sello visual, y hace *fallback* al ZPL
  local si el microservicio no responde.
- Permiso: cualquier rol con acceso al lote (`operario`, `empaquetado`, `jefe_area`, `jefe_planta`, admins).

**`@action reetiquetar` (F4)**
- POST `/lotes-produccion/{id}/reetiquetar/` — body `{cambios: {...}, motivo (requerido), detalle_motivo?, formato?}`.
- `cambios` solo acepta el whitelist `CAMBIOS_REETIQUETADO_PERMITIDOS = {peso_bruto, tara,
  peso_neto_producido, clasificacion_calidad, presentacion, cantidad_metros, unidades_empaque}`
  — **nunca** `codigo_lote` ni `orden_produccion` (`400` si se intenta).
- `400` si falta `motivo` o `cambios` está vacío.
- Aplica los cambios vía `LoteProduccionSerializer(partial=True)`, reutiliza
  `_ajustar_stock_por_cambio_peso` (extraído de `perform_update`) si cambió `peso_neto_producido`,
  y llama a `EventoEtiquetaService.registrar_reetiquetado` (anula la versión previa).
- **Permiso: `IsJefeAreaOrAdmin`** (jefe_area / jefe_planta / admin_sistemas) — `403` para
  operario/empaquetado.
- Todo dentro de `@transaction.atomic`.

---

### 4. Microservicio `printing_service` (F2 + F5)

Ver detalle completo en [docs/arquitectura/MICROSERVICIO_IMPRESION.md](../arquitectura/MICROSERVICIO_IMPRESION.md).

- **`EtiquetaRequest`** extendido con `tipo_evento`, `version`, `motivo`, `usuario`, `reimpreso`
  (todos opcionales, backward-compatible).
- **`PrintAuditLog`** extendido con `usuario`, `motivo`, `tipo_evento`, `version`.
- **`etiqueta.zpl`** — sello condicional `REIMPRESION vN` / `REETIQUETADO vN`.
- **`etiqueta_label.html`** (nuevo, F5) — plantilla PDF de 100×150mm, fallback universal para
  impresoras sin ZPL nativo, servida por `POST /pdf/etiqueta` (reutiliza `PdfOutputStrategy`).

---

### 5. Frontend — Types (`frontend/src/lib/types.ts`)

**`LoteProduccion` (actualizado)**
```typescript
clasificacion_calidad?: string;
```

---

### 6. Frontend — Components

#### `ReimprimirModal.tsx` (nuevo, F2)
- Modal con selector de motivo (obligatorio) + detalle opcional.
- Al confirmar: `POST /lotes-produccion/{id}/reimprimir/` → luego `printLabel(loteId, zpl)`.

#### `ReetiquetarModal.tsx` (nuevo, F4)
- Formulario de peso neto / calidad + motivo obligatorio.
- Solo envía en `cambios` los campos que realmente difieren del valor actual del lote.
- Alerta visual: "requiere autorización de supervisor... queda registrada en auditoría".
- Al confirmar: `POST /lotes-produccion/{id}/reetiquetar/` → luego `printLabel`.

#### `BuscadorLotes.tsx` (nuevo, F3)
- Filtros: rango de fechas, turno, código de lote, calidad → `GET /lotes-produccion/?page=1&...`.
- Tabla de resultados con paginación; botón **Reimprimir** siempre visible, botón
  **Reetiquetar** solo si `useAuth().profile.role` es `jefe_area`/`jefe_planta`/`admin_sistemas`/`admin_sede`.
- Montado actualmente dentro de `EmpaquetadoDashboard.tsx`.

  > **Limitación conocida:** como `EmpaquetadoDashboard` solo se renderiza para el rol
  > `empaquetado` (ver `App.tsx`), los supervisores (que tienen sus propios dashboards) no ven
  > hoy el botón "Reetiquetar" en la práctica, aunque el endpoint y el RBAC backend ya lo exigen
  > correctamente. Pendiente: montar `<BuscadorLotes />` también en `JefeAreaDashboard.tsx` /
  > `JefePlantaDashboard.tsx`.

#### `frontend/src/lib/printing.ts` (nuevo, F5)
- `printLabel(loteId, zpl): Promise<'zebra' | 'pdf' | 'clipboard'>`
  1. Intenta `window.BrowserPrint.getDefaultDevice('printer', ...)` (Zebra Browser Print) y
     envía el ZPL directo si hay impresora disponible.
  2. Si no hay Zebra, pide `GET /lotes-produccion/{id}/generate-pdf-label/` como `blob`, abre una
     pestaña nueva y dispara `window.print()`.
  3. Si todo falla, copia el ZPL al portapapeles (`navigator.clipboard.writeText`).
- Usado por `ReimprimirModal`, `ReetiquetarModal` y el auto-print tras registrar un lote nuevo
  en `EmpaquetadoDashboard.tsx`.

---

## Flujos de Negocio

### 1. Registrar un lote nuevo (evento ORIGINAL)

```
Empacador registra lote → RegistroLoteService.registrar_lote()
    ├─ crea LoteProduccion
    ├─ EventoEtiquetaService.registrar_original(lote, user)
    │   └─ EventoEtiqueta(tipo=ORIGINAL, secuencia=1, version=1)
    └─ ajusta stock (consumo MP + producción)
    ↓
Frontend: printLabel(loteId, zpl) → Zebra / PDF / portapapeles
```

### 2. Reimprimir (copia idéntica)

```
Usuario click "Reimprimir" → ReimprimirModal exige motivo
    ↓
POST /lotes-produccion/{id}/reimprimir/ {motivo, detalle_motivo, formato}
    ├─ 400 si falta motivo
    ├─ EventoEtiquetaService.registrar_reimpresion()
    │   └─ EventoEtiqueta(tipo=REIMPRESION, secuencia+1, version=<sin cambio>)
    ├─ PrintingService.generate_zpl_label(data con sello REIMPRESION vN)
    └─ printLabel(loteId, zpl)
```

### 3. Reetiquetar (cambio de datos)

```
Jefe de Área/Planta click "Reetiquetar" → ReetiquetarModal (peso/calidad + motivo)
    ↓
POST /lotes-produccion/{id}/reetiquetar/ {cambios, motivo, detalle_motivo, formato}
    ├─ 403 si no es supervisor (IsJefeAreaOrAdmin)
    ├─ 400 si falta motivo, cambios vacío, o cambios incluye campo no permitido (p.ej. codigo_lote)
    ├─ serializer.partial_update(cambios) → guarda el lote
    ├─ _ajustar_stock_por_cambio_peso() si cambió peso_neto_producido
    ├─ EventoEtiquetaService.registrar_reetiquetado()
    │   ├─ anula el evento previo (anulada=True)
    │   └─ EventoEtiqueta(tipo=REETIQUETADO, version+1, anula_a=<previo>)
    ├─ PrintingService.generate_zpl_label(data con sello REETIQUETADO vN)
    └─ printLabel(loteId, zpl)
    ↓
✓ codigo_lote y QR de trazabilidad sin cambios; historial preserva ambas versiones
```

---

## RBAC

| Rol | Registrar lote | Reimprimir | Reetiquetar | Buscar |
|---|---|---|---|---|
| `operario` / `empaquetado` | ✓ | ✓ (motivo obligatorio) | ✗ (403) | ✓ |
| `jefe_area` / `jefe_planta` / `admin_sistemas` / `admin_sede` | ✓ | ✓ | ✓ (motivo obligatorio) | ✓ |

---

## Tests

```
gestion/tests/test_evento_etiqueta.py        # modelo EventoEtiqueta + snapshot ORIGINAL (6 tests)
gestion/tests/test_production_views.py       # reimprimir/, reetiquetar/, etiquetas/,
                                              # generate-pdf-label/, filtros F3 (57 tests en total)
printing_service/tests/unit/test_printing_endpoints.py  # /zpl/etiqueta, /pdf/etiqueta con gobernanza
frontend/src/components/empaquetado/EmpaquetadoDashboard.test.tsx  # flujo de reimpresión con modal (34 tests)
```

> Los tests de Django en este proyecto corren contra MSSQL (`.env`/`.env.test`); en entornos sin
> un servidor MSSQL accesible, se pueden ejecutar localmente contra SQLite en memoria con
> `MIGRATION_MODULES` deshabilitado (ver comentario de configuración en el historial de este
> trabajo) — es solo un shim de verificación local, no reemplaza el pipeline de CI real.

---

## Pendientes / Trabajo Futuro

- Montar `<BuscadorLotes />` (con el botón "Reetiquetar") en `JefeAreaDashboard.tsx` y
  `JefePlantaDashboard.tsx` para que los supervisores accedan a la función sin depender del
  dashboard de Empaque.
- Backfill de `EventoEtiqueta(tipo=ORIGINAL)` para lotes creados antes de esta migración (hoy
  su ausencia se puede interpretar como "v1 histórica sin evento registrado").
- Selector de impresora/formato preferido por estación en el frontend (hoy `printLabel` siempre
  intenta Zebra primero).
