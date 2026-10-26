# Planes y especificaciones (superpowers)

> **Revisado y depurado el 14-oct-2026** contra el código de la rama `MES`. Los 22 planes ya terminados
> se **eliminaron**: su contenido estaba cumplido en el código y narrado en `CHANGELOG.md`. Esta tabla
> queda como registro de qué planes existieron y dónde está hoy el detalle de cada uno.

Qué hay ahora en cada carpeta:

- `plans/`: **solo los planes con trabajo pendiente.** Hoy, uno.
- `specs/`: el diseño acordado antes de implementar (el «qué» y el «por qué»). Se conservan los 9.

Dónde vive lo demás: el historial de lo ejecutado está en `CHANGELOG.md`, las decisiones de arquitectura
en `docs/arquitectura/ADR/`, los riesgos en `docs/requerimientos/REGISTRO_RIESGOS.md` y la relación
prueba ↔ requisito en `docs/matriz_trazabilidad_pruebas.md`.

## Plan abierto

| Plan | Tema | Qué falta |
|---|---|---|
| `plans/2026-08-21-division-dashboards-frontend.md` | División de los 6 dashboards «dios» del frontend | La verificación en el navegador con React DevTools Profiler (paso 12 de la hoja de ruta del `CHANGELOG`). El código está hecho y probado |

## Planes eliminados el 14-oct-2026 (registro)

Todos estaban cumplidos y verificados. La columna «Detalle» dice dónde leerlo hoy.

| Plan eliminado | Tema | Detalle |
|---|---|---|
| `2026-05-27-microservicios-independientes` | Satélites sin acceso directo a la base | Descartado a favor de «monolito con servicios satélite» (`docs/arquitectura/MICROSERVICIOS.md`); de ahí salió `internal_api` con JWT RS256 |
| `2026-06-01-produccion-flexible` | Transformación, mezcla de lotes y merma vendible | TEX-24, TEX-25 y TEX-29 en `EVIDENCIA_POR_SPRINT.md` |
| `2026-08-19-division-archivos-dios-backend` | División de los archivos dios (v1) | Supersedido por la v2 el 21-ago |
| `2026-08-21-division-archivos-dios-backend-v2` | División de los archivos dios | `CHANGELOG`, 21-ago-2026: los 4 son paquetes por dominio |
| `2026-09-01-hygiene-sweep-fase1-seguridad` | Higiene, fase 1: seguridad | `CHANGELOG`, 1-sep-2026 (7 commits) y los riesgos `RS-*` |
| `2026-09-02-hygiene-sweep-fase2-codigo-muerto` | Higiene, fase 2: código muerto | `CHANGELOG`, 2-sep-2026 |
| `2026-09-02-hygiene-sweep-fase3-4-comentarios-docs` | Higiene, fases 3 y 4 | `CHANGELOG`, 2-sep-2026 |
| `2026-09-02-hygiene-sweep-fase5-mejoras-arquitectonicas` | Higiene, fase 5: arquitectura | `CHANGELOG`, 2 y 3-sep-2026 (`Batch` eliminado en `481ce7f`) |
| `2026-09-02-hygiene-sweep-fase6-limpieza-tests` | Higiene, fase 6: limpieza de pruebas | `CHANGELOG`, 2-sep-2026 y `matriz_trazabilidad_pruebas.md` |
| `2026-09-03-internal-api-hardening` | Endurecer `internal_api` | `CHANGELOG`, 3-sep-2026; riesgos `RS-09` a `RS-12` |
| `2026-09-17-mes-motor-unificado` | Motor unificado MES, 6 fases | `CHANGELOG`, 17-sep-2026 y `spec` del mismo nombre |
| `2026-09-21-buscador-productos-bodeguero` | Buscador del selector de productos | `CHANGELOG`, 21-sep-2026 y su `spec` |
| `2026-09-21-sincronizacion-productos-quimicos` | Sincronización de productos y químicos | `CHANGELOG`, 21-sep-2026 y su `spec` |
| `2026-09-21-tipo-producto-colorante` | Tipo de producto colorante | `CHANGELOG`, 21-sep-2026 y su `spec` |
| `2026-09-22-portar-seguridad-y-deps-a-feature` | Portar seguridad y dependencias entre ramas | `CHANGELOG`, 22-sep-2026. El trabajo vive en `MES`; las ramas `refactorizacion` y `feature` se borraron el 14-oct-2026 |
| `2026-09-29-paginacion-lotes-y-ficha-lote` | Paginación de lotes y ficha del lote | `CHANGELOG`, 29-sep-2026 y la `spec` de paginación |
| `2026-09-30-correcciones-auditoria-tesis` | Hallazgos C-1, C-2 y M-4 de la auditoría | `AUDITORIA_BACKLOG_VS_CODIGO.md` (tabla de estado) y `CHANGELOG`, 30-sep-2026 |
| `2026-10-01-decisiones-fase-b-y-unificacion-migraciones` | Decisiones de la fase B y migraciones unificadas | `CHANGELOG`, 1-oct-2026 |
| `2026-10-01-fase-b-rutas-sin-consumidor` | Rutas de la API sin consumidor | `CHANGELOG`, 1-oct-2026; `scripts/auditar_rutas_frontend.py` devuelve 0 |
| `2026-10-05-migracion-ruff` | Migración a Ruff, 5 etapas | `CHANGELOG`, 5-oct (etapas 1-4) y 14-oct-2026 (etapa 5, el formateador); `ADR_008` |
| `2026-10-05-modernizacion-ci-cd` | Modernización del CI/CD, 7 fases | `CHANGELOG`, 5-oct, 13-oct y 14-oct-2026. Acciones en GitHub hechas el 26-oct-2026: rama por defecto `master`, rama `main` eliminada y `MES`, `staging` y `master` sincronizadas sin coautores de IA. El entorno y el runner siguen en GitLab |
| `2026-10-14-historial-mantenimiento-maquinas` | Historial de mantenimiento y paros de máquina | `CHANGELOG`, 14-oct-2026 (tarde) y `ADR_013` |

Las entradas antiguas del `CHANGELOG` siguen citando estas rutas: son referencias históricas a archivos
que ya no existen, y el `CHANGELOG` no se reescribe.

## Especificaciones conservadas

| Spec | Qué diseñó |
|---|---|
| `2026-05-27-microservicios-independientes-design.md` | La etapa de microservicios independientes (histórica) |
| `2026-06-01-produccion-flexible-design.md` | Transformación, mezcla y merma vendible |
| `2026-09-01-backend-hygiene-sweep-design.md` | Las 6 fases del barrido de higiene |
| `2026-09-17-mes-motor-unificado-design.md` | El motor unificado MES |
| `2026-09-21-buscador-productos-bodeguero-design.md` | El buscador del selector de productos |
| `2026-09-21-sincronizacion-productos-quimicos-design.md` | La sincronización de productos y químicos |
| `2026-09-21-tipo-producto-colorante-design.md` | El tipo de producto colorante |
| `2026-09-24-recetas-versionadas-tintoreria-design.md` | Las recetas versionadas (TEX-38, `VersionFormula`); se implementó sin plan propio |
| `2026-09-29-paginacion-lotes-y-cobertura-frontend-design.md` | La paginación de lotes y la cobertura del frontend |
