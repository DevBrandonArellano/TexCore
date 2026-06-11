"""
Artefacto RUP: Vistas REST
Casos de Uso: CU-TrazabilidadMateriaPrima (F0-001)
Roles: bodeguero (recepción), cualquier autenticado (consulta de trazabilidad)
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion.models import MateriaPrimaLote, LoteProduccion
from gestion.permissions import IsBodegueroOrAdmin
from gestion.serializers import (
    MateriaPrimaLoteSerializer, RegistrarMateriaPrimaSerializer,
)
from gestion.services.materia_prima_service import MateriaPrimaService, TraceabilityService

logger = logging.getLogger('gestion.views.materia_prima')


class MateriaPrimaLoteViewSet(viewsets.ModelViewSet):
    """CRUD de lotes de materia prima + acción de recepción transaccional."""
    queryset = MateriaPrimaLote.objects.all()
    serializer_class = MateriaPrimaLoteSerializer
    permission_classes = [IsAuthenticated, IsBodegueroOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = MateriaPrimaLote.objects.select_related(
            'producto', 'proveedor', 'bodega_recepcion', 'sede'
        ).order_by('-fecha_recepcion', '-id')

        # Bodeguero ve solo lotes de sus bodegas asignadas
        if user.groups.filter(name='bodeguero').exists() and not user.is_superuser:
            queryset = queryset.filter(
                bodega_recepcion__in=user.bodegas_asignadas.all()
            )

        # Filtros opcionales para el dashboard
        proveedor_id = self.request.query_params.get('proveedor')
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        disponibles = self.request.query_params.get('disponibles')
        if disponibles in ('1', 'true'):
            queryset = queryset.filter(completamente_consumida=False)

        return queryset

    @action(detail=False, methods=['post'], url_path='registrar-entrada')
    def registrar_entrada(self, request):
        """POST /api/materia-prima/registrar-entrada/ — recepción de MP.

        Crea el lote de MP + stock + movimiento COMPRA en una transacción.
        Acepta multipart para adjuntar certificado_calidad.
        """
        serializer = RegistrarMateriaPrimaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mp_lote = MateriaPrimaService.registrar_entrada(
            proveedor=serializer.validated_data['proveedor'],
            producto=serializer.validated_data['producto'],
            lote_proveedor=serializer.validated_data['lote_proveedor'],
            cantidad_kg=serializer.validated_data['cantidad_kg'],
            costo_unitario=serializer.validated_data['costo_unitario'],
            bodega_recepcion=serializer.validated_data['bodega_recepcion'],
            fecha_recepcion=serializer.validated_data['fecha_recepcion'],
            usuario=request.user,
            certificado=request.FILES.get('certificado_calidad'),
            numero_documento=serializer.validated_data.get('numero_documento_entrada'),
        )

        return Response(
            MateriaPrimaLoteSerializer(mp_lote).data,
            status=status.HTTP_201_CREATED,
        )


class TraceabilityViewSet(viewsets.ViewSet):
    """Consulta de la cadena de trazabilidad (lectura para cualquier rol)."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='lote-produccion')
    def lote_produccion(self, request):
        """GET /api/trazabilidad/lote-produccion/?lote_id=X

        Responde la cadena completa: producto final ← lotes de MP ← proveedores
        con certificados y costos. Caso de uso: reclamo de cliente.
        """
        lote_id = request.query_params.get('lote_id')
        if not lote_id:
            return Response(
                {'error': 'Parámetro lote_id requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lote = get_object_or_404(LoteProduccion, id=lote_id)
        cadena = TraceabilityService.obtener_cadena_completa(lote)

        logger.info(
            'Cadena de trazabilidad consultada',
            extra={'sd': {
                'entity': 'LoteProduccion',
                'action': 'READ_TRACEABILITY',
                'lote': lote.codigo_lote,
                'user': request.user.username,
            }},
        )
        return Response(cadena)
