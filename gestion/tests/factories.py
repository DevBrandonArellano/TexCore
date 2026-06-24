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
from datetime import datetime


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
    direccion_envio = factory.Sequence(lambda n: f'Calle Test {n}')
    limite_credito = Decimal('1000.00')
    plazo_credito_dias = 30
    nivel_precio = 'normal'
    is_active = True
    sede = factory.SubFactory(SedeFactory)


class MaquinaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Maquina'

    nombre = factory.Sequence(lambda n: f'Maquina-{n}')
    capacidad_maxima = Decimal('500.00')
    eficiencia_ideal = Decimal('0.85')
    estado = 'operativa'
    area = factory.SubFactory(AreaFactory)


class OrdenProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.OrdenProduccion'

    codigo = factory.Sequence(lambda n: f'OP-{n:04d}')
    producto_entrada = factory.SubFactory(ProductoFactory)
    producto_salida = factory.SubFactory(
        ProductoFactory,
        codigo=factory.Sequence(lambda n: f'OUT-{n:04d}')
    )
    bodega_entrada = factory.SubFactory(BodegaFactory)
    bodega_salida = factory.SubFactory(BodegaFactory)
    peso_neto_requerido = Decimal('100.00')
    estado = 'pendiente'
    prioridad = 'normal'
    sede = factory.SubFactory(SedeFactory)
    area = factory.SubFactory(AreaFactory)


class FormulaColorFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.FormulaColor'

    codigo = factory.Sequence(lambda n: f'FORM-{n:04d}')
    nombre_color = factory.Sequence(lambda n: f'Color Test {n}')
    description = factory.Sequence(lambda n: f'Descripción Fórmula {n}')
    tipo_sustrato = 'algodon'
    sede = factory.SubFactory(SedeFactory)
    estado = 'aprobada'


class FaseRecetaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.FaseReceta'

    formula = factory.SubFactory(FormulaColorFactory)
    nombre = 'tintura'
    orden = factory.Sequence(lambda n: n)


class DetalleFormulaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.DetalleFormula'

    fase = factory.SubFactory(FaseRecetaFactory)
    producto = factory.SubFactory(ProductoFactory)
    concentracion_gr_l = Decimal('10.00')
    tipo_calculo = 'gr_l'
    orden_adicion = 1


class MaquinaConMermaFactory(MaquinaFactory):
    producto_merma = factory.SubFactory(
        ProductoFactory,
        tipo='subproducto',
        codigo=factory.Sequence(lambda n: f'MERMA-{n:04d}')
    )
    bodega_merma = factory.SubFactory(BodegaFactory)


class ComponenteMezclaOPFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.ComponenteMezclaOP'

    orden = factory.SubFactory(OrdenProduccionFactory)
    producto = factory.SubFactory(ProductoFactory)
    bodega = factory.SubFactory(BodegaFactory)
    porcentaje = Decimal('50.00')
    cantidad_kg = Decimal('50.000')


class LoteProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.LoteProduccion'

    orden_produccion = factory.SubFactory(OrdenProduccionFactory)
    codigo_lote = factory.Sequence(lambda n: f'OP-TEST-L{n}')
    peso_neto_producido = Decimal('95.000')
    peso_merma = Decimal('5.000')
    tipo_merma = 'maquina'
    maquina = factory.SubFactory(MaquinaFactory)
    turno = 'Dia'
    hora_inicio = factory.LazyFunction(lambda: datetime(2026, 1, 1, 8, 0))
    hora_final = factory.LazyFunction(lambda: datetime(2026, 1, 1, 16, 0))
    unidades_empaque = 1
    presentacion = 'cono'


class ConsumoLoteDetalleFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.ConsumoLoteDetalle'

    lote_produccion = factory.SubFactory(LoteProduccionFactory)
    lote_origen = factory.SubFactory(LoteProduccionFactory)
    cantidad_consumida = Decimal('50.000')
    genera_nuevo_lote = True


class StockBodegaFactory(DjangoModelFactory):
    class Meta:
        model = 'inventory.StockBodega'

    bodega = factory.SubFactory(BodegaFactory)
    producto = factory.SubFactory(ProductoFactory)
    lote = None
    cantidad = Decimal('100.00')


class ProveedorFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.Proveedor'

    nombre = factory.Sequence(lambda n: f'Proveedor Test {n}')
    sede = factory.SubFactory(SedeFactory)


class TransformacionProductoFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.TransformacionProducto'

    orden_produccion = factory.SubFactory(OrdenProduccionFactory)
    numero_secuencia = factory.Sequence(lambda n: n + 1)
    producto_entrada = factory.SubFactory(ProductoFactory)
    producto_salida = factory.SubFactory(
        ProductoFactory, codigo=factory.Sequence(lambda n: f'TRANSF-OUT-{n:04d}')
    )
    maquina = factory.SubFactory(MaquinaFactory)
    peso_entrada = Decimal('100.000')
    peso_salida = Decimal('95.000')
    fecha_inicio = factory.LazyFunction(lambda: datetime(2026, 1, 1, 8, 0))
    fecha_fin = factory.LazyFunction(lambda: datetime(2026, 1, 1, 12, 0))
    estado = 'completada'
