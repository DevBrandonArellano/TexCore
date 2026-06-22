"""
Router para generación de etiquetas ZPL.
DIP: get_zpl_strategy y get_audit_repo crean dependencias; el router no las construye.
ISO 27001 A.12.4: cada generación de etiqueta genera un registro de auditoría persistido en SQLite.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader

from ..config import TEMPLATES_DIR
from ..database.repository import AuditRepository, build_print_record, get_audit_repo
from ..schemas.printing import EtiquetaRequest
from ..services.output_strategy import ZplOutputStrategy

router = APIRouter(prefix="/zpl", tags=["ZPL"])


def get_zpl_strategy() -> ZplOutputStrategy:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))  # nosec B701 — ZPL no es HTML
    return ZplOutputStrategy(env)


@router.post("/etiqueta", summary="Genera etiqueta ZPL para impresora Zebra")
async def generate_zpl_label(
    data: EtiquetaRequest,
    background_tasks: BackgroundTasks,
    strategy: ZplOutputStrategy = Depends(get_zpl_strategy),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        result = strategy.render("etiqueta.zpl", data.model_dump(), data.lote_codigo)
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(
            document_type="ZPL",
            template_used="etiqueta.zpl",
            success=success,
            pedido_id=None,
            guia_remision=None,
            lote_codigo=data.lote_codigo,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail)
    return result
