"""
Equivalencias de empaque de una sede (TEX-43): GET y PUT /api/configuracion-empaque/.

El Administrador de Sede lee y configura la de su sede; el Administrador de Sistemas,
la de cualquier sede indicada con `sede_id`. Una sede ajena responde igual que una
inexistente (OWASP A01). Modificarla exige justificación (TEX-10) y queda en el
AuditLog con la sede del objeto.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import ConfiguracionEmpaqueSede, Sede
from gestion.permissions import IsAdminSistemasOrSede, ve_todas_las_sedes

from ._common import parse_int_param

MIN_JUSTIFICACION = 10


class ConfiguracionEmpaqueEntradaSerializer(serializers.Serializer):
    fundas_por_bano = serializers.IntegerField(min_value=1)
    conos_por_funda = serializers.IntegerField(min_value=1)
    justificacion = serializers.CharField(trim_whitespace=True)

    def validate_justificacion(self, valor):
        if len(valor) < MIN_JUSTIFICACION:
            raise serializers.ValidationError(
                f'La justificación debe tener al menos {MIN_JUSTIFICACION} caracteres.')
        return valor


def _respuesta(sede, config):
    return {
        'sede_id': sede.id,
        'sede_nombre': sede.nombre,
        'configurada': config is not None,
        'fundas_por_bano': config.fundas_por_bano if config else None,
        'conos_por_funda': config.conos_por_funda if config else None,
        'conos_por_bano': config.conos_por_bano if config else None,
    }


class ConfiguracionEmpaqueView(APIView):
    permission_classes = [IsAdminSistemasOrSede]

    def _sede(self, request):
        sede_id = parse_int_param(request.query_params.get('sede_id'), 'sede_id')
        if ve_todas_las_sedes(request.user):
            if sede_id is None:
                raise ValidationError({'sede_id': 'Indique la sede a configurar.'})
        else:
            propia = request.user.sede_id
            if propia is None or (sede_id is not None and sede_id != propia):
                raise NotFound('Sede no encontrada.')
            sede_id = propia
        return get_object_or_404(Sede, pk=sede_id)

    def get(self, request):
        sede = self._sede(request)
        return Response(_respuesta(sede, ConfiguracionEmpaqueSede.para_sede(sede)))

    def put(self, request):
        sede = self._sede(request)
        entrada = ConfiguracionEmpaqueEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        with transaction.atomic():
            config = ConfiguracionEmpaqueSede.objects.select_for_update().filter(sede=sede).first()
            creada = config is None
            if creada:
                config = ConfiguracionEmpaqueSede(sede=sede)
            config.fundas_por_bano = datos['fundas_por_bano']
            config.conos_por_funda = datos['conos_por_funda']
            config._justificacion_auditoria = datos['justificacion']
            config.save()

        return Response(_respuesta(sede, config),
                        status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK)
