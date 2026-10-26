"""
Router HTTP para validación de lotes.
DIP: get_validation_service y get_audit_repo crean dependencias; el router no las construye.
La función se expone para que los tests puedan usar app.dependency_overrides.
ISO 27001 A.12.4: cada validación genera un registro de auditoría persistido en SQLite.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from ..database.repository import AuditRepository, build_scan_record, get_audit_repo
from ..domain.models import AlcanceSede
from ..schemas.validate import ValidateRequest, ValidateResponse
from ..services.validation_service import LoteValidationService

router = APIRouter(tags=["Validación"])


def get_validation_service(req: Request) -> LoteValidationService:
    return LoteValidationService(req.app.state.django_client)


def get_alcance_sede(
    x_texcore_ve_todas: Annotated[str | None, Header()] = None,
    x_texcore_sede_id: Annotated[str | None, Header()] = None,
) -> AlcanceSede:
    """
    Sede del usuario que escanea, tal como la deja nginx tras verificar la sesión con
    Django (`auth_request`, OWASP API2). nginx reemplaza estas cabeceras, así que el
    navegador no puede elegirlas. Si faltan, la petición no pasó por esa verificación:
    401 sin consultar nada.
    """
    if x_texcore_ve_todas not in ("0", "1"):
        raise HTTPException(status_code=401, detail="Sesión no verificada.")
    sede_id = int(x_texcore_sede_id) if (x_texcore_sede_id or "").isdigit() else None
    return AlcanceSede(sede_id=sede_id, ve_todas=x_texcore_ve_todas == "1")


@router.post(
    "/validate",
    summary="Validar código de lote escaneado",
    description=(
        "Verifica que el código exista, tenga orden de producción con producto, "
        "y que haya stock disponible (cantidad > 0) en alguna bodega."
    ),
)
async def validate_lote(
    request: ValidateRequest,
    background_tasks: BackgroundTasks,
    alcance: Annotated[AlcanceSede, Depends(get_alcance_sede)],
    svc: Annotated[LoteValidationService, Depends(get_validation_service)],
    audit: Annotated[AuditRepository, Depends(get_audit_repo)],
) -> ValidateResponse:
    """
    Valida un código de lote escaneado (QR o código de barras).

    - **code**: Código del lote tal como fue leído por el escáner. No puede estar vacío.
    """
    # LoteValidationService.validate() hace I/O síncrono bloqueante (httpx.get
    # a Django Internal API). Llamarlo directo desde este handler async
    # bloquearía el event loop completo de Uvicorn, serializando escaneos
    # concurrentes en despacho. run_in_threadpool lo delega a un hilo worker.
    response = await run_in_threadpool(svc.validate, request.code, alcance)
    record = build_scan_record(request.code, response)
    background_tasks.add_task(audit.save, record)
    return response
