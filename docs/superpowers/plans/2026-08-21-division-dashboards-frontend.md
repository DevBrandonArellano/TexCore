# Auditoría y división de los 6 dashboards "dios" del frontend (SOLID / Clean Code / ISO 25010)

> **Estado: PLANIFICADO, NO EJECUTADO.** Decisión explícita del usuario (2026-08-21): documentar el
> plan a fondo y retomarlo en otra sesión — no se tocó ningún archivo de código en esta sesión.

## Motivación real: no es el tamaño del archivo, es el re-render en cascada

Se le preguntó explícitamente al usuario si el problema era mantenibilidad o performance percibida.
Confirmó **performance**: los componentes "se llaman a cada rato y por ello recarga todo". Esto es
técnicamente preciso y merece explicarse bien, porque **dividir un archivo en varios no resuelve esto
por sí solo** — hay que hacerlo con una técnica específica.

**Cómo funciona el problema:** en cada uno de los 6 dashboards, todo el estado (`useState`) del
componente gigante vive en una sola función. React no sabe qué parte del JSX depende de qué pieza de
estado — cuando *cualquiera* de esos `useState` cambia (escribir en un buscador, abrir un modal,
tipear un campo), React vuelve a ejecutar la función completa del componente y recalcula/diffea *todo*
su árbol JSX, incluidas partes visualmente no relacionadas (otros tabs, otras tablas). Con 17-33
`useState` en un solo componente (`VendedorDashboard`: 33; `EjecutivosDashboard`: 24;
`AdminSistemasDashboard`: 17; `JefeAreaDashboard`: 19), casi cualquier interacción dispara un
re-render del archivo completo.

Casos concretos ya identificados (agravan el problema, no lo causan):
- `EjecutivosDashboard.tsx` (~línea 1038-1069): el funnel de pedidos se calcula con un IIFE **dentro
  del JSX**, sin `useMemo` — se recalcula en cada render, tenga o no los mismos datos.
- `KardexView` (dentro de `InventoryDashboard.tsx`) y `getSedeStats` (dentro de
  `AdminSistemasDashboard.tsx`): cálculos de agregación no memoizados, recalculados en cada render.
- `JefeAreaDashboard.tsx` (línea ~368): fetch de OEE por máquina dentro de un `Promise.all` anidado
  (patrón N+1) — esto es lentitud real de red, no de render, y **es un problema de backend/endpoint,
  no de este archivo**. Se deja anotado como hallazgo relacionado pero **fuera de alcance** de este
  plan (candidato a un endpoint batch `/maquinas/oee-batch/` en otra sesión).

**Por qué "solo mover código a otro archivo" NO alcanza:** si `EjecutivosDashboard.tsx` se parte en
`ResumenTab.tsx`, `ProduccionTab.tsx`, etc. pero se siguen renderizando como `<ResumenTab prop={x} />`
sin más, React igual re-renderiza `ResumenTab` cada vez que el padre se re-renderiza — porque por
defecto un componente hijo se re-renderiza cuando su padre se re-renderiza, sin importar si sus props
cambiaron. La división por sí sola es necesaria pero no suficiente. Para que el split realmente frene
la cascada de re-renders hacen falta **3 técnicas aplicadas juntas**, en cada fase:

1. **Extraer cada Tab/Panel/View a su propio componente** (lo que ya describe este plan) — es el
   prerrequisito: sin límite de componente no hay nada que memoizar.
2. **Envolver esos componentes con `React.memo(...)`** — así React compara las props antes de
   re-renderizar, y si no cambiaron, se salta el re-render de ese subárbol completo.
3. **Pasar props con referencia estable**: los callbacks que hoy se definen inline en el JSX
   (`onClick={() => handleX(id)}`) deben envolverse en `useCallback` dentro de los hooks extraídos, y
   los objetos/arrays derivados deben venir de un `useMemo` — de lo contrario `React.memo` no sirve de
   nada, porque cada render crea una función/objeto nuevo y las props "cambian" aunque los datos sean
   los mismos.

Sin los puntos 2 y 3, el split logra el objetivo de **mantenibilidad** (SOLID/ISO 25010, la
motivación original) pero **no** resuelve la lentitud. Este plan apunta a ambos a la vez.

## Contexto

Tras dividir los 4 archivos monolíticos del backend (sesión anterior, ejecutado y verificado:
865/865 tests), el mismo problema existe en el frontend — y ahí los archivos son más grandes
todavía. Ninguno de estos 6 tiene plan previo:

| Archivo | Líneas | Líneas del componente "gigante" |
|---|---|---|
| `vendedor/VendedorDashboard.tsx` | 1880 | ~1513 (componente principal) |
| `ejecutivos/EjecutivosDashboard.tsx` | 1506 | ~1267 |
| `admin-sistemas/AdminSistemasDashboard.tsx` | 1269 | ~1200 |
| `jefe-planta/ManageOrdenesProduccion.tsx` | 1141 | ~627 (resto ya modularizado) |
| `admin-sistemas/InventoryDashboard.tsx` | 1096 | ya son 6 componentes en 1 archivo |
| `jefe-area/JefeAreaDashboard.tsx` | 1019 | ~735 |

A diferencia del refactor de backend (100% mecánico, byte-idéntico), este es un refactor real:
mover `useState`/`useEffect` a hooks y JSX a sub-componentes cambia el árbol de módulos aunque el
comportamiento deba quedar igual. Por eso la verificación se apoya en los **tests ya existentes**
(994 tests, muchos ya organizados por sub-dominio — `Component.dominio.test.tsx` — anticipando
exactamente esta división) más `tsc --noEmit` y una prueba manual en navegador por archivo, tal
como exige `CLAUDE.md` para cambios de frontend.

## Radio de impacto verificado (grep de imports reales, no solo lectura de agentes)

Ningún agente de exploración reportó esto — se verificó aparte antes de cerrar el plan. Grep de
`import.*{...}.*from` sobre todo `frontend/src/` confirma quién renderiza cada uno de los 6
dashboards **fuera de su propia carpeta**:

| Dashboard | Consumidor(es) externos | Vía |
|---|---|---|
| `VendedorDashboard` | `App.tsx` | ruta, sin props |
| `AdminSistemasDashboard` | `App.tsx` | ruta, sin props |
| `JefeAreaDashboard` | `App.tsx` | ruta, sin props |
| `ManageOrdenesProduccion` | `jefe-planta/JefePlantaDashboard.tsx` | componente hijo |
| `EjecutivosDashboard` | `App.tsx` **y** `admin-sede/AdminSedeDashboard.tsx` | `<EjecutivosDashboard isAdminSede={true} />` |
| `InventoryDashboard` | `admin-sistemas/AdminSistemasDashboard.tsx` **y** `bodeguero/BodegueroDashboard.tsx` | props: `{ sedeId?, productos, bodegas, lotesProduccion, proveedores, onDataRefresh }` |

Los 2 consumidores no obvios (`AdminSedeDashboard.tsx` para Ejecutivos, `BodegueroDashboard.tsx`
para Inventory) usan el componente como caja negra por su interfaz pública de props — **no**
importan nada interno (ni modales, ni tabs, ni tipos). Mientras la Fase 1 y la Fase 2 preserven el
nombre exportado, la forma de export (`export function X`) y la firma de props exacta de
`InventoryDashboard`/`EjecutivosDashboard`, estos 2 consumidores no se ven afectados — pero
**ambos tienen su propio `.test.tsx`** (`BodegueroDashboard.test.tsx`,
`AdminSedeDashboard.test.tsx`) y se agregan a la verificación de Fase 1 y Fase 2 como red de
seguridad extra.

Para los otros 4 dashboards, cada uno tiene **un solo consumidor externo** (confirmado por grep),
consistente con lo que reportaron los agentes.

## Investigación previa (3 agentes de exploración, verificada con spot-checks)

**No existe** ninguna carpeta `hooks/` ni `components/` anidada en todo `frontend/src/components/`
— la convención real y ya probada del repo es **archivos hermanos en la misma carpeta** por
responsabilidad, cada uno con su `.test.tsx`: `jefe-area/{ManageMaquinas,ManageLineas,
RegistrarParoModal,ComponenteMezclaPanel}.tsx`, `admin-sistemas/{Manage*,TransformationView}.tsx`,
`ejecutivos/DrillDownModals.tsx`, `bodeguero/{EditarMovimientoDialog,AuditoriaDialog,...}.tsx`. El
plan reutiliza esa convención — no introduce carpetas nuevas, salvo la única excepción justificada
más abajo.

**No existe** ninguna capa de servicio API por dominio (`lib/api/*.ts`) — todo componente llama
`apiClient` directo. Tampoco existe ningún custom hook compartido (`frontend/src/hooks/` no existe).

**Duplicación cross-archivo confirmada** (relevante para Clean Code / DRY):
- Paginación manual (`currentXPage`, `totalXPages`, `slice`) duplicada casi idéntica en
  `AdminSistemasDashboard.tsx`, `ManageOrdenesProduccion.tsx`, `VendedorDashboard.tsx` (x2, clientes
  y pedidos), `JefeAreaDashboard.tsx` (x2, alertas y lotes) — **6+ implementaciones** del mismo patrón.
- Descarga de blob/CSV (`exportToCSV`, `downloadBlob`, `descargarBlob`) duplicada en
  `InventoryDashboard.tsx` (x2, dentro del mismo archivo) y `EjecutivosDashboard.tsx`.
- Cálculo de total de pedido (`calculateOrderTotal`/`getPedidoTotal`) duplicado entre
  `VendedorDashboard.tsx`, `ejecutivos/DrillDownModals.tsx` y de nuevo inline en la tabla de
  `VendedorDashboard.tsx`.
- `StockItem` (interfaz) duplicada casi idéntica entre `InventoryDashboard.tsx` y
  `DrillDownModals.tsx`.

**Código muerto confirmado por spot-check** (no solo hallazgo de agente, verificado con grep):
- `AdminSistemasDashboard.tsx:99` — `activeTab`/`setActiveTab` declarado, nunca leído en ningún otro
  lado del archivo (el `Tabs` usa `defaultValue`, no `value={activeTab}`).
- `EjecutivosDashboard.tsx:65` — `LineChart` importado de `recharts`, nunca usado en JSX.
- `EjecutivosDashboard.tsx:80` — `OrdenCompraSugerida`, `RequerimientoMaterial` importados de
  `lib/types`, nunca referenciados en el archivo.

## Mapeo a SOLID / Clean Code / ISO 25010

El criterio de división en los 6 archivos es siempre el mismo (Single Responsibility aplicado 3
veces por archivo):

1. **Estado + efectos + llamadas API** → un custom hook `use<Dominio>.ts`, hermano del componente.
   Aplica SRP (una razón de cambio: "cómo se obtienen/mutan estos datos") y DIP (el componente ya no
   conoce `apiClient`/endpoints, depende de la interfaz del hook).
2. **Cálculos puros / formateo / validaciones** mezclados en el JSX → funciones puras en `utils.ts`
   hermano. Mejora Testability (función pura testeable sin montar el componente) y elimina
   duplicación (Clean Code DRY).
3. **Bloques JSX grandes y autocontenidos** (modales, tabs, paneles, tablas, formularios) → componentes
   hermanos `<Nombre>.tsx`, recibiendo datos/callbacks por props. Aplica OCP (un tab nuevo se agrega
   sin tocar el orquestador) y reduce el archivo contenedor a puro *composition root*.

Mapeo a características de **ISO/IEC 25010** — el eje central es **Mantenibilidad**, con estas
subcaracterísticas mejorando directamente: *Modularidad* (cada archivo, una responsabilidad),
*Reusabilidad* (hooks/utils/componentes reusables entre dashboards, ej. paginación), *Analizabilidad*
(ubicar código deja de requerir leer 1000+ líneas), *Modificabilidad* (cambiar un tab no arriesga
romper otro), *Testabilidad* (los tests ya divididos por sub-dominio hoy montan igual el archivo de
1000+ líneas completo — tras el split podrán testear la unidad real). *Adecuación funcional* y
*Fiabilidad* son las que hay que **proteger, no mejorar**: cero cambios de comportamiento observable,
verificado con la suite existente.

## Las 2 únicas piezas nuevas compartidas (excepción justificada a "sin carpetas nuevas")

Dado que la paginación se duplica en 5+ archivos y la descarga de blobs en 2 (con más candidatos
futuros), crear estas 2 piezas evita repetir la misma extracción 5 veces:

- **`frontend/src/hooks/usePagination.ts`** (nuevo, primer hook compartido del repo) — hook genérico
  `usePagination<T>(items: T[], itemsPerPage: number)` que reemplaza los 6+ bloques manuales de
  `currentPage`/`totalPages`/`slice`. Se crea en la Fase 2 (Inventory, que ya tiene el patrón en
  `StockView`) y se reutiliza en las fases siguientes.
- **`frontend/src/lib/downloadBlob.ts`** (nuevo, junto a `errorUtils.ts`/`apiError.ts` — no es carpeta
  nueva, es un archivo más en `lib/` ya existente) — función `downloadBlob(blob, filename)` que
  reemplaza `exportToCSV`/`downloadBlob`/`descargarBlob`. Se crea en la Fase 2.

Todo lo demás sigue la convención de archivo-hermano ya usada en el repo — sin `hooks/` locales por
carpeta, sin capa de servicio API nueva (fuera de alcance: introducir `lib/api/*.ts` sería un cambio
de convención mayor no pedido, y ninguno de los 6 archivos lo usa hoy).

## Orden de ejecución (menor a mayor riesgo/entrelazamiento)

1. **`EjecutivosDashboard.tsx`** — ya tiene modales extraídos (`DrillDownModals.tsx`) y utils fuera
   del componente (`fmt`, `abreviar`, `toNum`, `toArray`, `descargarBlob`); solo falta extraer los 7
   `TabsContent` a componentes y las llamadas a 5 custom hooks. Valida la mecánica del patrón "Tab →
   componente" con el menor riesgo.
2. **`InventoryDashboard.tsx`** — ya son 6 componentes en el mismo archivo (`StockView`,
   `RegistrarEntradaView`, `TransferView`, `KardexView`, `ReportesView` + el orquestador); "solo"
   hay que promoverlos a archivos propios y extraer 2-3 hooks (`useKardex`, `useReportesExport`).
   Aquí nacen `usePagination` y `downloadBlob`.
3. **`ManageOrdenesProduccion.tsx`** — 3 sub-componentes ya delimitados dentro del archivo
   (`RequisitosMaterialesDialog`, `RegistrarLoteDialog`, `OrdenDetalleSheet`); promoverlos + extraer
   el formulario de crear/editar orden + utils de validación/payload.
4. **`JefeAreaDashboard.tsx`** — 2 sub-componentes ya extraídos (`MaquinaDialog`,
   `MaquinaCardInline`); falta partir el resto (~735 líneas) en 5 paneles + 1 hook de datos.
5. **`AdminSistemasDashboard.tsx`** — el más "orquestador puro": ~450 líneas son 20 handlers CRUD
   (fetch+POST/PUT/DELETE) que alimentan 12 componentes hijos ya modulares. División principal: por
   hooks de dominio, no por JSX (hay poco JSX propio para extraer).
6. **`VendedorDashboard.tsx`** — el más grande y más entrelazado (lógica de negocio inline en el
   JSX, duplicaciones, `any` sin tipar en `PagoReversionModal`). Se hace último, aplicando todos los
   patrones ya probados en 1-5.

Cada fase es un commit independiente y revertible (los commits los hace el usuario, no yo).

---

## Fase 1 — `ejecutivos/EjecutivosDashboard.tsx`

**Extraer a hooks** (todos en `frontend/src/components/ejecutivos/`, siguiendo el naming `use<Dominio>.ts`):
- `useDashboardEjecutivoData.ts` — `sedes`, `filtroSedeId`, `kpiEjecutivo`, `loading`, `refreshing`,
  `autoRefresh`, `fetchSedes`, `fetchData` (líneas 281-338 aprox.).
- `useProduccionEjecutivo.ts` — `produccionResumen`, `tendencia`, `rangoTendencia`,
  `agrupacionTendencia`, `datosTendenciaProcesados`.
- `useStockEjecutivo.ts` — `alertas`, `stock`, `busquedaAlertas`, `bodegaSeleccionada`,
  `stockPorBodega`, `alertasFiltradas`, `topAlertas`.
- `useVentasEjecutivo.ts` — `clientes`, `pedidos`, `ventasPorVendedor`, `topClientesGerencial`,
  `topDeudores`, `distribucionPago`, `totalVentas`, `cuentasPorCobrar`, `carteraVencida`,
  `limiteCartera`, estado de los 4 modales drill-down.
- `useExportesGerenciales.ts` — `reportFechas`, `descargando`, la función genérica `exportar` (línea
  466) + los 6 wrappers (`exportVentas`, `exportTopClientes`, `exportDeudores`, `exportOrdenes`,
  `exportLotes`, `exportTendencia`). Usa `downloadBlob` de `lib/` (Fase 2) — si Fase 2 corre después,
  dejar el `descargarBlob` local tal cual por ahora y unificar cuando exista `lib/downloadBlob.ts`.

**Extraer a componentes** (`<Tab>.tsx` hermanos, reciben los datos ya calculados por props):
`ResumenTab.tsx`, `ProduccionTab.tsx`, `StockTab.tsx`, `VentasTab.tsx`, `ReportesTab.tsx`. Los tabs
`aprobaciones`/`auditoria` ya delegan 100% a `MovementApproval`/`AuditLogViewer` — no requieren
extracción, solo quedan como `<TabsContent>` de una línea en el orquestador.

**Fixes de limpieza durante el paso** (no antes — se hacen junto con la extracción del bloque que
tocan, no como cambio aislado):
- Reemplazar el IIFE inline del funnel de pedidos (líneas 1038-1069) por un `useMemo` dentro de
  `useVentasEjecutivo.ts` — hoy recalcula en cada render sin memoizar.
- Quitar `LineChart` del import de `recharts` (no usado).
- Quitar `OrdenCompraSugerida`, `RequerimientoMaterial` del import de `lib/types` (no usados).
- `StockItem` — usar el tipo ya exportado por `DrillDownModals.tsx` en vez de la copia duplicada.

**Verificación**: `EjecutivosDashboard.test.tsx` (36 tests) + `EjecutivosDashboard.reportes.test.tsx`
(12 tests) deben seguir en verde sin modificarse (son pruebas de caja negra sobre el componente
completo). **Preservar exactamente** `export function EjecutivosDashboard({ isAdminSede = false }:
EjecutivosDashboardProps)` — `admin-sede/AdminSedeDashboard.tsx` consume esa firma; correr también
`AdminSedeDashboard.test.tsx` como red de seguridad extra. `tsc --noEmit` limpio.

---

## Fase 2 — `admin-sistemas/InventoryDashboard.tsx`

**Nuevas piezas compartidas** (ver sección anterior): `frontend/src/hooks/usePagination.ts`,
`frontend/src/lib/downloadBlob.ts`.

**Promover a archivos propios** (ya son funciones delimitadas en el archivo, solo mover +
ajustar imports): `StockView.tsx`, `RegistrarEntradaView.tsx`, `TransferView.tsx`, `KardexView.tsx`,
`ReportesView.tsx` — los 5 en `admin-sistemas/`, junto a `InventoryDashboard.tsx` (que queda como
orquestador de `Tabs` + fetch de `stock` top-level, ~55 líneas).

**Extraer a hooks**: `useKardex.ts` (filtros + fetch + cálculo de saldo acumulado + CSV — el bloque
más denso, líneas 377-768) y `useReportesExport.ts` (loading map + `handleExport`, usa
`downloadBlob`).

**Extraer a utils** (`admin-sistemas/inventoryUtils.ts` o junto a `KardexView.tsx`):
`normalizeBodegaKey`, cálculo de saldo acumulado como función pura, `TransferView.validate()`.

**Verificación**: `InventoryDashboard.test.tsx` (31 tests) + `InventoryDashboard.reportes.test.tsx`
(10 tests) en verde. **Preservar exactamente** la firma
`export function InventoryDashboard({ sedeId, productos, bodegas, lotesProduccion, onDataRefresh,
proveedores }: {...})` — tanto `AdminSistemasDashboard.tsx` como `bodeguero/BodegueroDashboard.tsx`
consumen esas props; correr también `BodegueroDashboard.test.tsx` como red de seguridad extra.
`tsc --noEmit` limpio.

---

## Fase 3 — `jefe-planta/ManageOrdenesProduccion.tsx`

**Promover a archivos propios**: `RequisitosMaterialesDialog.tsx`, `RegistrarLoteDialog.tsx`,
`OrdenDetalleSheet.tsx` (ya delimitados, líneas 53-513 del archivo actual).

**Extraer a componente nuevo**: `OrdenFormDialog.tsx` — el formulario de crear/editar orden
(líneas ~730-876), hoy inline en el componente principal.

**Extraer a utils** (`jefe-planta/ordenUtils.ts`): `toLocalDatetimeInput` (ya es función pura, solo
mover), `getOrdenVencimientoStatus` (unifica el cálculo de `isOverdue`/`isToday` duplicado en 2
lugares), `estadoBadge`/`prioridadBadge` (unifica el mapeo duplicado entre `OrdenDetalleSheet` y la
tabla), `buildOrdenPayload` (extrae la transformación de `formData` a payload de `handleSubmit`),
`validate()` del formulario.

**Reusar `usePagination`** (Fase 2) para `filteredOrdenes`/`paginatedOrdenes`, eliminando la
duplicación con `AdminSistemasDashboard.tsx`.

**Fix de limpieza confirmado** (verificado con grep, no solo hallazgo de agente): `Textarea` se
importa en la línea 15 y no se usa en ningún otro lado del archivo — eliminar el import al tocar
el bloque de imports.

**Verificación**: `ManageOrdenesProduccion.test.tsx` (11 tests) + `ManageOrdenesProduccion.crud.test.tsx`
(30 tests) en verde — su organización por `describe` (tabla/diálogos/sheet/CRUD/paginación) ya
refleja la división propuesta, buena señal de que el split es correcto. `tsc --noEmit` limpio.

---

## Fase 4 — `jefe-area/JefeAreaDashboard.tsx`

**Ya extraídos, sin cambios**: `MaquinaDialog.tsx`, `MaquinaCardInline.tsx` — moverlos a archivos
propios (hoy viven dentro de `JefeAreaDashboard.tsx`, líneas 40-283) sin alterar su contenido.

**Extraer a componentes**: `KpiSection.tsx` (5 KPI cards), `OrdenesAsignacionPanel.tsx` (panel de
asignación de órdenes a máquina/operario), `MaquinasPorLineaPanel.tsx` (el bloque más complejo —
agrupación de máquinas por línea, usa `MaquinaCardInline`), `AlertasInventarioPanel.tsx`,
`LotesRecientesTable.tsx`.

**Extraer a hooks**: `useJefeAreaData.ts` (los 7 endpoints en paralelo + cálculo de carga por
máquina + OEE de `fetchDashboardData`, líneas 322-368), `useMaquinaActions.ts`
(`handleEditMaquina`, `handleToggleEstadoMaquina`, `handleRechazarLote`).

**Extraer a utils** (`jefe-area/maquinaUtils.ts`): `claseSeveridadOee` (ya es función pura, solo
mover), `agruparMaquinasPorLinea` (extrae la lógica del `useMemo` `gruposPorLinea`).

**Reusar `usePagination`** para alertas y lotes recientes (hoy duplicado literal 2 veces en el mismo
archivo, líneas 452-464).

**Fix de limpieza al tocar `handleRechazarLote`**: hoy usa `window.prompt`/`window.alert` en vez del
`toast` que usa el resto del archivo — inconsistencia de UX que un agente detectó; homologar a
`toast` al mover la función (no antes, junto con la extracción).

**Verificación**: `JefeAreaDashboard.test.tsx` (56 tests, único archivo — no está pre-dividido como
los anteriores, así que esta fase es la primera donde el test no "guía" la división) en verde.
`tsc --noEmit` limpio.

---

## Fase 5 — `admin-sistemas/AdminSistemasDashboard.tsx`

Es distinto a los anteriores: la mayoría de las 1200 líneas del componente principal son handlers
CRUD (fetch + POST/PUT/DELETE), no JSX. La división es principalmente por **hooks de dominio**, uno
por cada entidad de catálogo, todos en `admin-sistemas/`:

- `useSedesYGrupos.ts` — `sedes`, `groups`, `sedesFetchDone`, `fetchGlobalData`,
  `handleSedeCreate/Update/Delete`, `handleAreaCreate/Update/Delete` (Área depende de sede).
- `useSedeSpecificData.ts` — el resto de los 11 fetches paralelos (`users, productos, quimicos,
  bodegas, ordenesProduccion, lotesProduccion, formulasColor, pedidosVenta, clientes, proveedores`)
  + sus handlers CRUD correspondientes (agrupables por sub-hooks si el archivo resultante es
  demasiado grande — evaluar al implementar, no partir preventivamente).
- `useProductionPagination.ts` — paginación de producción, o directamente `usePagination` (Fase 2)
  si el shape de datos calza sin adaptar.

**Extraer a componentes**: `SedesSidebar.tsx` (sidebar de selección de sede), `OverviewTab.tsx` (tab
resumen), `ProduccionTab.tsx` (tab producción con su tabla paginada), `RolesPanel.tsx` (el bloque
inline de "Roles" dentro de la sub-tab de Gestión, líneas 1234-1256 — el único JSX de negocio ahí
que no delega ya a un `Manage*.tsx`).

**Extraer a utils** (`admin-sistemas/sedeUtils.ts`): `getSedeStats` (cálculo de conteos por sede),
`getData` (normalización de respuesta paginada vs array — revisar si ya existe algo equivalente en
`lib/` antes de duplicar), `showApiError` (hoy es función suelta en el archivo, moverla a `lib/` si
se usa en más de un dashboard tras el split, o a un `utils.ts` local si es exclusiva de este).

**Fix de limpieza**: eliminar el estado muerto `activeTab`/`setActiveTab` (confirmado sin uso) al
tocar la sección donde se declara — no antes, para no mezclar un cambio de comportamiento con el
resto de fases ya en curso.

**Tipo `Group` local** (línea 63-66) — evaluar si moverlo a `lib/types.ts` (si se termina usando
desde el hook + `RolesPanel.tsx`) o dejarlo junto al hook que lo use.

**Verificación**: `AdminSistemasDashboard.test.tsx` (96 tests, un único `describe` monolítico — igual
que Fase 4, no hay pre-división en el test) en verde. `tsc --noEmit` limpio.

---

## Fase 6 — `vendedor/VendedorDashboard.tsx`

El más grande y el que menos separación tiene hoy.

**Promover a archivos propios** (ya son funciones delimitadas): `AnularPedidoModal.tsx`,
`EditarPedidoModal.tsx`, `HistorialPedidoModal.tsx`, `PagoReversionModal.tsx` (líneas 52-363).

**Extraer a componentes nuevos**: `NuevaVentaDialog.tsx` (formulario de venta nueva, líneas
~873-1109), `ClienteDetailDialog.tsx` (expediente de cliente con sub-tabs internos, líneas
~1680-1847).

**Extraer a hooks**: `useClientesVendedor.ts`, `usePedidosVendedor.ts`, `usePagosCliente.ts`,
`useReportesVendedor.ts` (usa `downloadBlob` de Fase 2).

**Extraer a utils** (`vendedor/pedidoUtils.ts` o compartido si se unifica con Ejecutivos —
evaluar al implementar): `parseFechaPedido` (ya es función pura, solo mover), unificar
`calculateOrderTotal`/el cálculo inline duplicado en la tabla (líneas 1011-1013 y 1531-1537) en una
sola función, `calcularDiasMora`, `normalizarInputNumerico` (unifica los 2 casi-idénticos de peso y
precio_unitario), `calcularPorcentajeCredito`.

**Fix de tipado** (al tocar `PagoReversionModal.tsx`): reemplazar `pago: any | null` por un tipo
concreto — es el único `any` sin tipar detectado en los 6 archivos.

**Reusar `usePagination`** para clientes y pedidos (hoy 2 implementaciones manuales en el mismo
archivo).

**Verificación**: los 6 archivos de test (`VendedorDashboard.test.tsx`,
`.cliente.test.tsx`, `.cobranza.test.tsx`, `.anulacion.test.tsx`, `.detalle.test.tsx`,
`.sinvendedor.test.tsx` — 97 tests en total, ya organizados por dominio funcional exactamente como
se divide el código) en verde sin modificarlos. `tsc --noEmit` limpio.

---

## Prácticas transversales (las 6 fases)

1. **Comportamiento observable idéntico.** Ningún fix de bug ni mejora de UX salvo los 4 explícitamente
   señalados arriba (estado muerto, imports muertos, `window.alert`→`toast`, `any`→tipo concreto) —
   y esos se hacen *en el mismo paso* que ya toca esa línea, no como cambios sueltos.
2. **Props explícitas, no context nuevo.** Los componentes extraídos reciben datos y callbacks por
   props (patrón ya usado en `MaquinaDialog`, `RequisitosMaterialesDialog`, etc.) — no se introduce
   Context API ni estado global nuevo.
3. **Todo componente Tab/Panel/View extraído se envuelve en `React.memo(...)`** — sin esto, el split
   no logra el objetivo de performance explicado arriba, solo el de mantenibilidad.
4. **Todo callback pasado como prop a un componente memoizado va en `useCallback`**, y todo
   objeto/array derivado que se pase como prop va en `useMemo` — dentro del hook de dominio
   correspondiente, no en el componente. Regla práctica: si un componente está envuelto en
   `React.memo`, cada prop que reciba debe poder trazarse a un `useState`/`useMemo`/`useCallback`
   estable, nunca a un literal creado inline en cada render del padre.
5. **Nombres de hook siempre `use<Dominio>.ts`**, siguiendo la convención de React; nombres de
   componente siempre `PascalCase.tsx`, como ya hace el 100% del repo.
6. **No commitear** — cada fase queda lista para que el usuario revise y commitee cuando quiera (ver
   memoria `no-commit-no-push`).

## Verificación por fase

1. `cd frontend && npx tsc --noEmit` → 0 errores.
2. Los `.test.tsx` **ya existentes** de ese dashboard (no se reescriben, son caja negra sobre
   comportamiento) → todos en verde. Si algún test importa un símbolo movido (ej. un sub-componente
   que antes no se exportaba y ahora sí), ajustar el import, nunca la aserción.
3. `npm test -- --run` completo al cerrar cada fase → mismo conteo total de tests que el baseline de
   esta sesión (994) — ningún test debe desaparecer ni fallar por el split.
4. **Antes de dar una fase por cerrada**: levantar el dev server (`npm run dev` o el stack Docker ya
   levantado, `docker-compose ... up -d frontend`) y probar manualmente el flujo principal del
   dashboard tocado en el navegador — tal como exige `CLAUDE.md` para cambios de frontend. Reportar
   explícitamente qué se probó.
5. **Verificación específica de performance (el motivo real de este plan)**: con React DevTools
   instalado en el navegador, pestaña "Profiler" → activar "Highlight updates when components render"
   → grabar una interacción típica del dashboard (escribir en el buscador, abrir un modal, tipear un
   campo de formulario) **antes** de la fase (contra el archivo monolítico actual, como baseline) y
   **después** de la fase. Confirmar que tras el split, esa interacción ya NO resalta como
   re-renderizados los componentes/tabs no relacionados (ej. escribir en el buscador de Clientes en
   `VendedorDashboard` no debe re-renderizar el tab de Pedidos). Si algo sigue re-renderizando de más,
   revisar el punto 4 de prácticas transversales (props no memoizadas) antes de dar la fase por
   cerrada — es la causa más común de que `React.memo` "no funcione".
6. Al cerrar las 6 fases: actualizar `CHANGELOG.md` con el resumen (mismo formato usado para el
   refactor de backend) y dejar una nota en memoria del proyecto.

## Archivos críticos de referencia

- `frontend/src/components/ejecutivos/DrillDownModals.tsx` y su test — el precedente más cercano al
  patrón a replicar (componentes + tipos extraídos a archivo hermano, testeados de forma aislada).
- `frontend/src/components/jefe-area/{ManageMaquinas,RegistrarParoModal}.tsx` — ejemplo de
  componente hermano con su propio test, en la misma carpeta que se va a tocar en Fase 4.
- `frontend/src/lib/{errorUtils,apiError}.ts` — convención ya usada para funciones puras
  compartidas en `lib/`, a replicar en `lib/downloadBlob.ts`.
- `frontend/src/lib/types.ts` (457 líneas) y `frontend/src/types/produccion.ts` — las dos fuentes de
  tipos de dominio existentes; no crear una tercera.
