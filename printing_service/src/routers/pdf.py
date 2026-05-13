"""
Router para generación de PDFs.
Responsabilidad única: traducir HTTP → DocumentService → PdfOutputStrategy.
"""
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader

from ..config import TEMPLATES_DIR
from ..schemas.printing import NotaVentaRequest
from ..services.document_service import DocumentService
from ..services.output_strategy import PdfOutputStrategy

router = APIRouter(prefix="/pdf", tags=["PDF"])


def get_pdf_strategy() -> PdfOutputStrategy:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    return PdfOutputStrategy(env)


@router.post(
    "/nota-venta",
    summary="Genera PDF de nota de venta",
    description="Recibe los datos del pedido, calcula totales e IVA, y retorna el PDF generado.",
)
async def generate_nota_venta_pdf(
    data: NotaVentaRequest,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
):
    """
    Genera la nota de venta en PDF.
    - **data**: Datos completos del pedido incluyendo detalles con IVA.
    """
    try:
        contexto = DocumentService.construir_contexto(data)
        filename = f"nota_venta_{data.guia_remision or data.id}"
        return strategy.render("nota_venta.html", contexto.model_dump(), filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
