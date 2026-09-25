from rest_framework import serializers

from gestion.models import Producto, Proveedor

from ._common import ConservarOmitidosEnPutMixin


class ProveedorSerializer(ConservarOmitidosEnPutMixin, serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'


class ProductoSerializer(ConservarOmitidosEnPutMixin, serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'
