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
from ..schemas.printing import (
    BalanceMasasRequest, EtiquetaRequest, GuiaRemisionRequest,
    HistorialDespachosRequest, NotaVentaRequest, ReporteAvanceRequest,
)
from ..services.document_service import DocumentService
from ..services.label_service import LabelService
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


@router.post(
    "/etiqueta",
    summary="Genera etiqueta en PDF para impresoras genéricas (no Zebra)",
    description="F5: fallback universal — misma plantilla lógica que /zpl/etiqueta pero en PDF, "
                "para impresoras de etiquetas sin soporte ZPL nativo.",
)
async def generate_etiqueta_pdf(
    data: EtiquetaRequest,
    background_tasks: BackgroundTasks,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        contexto = LabelService.construir_contexto(data)
        result = strategy.render("etiqueta_label.html", contexto.model_dump(), data.lote_codigo)
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(
            document_type="PDF",
            template_used="etiqueta_label.html",
            success=success,
            pedido_id=None,
            guia_remision=None,
            lote_codigo=data.lote_codigo,
            error_detail=error_detail,
            usuario=data.usuario,
            motivo=data.motivo,
            tipo_evento=data.tipo_evento,
            version=data.version,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail)
    return result


@router.post(
    "/reporte-avance",
    summary="Genera PDF de reporte de avance de producción",
    description="Fase 2: recibe filas ya agregadas por Django (sin lógica de negocio "
                "aquí) y las renderiza en reporte_avance.html (A4 landscape).",
)
async def generate_reporte_avance_pdf(
    data: ReporteAvanceRequest,
    background_tasks: BackgroundTasks,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        result = strategy.render("reporte_avance.html", data.model_dump(), "reporte_avance")
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(
            document_type="PDF",
            template_used="reporte_avance.html",
            success=success,
            pedido_id=None,
            guia_remision=None,
            lote_codigo=None,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail)
    return result


@router.post(
    "/historial-despachos",
    summary="Genera PDF del historial de despachos (rol Despacho)",
    description="Recibe filas ya filtradas por fecha por Django y las renderiza "
                "en historial_despachos.html (A4 landscape).",
)
async def generate_historial_despachos_pdf(
    data: HistorialDespachosRequest,
    background_tasks: BackgroundTasks,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        result = strategy.render("historial_despachos.html", data.model_dump(), "historial_despachos")
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(
            document_type="PDF",
            template_used="historial_despachos.html",
            success=success,
            pedido_id=None,
            guia_remision=None,
            lote_codigo=None,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail)
    return result


@router.post(
    "/guia-remision",
    summary="Genera PDF de la Guía de Remisión (documento informativo)",
    description="Documento de acompañamiento de mercadería con los campos que exige "
                "el SRI — NO es un comprobante electrónico autorizado (sin clave de "
                "acceso ni firma digital); la facturación electrónica la maneja "
                "software externo.",
)
async def generate_guia_remision_pdf(
    data: GuiaRemisionRequest,
    background_tasks: BackgroundTasks,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        result = strategy.render("guia_remision.html", data.model_dump(), f"guia_remision_{data.numero}")
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(
            document_type="PDF",
            template_used="guia_remision.html",
            success=success,
            pedido_id=None,
            guia_remision=data.numero,
            lote_codigo=None,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail)
    return result


@router.post(
    "/reporte-balance",
    summary="Genera PDF de balance de masas mensual",
    description="Fase 2: recibe filas ya calculadas por Django (sin lógica de negocio "
                "aquí) y las renderiza en reporte_balance.html (A4 portrait).",
)
async def generate_balance_masas_pdf(
    data: BalanceMasasRequest,
    background_tasks: BackgroundTasks,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        result = strategy.render("reporte_balance.html", data.model_dump(), "balance_masas")
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(
            document_type="PDF",
            template_used="reporte_balance.html",
            success=success,
            pedido_id=None,
            guia_remision=None,
            lote_codigo=None,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail)
    return result
