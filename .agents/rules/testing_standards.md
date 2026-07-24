---
trigger: always_on
description: Standard testing commands, conventions and SQL Server 2022 verification rules for TexCore.
---

## TexCore Testing & Quality Standards

Rules:
- **Backend Django Tests**: Execute `pytest gestion/ inventory/ internal_api/` or `python manage.py test --settings=TexCore.settings_test`.
- **FastAPI Microservices**: Execute `pytest scanning_service/tests`, `pytest reporting_excel/tests`, and `pytest printing_service/tests`.
- **Frontend Verification**: Run `cd frontend && npx tsc --noEmit` and `npm test`.
- **Naming Convention (ISTQB CTFL v4.0)**: Use `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`.
- **Database & Domain Best Practices**:
  - Always prevent N+1 queries using `select_related()` and `prefetch_related()`.
  - Ensure stock mutations use `select_for_update()`.
  - Textile equivalences (e.g. Yarns: 1 baño = 15 fundas = 225 conos; Fabrics: 1 baño = 600m with `DECIMAL(12,4)`) are configurable per-sede reference examples.
  - `seed_production_masters` seeds RBAC roles/permissions and superuser `admin` without pre-creating fake Sedes or Areas (created dynamically by System Admin).
  - After modifying code files in this session, run `graphify update .` to keep the knowledge graph current.
