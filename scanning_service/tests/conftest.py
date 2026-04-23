"""
conftest.py del scanning_service.

Con la arquitectura refactorizada (DI via Depends + ILoteRepository Protocol):
  - Los tests unitarios en tests/unit/ no importan main.py; inyectan mocks directo
    al constructor de LoteValidationService.
  - Los tests de integración en tests/integration/ usan app.dependency_overrides
    para sustituir get_validation_service o get_db.

Ya no se necesita parchear sys.modules. Este archivo queda vacío
(pytest lo sigue requiriendo para reconocer el paquete tests/).
"""
