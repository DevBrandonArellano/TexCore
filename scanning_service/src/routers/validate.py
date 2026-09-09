"""
Router HTTP para validación de lotes.
DIP: get_validation_service y get_audit_repo crean dependencias; el router no las construye.
La función se expone para que los tests puedan usar app.dependency_overrides.
ISO 27001 A.12.4: cada validación genera un registro de auditoría persistido en SQLite.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.concurrency import run_in_threadpool

from ..database.repository import AuditRepository, build_scan_record, get_audit_repo
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
async def validate_lote(
    request: ValidateRequest,
    background_tasks: BackgroundTasks,
    svc: LoteValidationService = Depends(get_validation_service),
    audit: AuditRepository = Depends(get_audit_repo),
) -> ValidateResponse:
    """
    Valida un código de lote escaneado (QR o código de barras).

    - **code**: Código del lote tal como fue leído por el escáner. No puede estar vacío.
    """
    # LoteValidationService.validate() hace I/O síncrono bloqueante (httpx.get
    # a Django Internal API). Llamarlo directo desde este handler async
    # bloquearía el event loop completo de Uvicorn, serializando escaneos
    # concurrentes en despacho. run_in_threadpool lo delega a un hilo worker.
    response = await run_in_threadpool(svc.validate, request.code)
    record = build_scan_record(request.code, response)
    background_tasks.add_task(audit.save, record)
    return response
