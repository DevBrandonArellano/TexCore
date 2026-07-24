# TexCore Claude Code Guidelines

## 1. Graphify Knowledge Graph
This project has a knowledge graph at `graphify-out/` with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context.
- **After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).**

---

## 2. Testing & Verification Commands
- **Backend Django & DRF**:
  - `pytest gestion/ inventory/ internal_api/`
  - `python manage.py test --settings=TexCore.settings_test`
- **Microservices FastAPI**:
  - `pytest scanning_service/tests`
  - `pytest reporting_excel/tests`
  - `pytest printing_service/tests`
- **Frontend React/TypeScript**:
  - `cd frontend && npx tsc --noEmit`
  - `cd frontend && npm test`
- **Test Naming Convention (ISTQB CTFL v4.0)**:
  `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`

---

## 3. Architecture & Database Rules (SQL Server 2022)
- **Django ORM**:
  - Prevent N+1 issues: Always use `select_related()` for ForeignKeys and `prefetch_related()` for M2M relationships.
  - Stock updates must use `select_for_update()`.
  - Business validations belong in `Model.clean()`.
- **Textile Domain Constraints**:
  - Packaging equivalences (e.g. Yarns: 1 baño = 15 fundas = 225 conos; Fabrics: 1 baño = 600m) are **configurable reference examples per sede**, not system-wide hardcoded constants.
  - Fabrics use `DECIMAL(12, 4)` in `cantidad_metros`.
  - Native T-SQL CHECK constraints (`database/V2__optimize_sqlserver2022_texcore.sql`).
- **Stored Procedures & Master Seeding**:
  - Stored procedures are maintained in `database/V3__optimize_stored_procedures_texcore.sql`.
  - Execute queries in Read Committed Snapshot Isolation (RCSI) mode.
  - `python manage.py seed_production_masters` creates RBAC groups, permissions and initial `admin` account without pre-creating fake Sedes or Areas. The **System Administrator** creates real Sedes and Areas upon initial system startup.
