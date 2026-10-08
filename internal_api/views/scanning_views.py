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
from inventory.utils import principal_primero, stock_vendible_del_lote

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

        # Filas vendibles con stock (todas salvo la merma vendible), la del producto del
        # lote primero: tomar la primera fila por lote devolvía a veces la merma.
        filas = principal_primero(
            stock_vendible_del_lote(
                StockBodega.objects.select_related("bodega", "producto").filter(cantidad__gt=0), [lote]),
            lote,
        )
        stock = filas[0] if filas else None

        op = lote.orden_produccion
        # Producto informado: el de la fila principal; sin stock, el de la OP.
        producto = stock.producto if stock else (op.producto_salida if op else None)
        if producto is None:
            return Response(
                {"detail": "Lote sin orden de producción o producto."},
                status=404,
            )

        return Response({
            "lote_id": lote.id,
            "codigo_lote": lote.codigo_lote,
            "producto": {
                "id": producto.id,
                "descripcion": producto.descripcion,
            },
            "estado": op.estado if op else None,
            "orden_produccion_id": op.id if op else None,
            "stock_id": stock.id if stock else None,
            "peso_kg": str(stock.cantidad) if stock else None,
            "bodega": {
                "id": stock.bodega.id,
                "nombre": stock.bodega.nombre,
            } if stock else None,
            # Un lote puede traer productos agregados a mano además del de su OP; el
            # despacho los vende si los piden los pedidos.
            "peso_total_kg": str(sum(f.cantidad for f in filas)) if filas else None,
            "productos": [
                {
                    "producto_id": f.producto_id,
                    "descripcion": f.producto.descripcion,
                    "peso_kg": str(f.cantidad),
                    "bodega": {"id": f.bodega.id, "nombre": f.bodega.nombre},
                }
                for f in filas
            ],
        })
