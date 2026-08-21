import logging

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.serializers import RequerimientoMaterialSerializer, OrdenCompraSugeridaSerializer
from inventory.models import RequerimientoMaterial, OrdenCompraSugerida
from inventory.services.mrp_engine import MRPEngine

logger = logging.getLogger('inventory.views')


class RequerimientoMaterialViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RequerimientoMaterial.objects.select_related(
        'producto_requerido', 'sede').all().order_by('-fecha_calculo')
    serializer_class = RequerimientoMaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if not user.is_superuser and not user.groups.filter(name__in=['admin_sistemas']).exists():
            # Filtrar por sede si no es admin global
            queryset = queryset.filter(sede=user.sede)
        return queryset


class OrdenCompraSugeridaViewSet(viewsets.ModelViewSet):
    queryset = OrdenCompraSugerida.objects.select_related('producto', 'sede').all().order_by('-fecha_generacion')
    serializer_class = OrdenCompraSugeridaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if not user.is_superuser and not user.groups.filter(name__in=['admin_sistemas']).exists():
            queryset = queryset.filter(sede=user.sede)
        return queryset

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
