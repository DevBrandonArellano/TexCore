"""
Router para generación de PDFs.
Responsabilidad única: traducir HTTP → DocumentService → PdfOutputStrategy.
DIP: get_pdf_strategy y get_audit_repo crean dependencias; el router no las construye.
ISO 27001 A.12.4: cada generación de PDF genera un registro de auditoría persistido en SQLite.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import TEMPLATES_DIR
from ..database.repository import AuditRepository, build_print_record, get_audit_repo
from ..schemas.printing import NotaVentaRequest
from ..services.document_service import DocumentService
from ..services.output_strategy import PdfOutputStrategy

router = APIRouter(prefix="/pdf", tags=["PDF"])


def get_pdf_strategy() -> PdfOutputStrategy:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    return PdfOutputStrategy(env)


@router.post(
    "/nota-venta",
    summary="Genera PDF de nota de venta",
    description="Recibe los datos del pedido, calcula totales e IVA, y retorna el PDF generado.",
)
async def generate_nota_venta_pdf(
    data: NotaVentaRequest,
    background_tasks: BackgroundTasks,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
    audit: AuditRepository = Depends(get_audit_repo),
):
    """
    Genera la nota de venta en PDF.
    - **data**: Datos completos del pedido incluyendo detalles con IVA.
    """
    success, error_detail, result = True, None, None
    try:
        contexto = DocumentService.construir_contexto(data)
        filename = f"nota_venta_{data.guia_remision or data.id}"
        result = strategy.render("nota_venta.html", contexto.model_dump(), filename)
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(
            document_type="PDF",
            template_used="nota_venta.html",
            success=success,
            pedido_id=data.id,
            guia_remision=data.guia_remision,
            lote_codigo=None,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail)
    return result
