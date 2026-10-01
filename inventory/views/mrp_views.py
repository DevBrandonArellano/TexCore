import logging

from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.serializers import RequerimientoMaterialSerializer, OrdenCompraSugeridaSerializer
from inventory.models import RequerimientoMaterial, OrdenCompraSugerida
from inventory.services.mrp_engine import MRPEngine
from gestion.permissions import IsMRPRole, filtrar_por_sede

logger = logging.getLogger('inventory.views')


class RequerimientoMaterialViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """MRP (Bodeguero y Ejecutivo): requerimientos de material de la sede."""
    serializer_class = RequerimientoMaterialSerializer
    permission_classes = [IsMRPRole]

    def get_queryset(self):
        queryset = RequerimientoMaterial.objects.select_related(
            'producto_requerido', 'sede').order_by('-fecha_calculo')
        return filtrar_por_sede(queryset, self.request.user)


class OrdenCompraSugeridaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """MRP: órdenes de compra sugeridas. Las genera el motor (`ejecutar-mrp`),
    no se editan a mano."""
    serializer_class = OrdenCompraSugeridaSerializer
    permission_classes = [IsMRPRole]

    def get_queryset(self):
        queryset = OrdenCompraSugerida.objects.select_related('producto', 'sede').order_by('-fecha_generacion')
        return filtrar_por_sede(queryset, self.request.user)

    @action(detail=False, methods=['post'], url_path='ejecutar-mrp')
    def ejecutar_mrp(self, request):
        """
        Ejecuta el motor MRP de forma asíncrona para evitar timeouts HTTP.
        """
        import threading

        def _run_mrp_async():
            try:
                engine = MRPEngine()
                engine.ejecutar_mrp()
            except Exception as e:
                logger.error("Error en ejecución asíncrona de MRP", extra={'sd': {'error': str(e)}}, exc_info=True)

        try:
            # Lanzamos en un hilo separado para no bloquear la respuesta HTTP
            thread = threading.Thread(target=_run_mrp_async)
            thread.start()

            return Response({
                "status": "accepted",
                "message": "Cálculo MRP iniciado en segundo plano. Esto puede tomar unos minutos."
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error("Fallo al iniciar hilo de MRP", extra={'sd': {'error': str(e)}})
            return Response({"status": "error", "message": "No se pudo iniciar el proceso MRP"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
