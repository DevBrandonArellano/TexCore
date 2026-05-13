"""
DocumentService: lógica de negocio del dominio de documentos comerciales.
Responsabilidades (SRP):
  - Calcular subtotal, IVA (15% Ecuador), total con retención.
  - Formatear fechas ISO a formato legible.
  - Construir el contexto de datos para el template.
No conoce HTTP, Jinja2 ni WeasyPrint.
"""
import datetime
import logging
from typing import List

from ..schemas.printing import DetallePedido, NotaVentaRequest, NotaVentaContexto

logger = logging.getLogger(__name__)

IVA_RATE = 0.15  # Tasa IVA Ecuador vigente


class DocumentService:
    """
    Servicio que encapsula la lógica de negocio para documentos comerciales.
    Métodos estáticos porque no requiere estado de instancia.
    """

    @staticmethod
    def calcular_subtotal(detalles: List[DetallePedido]) -> float:
        """Subtotal = suma de (peso * precio_unitario) para todos los detalles."""
        return sum(d.peso * d.precio_unitario for d in detalles)

    @staticmethod
    def calcular_iva(detalles: List[DetallePedido]) -> float:
        """IVA = 15% solo sobre los detalles con incluye_iva=True."""
        return sum(
            d.peso * d.precio_unitario * IVA_RATE
            for d in detalles
            if d.incluye_iva
        )

    @staticmethod
    def calcular_total(subtotal: float, iva: float, valor_retencion: float) -> float:
        """Total = subtotal + iva - retención."""
        return subtotal + iva - valor_retencion

    @staticmethod
    def formatear_fecha(fecha_iso: str) -> str:
        """
        Convierte fecha ISO 8601 a formato de display dd/mm/YYYY HH:MM.
        Si el parsing falla, retorna el string original para no romper el documento.
        """
        try:
            dt = datetime.datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y %H:%M")
        except (ValueError, AttributeError):
            logger.warning("No se pudo parsear fecha: %s", fecha_iso)
            return fecha_iso

    @classmethod
    def construir_contexto(cls, request: NotaVentaRequest) -> NotaVentaContexto:
        """
        Construye el contexto enriquecido para el template a partir del DTO de entrada.
        Orquesta todos los cálculos.
        """
        subtotal = cls.calcular_subtotal(request.detalles)
        iva = cls.calcular_iva(request.detalles)
        total = cls.calcular_total(subtotal, iva, request.valor_retencion)
        fecha_formatted = cls.formatear_fecha(request.fecha_pedido)

        return NotaVentaContexto(
            **request.model_dump(),
            fecha_pedido_formatted=fecha_formatted,
            subtotal=subtotal,
            iva=iva,
            total=total,
        )
