from rest_framework import serializers

from gestion.models import Bodega, CustomUser


class BodegaSerializer(serializers.ModelSerializer):
    usuarios_asignados = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CustomUser.objects.all(),
        required=False,
        allow_empty=True
    )
    _justificacion_auditoria = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Bodega
        fields = ['id', 'nombre', 'sede', 'usuarios_asignados', '_justificacion_auditoria']

    def create(self, validated_data):
        usuarios = validated_data.pop('usuarios_asignados', [])
        justificacion = validated_data.pop('_justificacion_auditoria', None)
        bodega = Bodega.objects.create(**validated_data)
        if justificacion:
            bodega._justificacion_auditoria = justificacion
            bodega.save()
        if usuarios:
            bodega.usuarios_asignados.set(usuarios)
        return bodega

    def update(self, instance, validated_data):
        usuarios = validated_data.pop('usuarios_asignados', None)
        justificacion = validated_data.pop('_justificacion_auditoria', None)
        if justificacion:
            instance._justificacion_auditoria = justificacion
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if usuarios is not None:
            instance.usuarios_asignados.set(usuarios)
        return instance
