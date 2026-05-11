"""
Router HTTP para validación de lotes.
SRP: única responsabilidad — traducir HTTP a llamadas de servicio y viceversa.
DIP: recibe LoteValidationService inyectado via Depends (no lo construye directamente).
La función get_validation_service puede ser sobreescrita en tests via
app.dependency_overrides, eliminando la necesidad de parchear sys.modules.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories.lote_repository import SqlLoteRepository
from ..services.validation_service import LoteValidationService
from ..schemas.validate import ValidateRequest, ValidateResponse

router = APIRouter(tags=["Validación"])


def get_validation_service(db: Session = Depends(get_db)) -> LoteValidationService:
    """
    Factory de dependencia: construye el grafo de objetos (Session → Repository → Service).
    Punto de inyección para tests: app.dependency_overrides[get_validation_service] = ...
    """
    return LoteValidationService(SqlLoteRepository(db))


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validar código de lote escaneado",
    description=(
        "Verifica que el código exista, tenga orden de producción con producto, "
        "y que haya stock disponible (cantidad > 0) en alguna bodega."
    ),
)
def validate_lote(
    request: ValidateRequest,
    service: LoteValidationService = Depends(get_validation_service),
) -> ValidateResponse:
    """
    Valida un código de lote escaneado (QR o código de barras).

    - **code**: Código del lote tal como fue leído por el escáner. No puede estar vacío.
    """
    return service.validate(request.code)
