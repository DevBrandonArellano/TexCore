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
- **Reporting, Queries & Master Seeding**:
  - Reporting queries are served via Django ORM and `internal_api` with native SQL Server indexes (V2, V4, V5); legacy stored procedures were eliminated as dead code.
  - Execute queries in Read Committed Snapshot Isolation (RCSI) mode.
  - `python manage.py seed_production_masters` creates RBAC groups, permissions and initial `admin` account without pre-creating fake Sedes or Areas. The **System Administrator** creates real Sedes and Areas upon initial system startup.

---

## 4. Development Standards (Estilo de desarrollo)
Mandatory for all new code and changes in this repo:
1. **Requirements first**: If a requirement is unclear, ask before implementing. Do not implement without understanding the full requirement.
2. **Design patterns**: Use the pattern that fits the context. If the codebase already uses one, keep it. Do not break established patterns.
3. **SOLID principles**: All new code must follow SOLID.
4. **Clean code**: Readable, maintainable, small focused functions and clear names.
5. **TDD + ISTQB**: Write tests before implementation. Apply test techniques such as EP (Equivalence Partitioning), BVA (Boundary Value Analysis) and STT (State Transition Testing). Every new code path needs test coverage.
6. **Atomic transactions**: Use `@transaction.atomic` in every operation that modifies critical data.
7. **Test data**: Use `factory_boy` factories. Do not create manual JSON fixtures.
8. **Secrets**: Never hardcode secrets or sensitive values. Use environment variables.

**Do NOT:**
- Implement without understanding the complete requirement.
- Break existing patterns in the code.
- Write code without test coverage.
- Use `any` in TypeScript.
- Create manual JSON fixtures (use factory_boy).
- Hardcode secrets or sensitive values.

---

## 5. Development Workflow (obligatorio)
Every development task follows these phases in order:

0. **Read context first (always)**: At the start of every session or task, read `CHANGELOG.md`, starting with the most recent entries, to see what has been worked on in previous days and where the work was left. Use that context before planning. If the changelog does not explain the current state, check `git log` on the current branch as well.
1. **Plan first**: Before writing or changing any code, present a development plan. The plan must list the requirements understood, the files to change, the tests to write (TDD), the design pattern to use, and the documentation to update.
2. **Wait for approval**: Do NOT start implementation until the user explicitly approves the plan. If the user asks for changes, update the plan and wait again.
3. **Implement after approval**: Follow the approved plan. Write the tests first (TDD), then the code. Run the tests from section 2 and make sure they pass.
4. **Document at the end (always)**:
   - Add an entry to `CHANGELOG.md` describing what was done.
   - Update the affected documentation (for example files in `docs/`) so it matches the new behavior.
   - Run `graphify update .` after modifying code (see section 1).
5. **Report**: Summarize what changed, which tests were run and their results, and which documentation was updated.
