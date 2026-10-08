import logging

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from gestion.models import Sede
from gestion.permissions import IsMRPRole, filtrar_por_sede, ve_todas_las_sedes
from inventory.models import OrdenCompraSugerida, RequerimientoMaterial
from inventory.serializers import OrdenCompraSugeridaSerializer, RequerimientoMaterialSerializer
from inventory.services.mrp_engine import MRPEngine

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

    @staticmethod
    def _sedes_sin_configuracion_empaque(user):
        """Sedes activas que el usuario ve y que aún no tienen equivalencias de empaque."""
        sedes = Sede.objects.filter(status='activo', configuracion_empaque__isnull=True)
        if not ve_todas_las_sedes(user):
            sedes = sedes.filter(pk=user.sede_id) if user.sede_id else sedes.none()
        return list(sedes.order_by('nombre').values_list('nombre', flat=True))

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
                logger.exception("Error en ejecución asíncrona de MRP", extra={'sd': {'error': str(e)}})

        try:
            # Lanzamos en un hilo separado para no bloquear la respuesta HTTP
            thread = threading.Thread(target=_run_mrp_async)
            thread.start()

            return Response({
                "status": "accepted",
                "message": "Cálculo MRP iniciado en segundo plano. Esto puede tomar unos minutos.",
                # TEX-43 CA-3: el motor corre en segundo plano; el aviso se da aquí.
                "sedes_sin_configuracion_empaque": self._sedes_sin_configuracion_empaque(request.user),
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.exception("Fallo al iniciar hilo de MRP", extra={'sd': {'error': str(e)}})
            return Response({"status": "error", "message": "No se pudo iniciar el proceso MRP"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
