from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import io
import datetime

app = FastAPI(title="TexCore Printing Service", version="1.0.0")

# Setup Jinja2
templates = Environment(loader=FileSystemLoader("templates"))

# --- Models ---

class DetallePedido(BaseModel):
    producto_descripcion: str
    cantidad: float
    piezas: int
    peso: float
    precio_unitario: float

class NotaVentaRequest(BaseModel):
    id: int
    guia_remision: Optional[str] = None
    fecha_pedido: str
    cliente_nombre: Optional[str] = "Consumidor Final"
    cliente_ruc: Optional[str] = None
    cliente_direccion: Optional[str] = None
    vendedor_nombre: Optional[str] = None
    sede_nombre: Optional[str] = "Matriz"
    empresa_nombre: Optional[str] = "Empresa"
    esta_pagado: bool = False
    detalles: List[DetallePedido]
    
    @property
    def total(self):
        return sum(d.peso * d.precio_unitario for d in self.detalles)

class EtiquetaRequest(BaseModel):
    empresa: Optional[str] = "TexCore Industrial"
    producto_desc: str
    lote_codigo: str
    peso_neto: float
    unidad: Optional[str] = "kg"
    qr_data: str

# --- Endpoints ---

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/pdf/nota-venta")
async def generate_nota_venta_pdf(data: NotaVentaRequest):
    try:
        template = templates.get_template("nota_venta.html")
        
        # Format date for display
        try:
            dt = datetime.datetime.fromisoformat(data.fecha_pedido.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%d/%m/%Y %H:%M")
        except:
            formatted_date = data.fecha_pedido

        html_content = template.render(
            **data.dict(),
            total=data.total,
            fecha_pedido_formatted=formatted_date
        )
        
        pdf_file = HTML(string=html_content).write_pdf()
        
        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=nota_venta_{data.guia_remision or data.id}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/zpl/etiqueta")
async def generate_zpl_label(data: EtiquetaRequest):
    try:
        template = templates.get_template("etiqueta.zpl")
        zpl_content = template.render(**data.dict())
        return PlainTextResponse(zpl_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
