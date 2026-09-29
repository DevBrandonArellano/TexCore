# Plan — Paginación incremental de lotes y ficha de lote (Fase A)

**Estado:** completado el 29-sep-2026 (15/15 pasos). Además se unificaron los 18 controles de paginación duplicados.

Spec: `docs/superpowers/specs/2026-09-29-paginacion-lotes-y-cobertura-frontend-design.md`

Cada paso: prueba primero (roja), implementación, prueba verde. Backend en SQL Server (`scripts/run_backend_tests.sh`); frontend con `npx tsc --noEmit` y `npm test`.

## Backend

1. **Paginación obligatoria.** Test: `GET /lotes-produccion/` sin parámetros devuelve `{count, results}` con 30 filas; `page_size=500` se acota a 120. Quitar el override opt-in de `LotesProduccionPagination`; `page_size=30`, `max_page_size=120`. Ajustar los tests que esperaban lista plana.
2. **`resumen-hoy`.** Tests: sin lotes → ceros; lotes de hoy y de ayer → solo hoy; lote de otra sede no cuenta. Acción `@action(detail=False)` sobre `self.get_queryset()`, una sola `aggregate`.

## Frontend — cimientos

3. **`lib/api/lotesApi.ts`** (Repository) con tipos `PaginaLotes`, `ResumenHoyLotes`, `FichaLote`, `MovimientoLote`, `CadenaMateriasPrimas`. Tests con `apiClient` mockeado: URL y parámetros de cada método.
4. **`hooks/usePaginacionIncremental.ts`.** Tests: bloque inicial (1 petición, 4 páginas); precarga al entrar en la última página del bloque; salto a una página no cargada pide solo su bloque; `resetKey` vacía la caché; error expuesto; `recargar()`.
5. **`components/ui/controles-paginacion.tsx`.** Tests: deshabilitado en los bordes, «Ir a» valida el rango, indicador de carga.

## Frontend — ficha de lote

6. Extraer el contenido de `GenealogiaLoteModal` a `components/lotes/paneles/PanelGenealogia.tsx` (conserva y migra sus tests). Eliminar el modal.
7. Paneles `PanelResumen`, `PanelMovimientos`, `PanelMateriasPrimas` (carga al montarse). Tests: carga, vacío, error.
8. `components/lotes/FichaLoteDialog.tsx` con registro de pestañas por rol. Tests: pestañas visibles por rol; solo el panel activo se monta.

## Frontend — pantallas

9. Jefe de Área: `LotesRecientesTable` con el hook y botón «Ver ficha»; `useJefeAreaData` deja de pedir lotes y toma la carga por máquina de `maquinas/{id}/eficiencia/`.
10. Empaquetado: tabla con el hook, resumen del día desde `resumen-hoy`, `BuscadorLotes` a 30 por página y «Ver ficha».
11. Operario: últimos 10 con `page_size=10` y «Ver ficha».
12. Admin de Sistemas: `ProduccionTab` paginada y «Ver ficha»; `useSedeSpecificData` deja de cargar lotes.
13. Bodeguero: total desde `count` (`page_size=1`); quitar la prop muerta `lotesProduccion` de `InventoryDashboard` y sus dos llamadores.

## Cierre

14. Suites completas (backend en SQL Server, frontend, `tsc`, flake8 del CI); cobertura frontend ≥ umbrales de `vite.config.ts`.
15. Prueba de carga de 100 usuarios: `/lotes-produccion/` p95 < 300 ms. Actualizar `scripts/loadtest/README.md`, CHANGELOG y `graphify update .`.
