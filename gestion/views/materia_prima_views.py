"""
Artefacto RUP: Vistas REST
Casos de Uso: CU-TrazabilidadMateriaPrima (F0-001)
Roles: bodeguero (recepción), cualquier autenticado (consulta de trazabilidad)
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion.models import MateriaPrimaLote, LoteProduccion
from gestion.permissions import (
    IsBodegueroOrAdmin, IsTrazabilidadCostosRole, filtrar_lotes_por_sede, filtrar_por_sede,
)
from inventory.pagination import PaginacionAcotada
from inventory.permissions import bodegas_visibles, validar_bodega_operable
from gestion.serializers import (
    MateriaPrimaLoteSerializer, RegistrarMateriaPrimaSerializer,
)
from gestion.services.materia_prima_service import MateriaPrimaService, TraceabilityService

logger = logging.getLogger('gestion.views.materia_prima')


class MateriaPrimaLoteViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Lotes de materia prima: listado y recepción F0-001 (única vía de compra).
    Un lote no se crea, edita ni borra por la vía genérica: la recepción crea
    lote + stock + movimiento COMPRA, y la COMPRA enlazada sincroniza el lote."""
    serializer_class = MateriaPrimaLoteSerializer
    permission_classes = [IsAuthenticated, IsBodegueroOrAdmin]
    pagination_class = PaginacionAcotada  # la pantalla pide bloques de 4×30 (page_size=120)

    def get_queryset(self):
        user = self.request.user
        queryset = MateriaPrimaLote.objects.select_related(
            'producto', 'proveedor', 'bodega_recepcion', 'sede'
        ).order_by('-fecha_recepcion', '-id')

        # OWASP A01: lotes de su sede recibidos en bodegas que el usuario opera.
        queryset = filtrar_por_sede(queryset, user)
        visibles = bodegas_visibles(user)
        if visibles is not None:
            queryset = queryset.filter(bodega_recepcion__in=visibles)

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
        datos = serializer.validated_data

        # OWASP A01: bodega operable; producto y proveedor globales o de su sede.
        bodega = datos['bodega_recepcion']
        validar_bodega_operable(request.user, bodega, 'bodega_recepcion')
        for campo in ('producto', 'proveedor'):
            if datos[campo].sede_id not in (None, bodega.sede_id):
                raise ValidationError({campo: 'No encontrado.'})

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
            pais=datos.get('pais', ''),
            calidad=datos.get('calidad', ''),
        )

        return Response(
            MateriaPrimaLoteSerializer(mp_lote).data,
            status=status.HTTP_201_CREATED,
        )


class TraceabilityViewSet(viewsets.ViewSet):
    """Cadena de trazabilidad con proveedores y costos de compra: solo roles que
    ya gestionan costos de materia prima, y solo lotes de su sede."""
    permission_classes = [IsTrazabilidadCostosRole]

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

        lote = get_object_or_404(
            filtrar_lotes_por_sede(LoteProduccion.objects.all(), request.user),
            id=lote_id,
        )
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
