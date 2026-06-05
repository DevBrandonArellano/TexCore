"""
Endpoint interno para validación de lotes por scanning_service.
SRP: solo expone información de lote+stock para despacho.
DIP: usa Django ORM (abstracción) en lugar de SQL directo.
ISO 27001 A.12.4: audit trail de cada consulta de lote.
"""
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import LoteProduccion
from internal_api.audit import AuditLogger
from internal_api.authentication import JWTServiceAuthentication
from internal_api.permissions import HasScope, IsInternalService
from inventory.models import StockBodega

logger = logging.getLogger(__name__)


class ValidateLoteView(APIView):
    """
    GET /api/internal/v1/lotes/{codigo_barras}/validate/

    Retorna información del lote y stock activo para el scanning_service.
    Scope requerido: lotes:read
    """

    authentication_classes = [JWTServiceAuthentication]
    permission_classes = [IsInternalService, HasScope("lotes:read")]

    def get(self, request, codigo_barras: str):
        AuditLogger.log(
            service=request.user.service_name,
            action="validate_lote",
            resource=codigo_barras[:64],  # Truncar por seguridad en logs
        )

        try:
            lote = LoteProduccion.objects.select_related(
                "orden_produccion__producto_salida"
            ).get(codigo_lote=codigo_barras)
        except LoteProduccion.DoesNotExist:
            return Response({"detail": "Lote no encontrado."}, status=404)

        op = lote.orden_produccion
        if not op or not op.producto_salida:
            return Response(
                {"detail": "Lote sin orden de producción o producto."},
                status=404,
            )

        # Solo retorna stock con cantidad > 0
        stock = (
            StockBodega.objects.select_related("bodega")
            .filter(lote=lote, cantidad__gt=0)
            .first()
        )

        return Response({
            "lote_id": lote.id,
            "codigo_lote": lote.codigo_lote,
            "producto": {
                "id": op.producto_salida.id,
                "descripcion": op.producto_salida.descripcion,
            },
            "estado": op.estado,
            "orden_produccion_id": op.id,
            "stock_id": stock.id if stock else None,
            "peso_kg": str(stock.cantidad) if stock else None,
            "bodega": {
                "id": stock.bodega.id,
                "nombre": stock.bodega.nombre,
            } if stock else None,
        })
