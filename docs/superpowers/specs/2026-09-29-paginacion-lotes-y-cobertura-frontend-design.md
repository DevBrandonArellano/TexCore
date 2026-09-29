# Paginación incremental de lotes, ficha de lote y cobertura backend → frontend — Diseño

**Fecha:** 29 de septiembre de 2026
**Origen:** prueba de carga de 100 usuarios del 29-sep y auditoría de rutas backend sin consumidor frontend.

---

## 1. Problema

Verificado contra el código y bajo carga:

1. **`GET /api/lotes-produccion/` devuelve todo el historial.** `LotesProduccionPagination` es opt-in (solo pagina con `?page=`) «por compatibilidad». Con ~900 lotes, bajo carga: mediana 840 ms, p99 2.4 s, 273 KB por respuesta, y crece con cada lote. Es el único endpoint que empuja el p98 global (840 ms).
2. **Cinco pantallas cargan la lista completa**, y tres calculan en el navegador sobre ella:
   - Jefe de Área: carga del día por máquina (`useJefeAreaData.ts:50`). Duplica `GET /maquinas/{id}/eficiencia/`, que ya existe y **no tiene consumidor**. Además usa `toISOString()` (día UTC): entre las 19:00 y las 24:00 de Ecuador cuenta los lotes del día siguiente. Es el mismo bug que se corrigió en el backend el 24-sep.
   - Empaquetado: bultos, peso y promedio de hoy (`EmpaquetadoDashboard.tsx:318`), con el mismo bug UTC y truncado a los 200 lotes que pide.
   - Bodeguero: muestra `lotesProduccion.length` como total.
   - `InventoryDashboard` recibe `lotesProduccion` y **no lo usa** (prop muerta, en Bodeguero y Admin de Sistemas).
3. **45 rutas del backend no tienen ninguna llamada en el frontend** (cruce automático de las 191 rutas `api/` contra `frontend/src`; el cruce inverso, 110 URLs del frontend, no encontró llamadas a rutas inexistentes). Entre ellas, cinco endpoints de trazabilidad del mismo lote, de los que el frontend solo usa uno (el QR). El modal `GenealogiaLoteModal.tsx` está construido y testeado, pero ninguna pantalla lo abre.

## 2. Alcance

**Fase A (aprobada e implementada el 29-sep; ver CHANGELOG 29-sep §6):**

1. Paginación obligatoria en el servidor y carga incremental en el frontend: páginas de 30 y las 4 primeras de una vez; el resto a medida que se navega.
2. Los cálculos del día pasan al servidor: eficiencia por máquina para el Jefe de Área (endpoint existente) y resumen del día para Empaquetado (endpoint nuevo).
3. **Ficha de lote**: una sola pantalla que integra la trazabilidad del lote (resumen, genealogía, movimientos, materias primas y costos), abierta desde todas las tablas de lotes.
4. Retiro de la prop muerta y de la compatibilidad opt-in.

**Fase B (requiere aprobación, §7):** el resto de las 45 rutas.

## 3. Decisiones de diseño

| # | Decisión | Razón |
|---|---|---|
| **D1** | El servidor **siempre** pagina `/lotes-produccion/`: `page_size` 30 por defecto, máximo 120 | Una lista sin tope crece con la operación de la planta. Se retira el opt-in, que era un parche de compatibilidad |
| **D2** | El frontend pide **bloques** de 4 páginas en **una** petición (`page_size=120`) y los muestra en páginas de 30 | Cumple «4 páginas de 30 de golpe» con una sola consulta y un solo `COUNT` en SQL Server, en lugar de cuatro |
| **D3** | **Precarga**: al entrar en la última página cargada se pide el bloque siguiente en segundo plano; saltar a una página no cargada pide solo su bloque | Carga paulatina: la navegación secuencial no espera a la red, y el salto directo no descarga los bloques intermedios |
| **D4** | Hook genérico `usePaginacionIncremental<T>` con la **misma interfaz** que `usePagination` (`currentPage`, `setCurrentPage`, `totalPages`, `paginatedItems`) | Las tablas cambian la fuente de datos sin reescribir sus controles. La obtención del bloque se inyecta como función (**Strategy**), así el hook sirve para cualquier listado paginado, no solo lotes |
| **D5** | Capa **Repository** `lib/api/lotesApi.ts` para todos los endpoints de lote | Hoy cada componente arma sus URLs y normaliza `results`/lista a mano (hay 4 variantes de `Array.isArray(x) ? x : x.results`). Un solo punto de acceso, tipado |
| **D6** | La ficha de lote declara sus pestañas en un **registro** (`{ id, etiqueta, roles, Panel }`) y cada panel carga sus datos al activarse (**lazy**) | Agregar una pestaña es una entrada en el registro, sin tocar el diálogo. Solo se muestran las pestañas cuyo endpoint permite ese rol, y abrir la ficha no dispara 4 peticiones |
| **D7** | La pestaña de genealogía **reutiliza** el contenido de `GenealogiaLoteModal` extraído a un panel; el modal se elimina | Un solo componente de genealogía. Conserva sus tests |
| **D8** | Los cálculos del día viven **solo en el servidor** (`timezone.localdate()`) | Elimina la doble implementación y el bug de día UTC |
| **D9** | Los controles de paginación se extraen a `ControlesPaginacion` | Hoy están copiados a mano dentro de cada tabla |

## 4. Backend

- `LotesProduccionPagination`: sin override de `paginate_queryset`; `page_size = 30`, `max_page_size = 120`. Respuesta siempre `{count, next, previous, results}`.
- **Nuevo** `GET /lotes-produccion/resumen-hoy/` → `{bultos, peso_total_kg, peso_promedio_kg}` sobre el mismo `get_queryset` (mismo alcance de sede, área y rol que el listado) y `timezone.localdate()`. Una sola consulta `aggregate(Count, Sum)`.
- Sin cambios en `maquinas/{id}/eficiencia/` (ya calcula con `timezone.localdate()`).

## 5. Frontend

| Pieza | Responsabilidad |
|---|---|
| `lib/api/lotesApi.ts` | Repository: `listar(params)`, `resumenHoy()`, `ficha(id)`, `genealogia(codigo, direccion)`, `movimientos(codigo)`, `materiasPrimas(id)` |
| `hooks/usePaginacionIncremental.ts` | Caché de bloques, precarga (D3), `recargar()`, reinicio al cambiar filtros |
| `components/ui/controles-paginacion.tsx` | Anterior / «Ir a» / Siguiente + indicador de carga |
| `components/lotes/FichaLoteDialog.tsx` + `components/lotes/paneles/*` | Diálogo con registro de pestañas (D6) |

**Pestañas de la ficha y permisos (los mismos que exige el backend):**

| Pestaña | Endpoint | Roles |
|---|---|---|
| Resumen | `lotes-produccion/{id}/genealogia/` | todos los que ven el lote |
| Genealogía | `corridas-produccion/trazabilidad-lote/` | operario, jefe de área, jefe de planta, admins |
| Movimientos | `inventory/lotes/{código}/movimientos/` | todos menos operario |
| Materias primas y costos | `trazabilidad/lote-produccion/` | bodeguero, jefe de planta, ejecutivo, admins |

**Pantallas que cambian:** Jefe de Área (tabla paginada, carga por máquina desde `eficiencia`), Empaquetado (tabla paginada, resumen del día desde el servidor), Operario (últimos 10 con `page_size=10`), Admin de Sistemas (`ProduccionTab` paginada), Bodeguero (total desde `count`). `BuscadorLotes` ya pagina: se alinea a 30 por página y abre la ficha.

## 6. Pruebas

- Backend: paginación siempre activa y techo de `page_size`; `resumen-hoy` (vacío, con lotes de hoy y de ayer, alcance por sede).
- Frontend: `usePaginacionIncremental` (bloque inicial, precarga al llegar al borde, salto directo, reinicio por filtros, error); ficha (pestañas por rol, carga lazy); pantallas migradas.
- Carga: repetir 100 usuarios; objetivo `/lotes-produccion/` con p95 < 300 ms.

## 7. Fase B — rutas sin consumidor frontend (pendiente de aprobación)

Quedan 41 de las 45: la Fase A integró las 4 siguientes.

Cubiertas por la Fase A: `lotes-produccion/{id}/genealogia/`, `trazabilidad/lote-produccion/`, `inventory/lotes/{código}/movimientos/`, `maquinas/{id}/eficiencia/`.

**Funcionalidad de negocio sin pantalla (propuesta: construir la UI):**
- Materia prima: `materia-prima/` (listado, alta, edición) y `materia-prima/registrar-entrada/` (recepción F0-001).
- Costeo: `lotes-produccion/{id}/obtener-costo/`.
- Kárdex a fecha de corte: `inventory/retro-kardex/`.
- Tintorería: `formula-colors/{id}/derivadas/`, `formula-colors/{id}/calcular-dosificacion/`, `ordenes-produccion/{id}/calcular-dosificacion/`, `maquinas/{id}/procesos/`.
- Producción: `ordenes-produccion/{id}/transformaciones/`, `ordenes-produccion/{id}/completar_detalles/`, `consumo-lote-detalle/`.
- Indicadores: `areas/{id}/reporte-eficiencia/`, `users/{id}/desempeno/`, `users/vendedores/`.

**Posible duplicado o código muerto (propuesta: verificar y retirar del backend):**
- `quimicos/{id}/` (misma vista que `chemicals/`, que sí se usa).
- `detalle-formulas/` (las fases se escriben anidadas en `formula-colors/`).
- `detalles-pedido/` (los detalles se escriben anidados en `pedidos-venta/`).
- `process-steps/`, `area-process-steps/`, `ordenes-produccion-subprocesos/` y sus acciones (flujo de subprocesos anterior a MES; hoy las pantallas usan `etapas-produccion/`).
- `groups/{id}/` en escritura; `paros-maquina/{id}/` y `transferencias-interarea/{id}/` en edición y borrado.

**Detalle REST sin consumidor (`retrieve`):** `inventory/stock/{id}/`, `inventory/audit-logs/{id}/`, `inventory/requerimientos-material/{id}/`, `procesos-tintoreria/{id}/`, `operaciones-produccion/{id}/`, `consumo-lote-detalle/{id}/`. Propuesta: retirar el método si ninguna pantalla lo necesitará.

**Se conservan:** `schema/` y `docs/` (OpenAPI, herramienta de desarrollo).
