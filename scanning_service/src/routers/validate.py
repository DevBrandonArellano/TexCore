"""
Router HTTP para validación de lotes.
DIP: get_validation_service crea LoteValidationService con DjangoApiClient de app.state.
La función se expone para que los tests puedan usar app.dependency_overrides.
"""
from fastapi import APIRouter, Depends, Request

from ..schemas.validate import ValidateRequest, ValidateResponse
from ..services.validation_service import LoteValidationService

router = APIRouter(tags=["Validación"])


def get_validation_service(req: Request) -> LoteValidationService:
    return LoteValidationService(req.app.state.django_client)


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
    svc: LoteValidationService = Depends(get_validation_service),
) -> ValidateResponse:
    """
    Valida un código de lote escaneado (QR o código de barras).

    - **code**: Código del lote tal como fue leído por el escáner. No puede estar vacío.
    """
    return svc.validate(request.code)
