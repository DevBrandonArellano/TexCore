# TexCore Agent Guidelines (Gemini / Antigravity)

## 1. Graphify Knowledge Graph
This project has a knowledge graph at `graphify-out/` with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- Dirty `graphify-out/` files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context.
- **After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).**

---

## 2. Estándares de Testing y Verificación
- **Ejecución de Pruebas Backend (Django + DRF)**:
  - Comando principal: `pytest gestion/ inventory/ internal_api/`
  - Con settings de pruebas locales: `python manage.py test --settings=TexCore.settings_test`
  - Convención de nombres de prueba (ISTQB CTFL v4.0):  
    `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`
- **Ejecución de Pruebas de Microservicios (FastAPI / SQLAlchemy)**:
  - `pytest scanning_service/tests`
  - `pytest reporting_excel/tests`
  - `pytest printing_service/tests`
- **Verificación Frontend**:
  - `npx tsc --noEmit` (desde `frontend/`)
  - `npm test`

---

## 3. Normas de Arquitectura y Base de Datos (SQL Server 2022)
- **Django ORM**:
  - Prevenir N+1: Utilizar `select_related()` para relaciones ForeignKey y `prefetch_related()` para ManyToMany.
  - Usar `select_for_update()` en transacciones de stock e inventario.
  - La lógica de negocio vive en `Model.clean()`. El método `save()` invoca `self.full_clean()` antes de persistir.
- **Reglas Textiles y Precisión Decimal**:
  - Las equivalencias de empaquetado (ej. Hilos: $1 \text{ baño} = 15 \text{ fundas} = 225 \text{ conos}$; Telas: $1 \text{ baño} = 600 \text{ m}$) son **ejemplos configurables por sede**, no constantes globales rígidas. Cada sede puede definir sus propios estándares respetando la misma estructura matemática.
  - Telas utiliza `DECIMAL(12, 4)` en `cantidad_metros` para precisión métrica en mermas y costeo.
  - Respetar los CHECK Constraints nativos T-SQL (`database/V2__optimize_sqlserver2022_texcore.sql`).
- **Stored Procedures & Despliegue**:
  - Toda consulta reportable debe usar los 21 Stored Procedures optimizados de `database/V3__optimize_stored_procedures_texcore.sql` o endpoints de `internal_api`.
  - Respetar el nivel de aislamiento **Read Committed Snapshot Isolation (RCSI)**.
  - `seed_production_masters` inicializa la infraestructura global (grupos RBAC, permisos y superusuario `admin` sin sede). Las Sedes y Áreas reales son creadas dinámicamente por el **Administrador de Sistemas**.
