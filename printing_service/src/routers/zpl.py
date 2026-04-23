"""Router para generación de etiquetas ZPL."""
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader

from ..config import TEMPLATES_DIR
from ..schemas.printing import EtiquetaRequest
from ..services.output_strategy import ZplOutputStrategy

router = APIRouter(prefix="/zpl", tags=["ZPL"])


def get_zpl_strategy() -> ZplOutputStrategy:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    return ZplOutputStrategy(env)


@router.post("/etiqueta", summary="Genera etiqueta ZPL para impresora Zebra")
async def generate_zpl_label(
    data: EtiquetaRequest,
    strategy: ZplOutputStrategy = Depends(get_zpl_strategy),
):
    try:
        return strategy.render("etiqueta.zpl", data.model_dump(), data.lote_codigo)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
