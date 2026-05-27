"""
Router HTTP para validación de lotes.
DIP: recibe LoteValidationService con DjangoApiClient inyectado desde main.
"""
from fastapi import APIRouter

from ..main import django_client
from ..schemas.validate import ValidateRequest, ValidateResponse
from ..services.validation_service import LoteValidationService

router = APIRouter(tags=["Validación"])


def get_validation_service() -> LoteValidationService:
    """Usa el DjangoApiClient singleton creado en main.py."""
    return LoteValidationService(django_client)


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validar código de lote escaneado",
    description=(
        "Verifica que el código exista, tenga orden de producción con producto, "
        "y que haya stock disponible (cantidad > 0) en alguna bodega."
    ),
)
def validate_lote(request: ValidateRequest) -> ValidateResponse:
    """
    Valida un código de lote escaneado (QR o código de barras).

    - **code**: Código del lote tal como fue leído por el escáner. No puede estar vacío.
    """
    return get_validation_service().validate(request.code)
