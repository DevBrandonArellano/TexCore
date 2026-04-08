"""
Factories para tests de TexCore — usa factory_boy.

Convención:
- Cada factory corresponde a un modelo Django
- Usar SubFactory para relaciones FK
- Usar LazyAttributeSequence / Sequence para unicidad
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import Group
from decimal import Decimal


class SedeFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Sede'

    nombre = factory.Sequence(lambda n: f'Sede Test {n}')
    location = factory.Sequence(lambda n: f'Ciudad {n}')
    status = 'activo'


class AreaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Area'

    nombre = factory.Sequence(lambda n: f'Área Test {n}')
    sede = factory.SubFactory(SedeFactory)


class BodegaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Bodega'

    nombre = factory.Sequence(lambda n: f'Bodega Test {n}')
    sede = factory.SubFactory(SedeFactory)


class ProductoFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Producto'

    codigo = factory.Sequence(lambda n: f'PROD-{n:04d}')
    descripcion = factory.Sequence(lambda n: f'Producto Test {n}')
    tipo = 'hilo'
    unidad_medida = 'kg'
    stock_minimo = Decimal('10.000')
    precio_base = Decimal('5.000')
    sede = factory.SubFactory(SedeFactory)


class CustomUserFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.CustomUser'

    username = factory.Sequence(lambda n: f'usuario{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@texcore.test')
    password = factory.PostGenerationMethodCall('set_password', 'TestPass123!')
    first_name = factory.Sequence(lambda n: f'Nombre{n}')
    last_name = factory.Sequence(lambda n: f'Apellido{n}')
    is_active = True
    sede = factory.SubFactory(SedeFactory)

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        for group_name in extracted:
            group, _ = Group.objects.get_or_create(name=group_name)
            self.groups.add(group)


class ClienteFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Cliente'

    nombre_razon_social = factory.Sequence(lambda n: f'Cliente Test {n}')
    ruc_cedula = factory.Sequence(lambda n: f'{1700000000 + n}')
    limite_credito = Decimal('1000.00')
    plazo_credito_dias = 30
    nivel_precio = 'normal'
    is_active = True
    sede = factory.SubFactory(SedeFactory)


class MaquinaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Maquina'

    nombre = factory.Sequence(lambda n: f'Maquina-{n:03d}')
    capacidad_maxima = Decimal('100.00')
    eficiencia_ideal = Decimal('0.90')
    estado = 'operativa'
    area = factory.SubFactory(AreaFactory)


class OrdenProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.OrdenProduccion'

    codigo = factory.Sequence(lambda n: f'OP-{n:05d}')
    producto = factory.SubFactory(ProductoFactory)
    estado = 'pendiente'
    sede = factory.SubFactory(SedeFactory)
    area = factory.SubFactory(AreaFactory)
