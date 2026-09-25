"""
Factories para tests de TexCore — usa factory_boy.

Convención:
- Cada factory corresponde a un modelo Django
- Usar SubFactory para relaciones FK
- Usar LazyAttributeSequence / Sequence para unicidad
"""
import factory
from factory.django import DjangoModelFactory
from django.apps import apps
from django.contrib.auth.models import Group
from django.utils import timezone
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


class ParoMaquinaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.ParoMaquina'

    maquina = factory.SubFactory(MaquinaFactory)
    inicio = factory.LazyFunction(lambda: datetime(2026, 1, 1, 8, 0))
    fin = factory.LazyFunction(lambda: datetime(2026, 1, 1, 8, 30))
    categoria = 'AVERIA'
    planificado = False
    turno = 'Dia'


class LineaProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.LineaProduccion'

    nombre = factory.Sequence(lambda n: f'Linea-{n}')
    estado = 'activa'
    area = factory.SubFactory(AreaFactory)

    @factory.post_generation
    def maquinas(self, create, extracted, **kwargs):
        if create and extracted:
            self.maquinas.set(extracted)


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


class ProcesoTintoreriaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.ProcesoTintoreria'

    codigo = factory.Sequence(lambda n: f'PROC-{n:04d}')
    nombre = factory.Sequence(lambda n: f'Proceso Test {n}')
    tipo = 'colorante'
    activo = True
    sede = factory.SubFactory(SedeFactory)


class FormulaColorFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.FormulaColor'

    codigo = factory.Sequence(lambda n: f'FORM-{n:04d}')
    nombre_color = factory.Sequence(lambda n: f'Color Test {n}')
    description = factory.Sequence(lambda n: f'Descripción Fórmula {n}')
    tipo_sustrato = 'algodon'
    sede = factory.SubFactory(SedeFactory)
    estado = 'aprobada'

    @factory.post_generation
    def version_oficial(self, create, extracted, **kwargs):
        # Una fórmula aprobada siempre tiene versión oficial (regla 2); sin ella sus OPs
        # no podrían lanzarse (regla 4).
        if create and self.estado == 'aprobada' and not self.versiones.exists():
            apps.get_model('gestion', 'VersionFormula').objects.create(
                formula=self, numero=1, snapshot={'formula': {}, 'fases': []},
                motivo='Versión inicial de la fábrica de pruebas', es_oficial=True)


class FaseRecetaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.FaseReceta'

    class Params:
        # Valor del antiguo enum de fases; se resuelve al ProcesoTintoreria legacy
        # de la sede de la fórmula (FASES_LEGACY).
        nombre = 'tintura'

    formula = factory.SubFactory(FormulaColorFactory)
    proceso = factory.LazyAttribute(
        lambda o: apps.get_model('gestion', 'ProcesoTintoreria').obtener_legacy(o.nombre, o.formula.sede))
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


class EventoEtiquetaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.EventoEtiqueta'

    lote = factory.SubFactory(LoteProduccionFactory)
    tipo_evento = 'ORIGINAL'
    secuencia = 1
    version = 1
    formato = 'ZPL'
    datos_snapshot = factory.LazyFunction(dict)


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


class CorridaProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.CorridaProduccion'

    codigo = factory.Sequence(lambda n: f'CORR-{n:04d}')
    sede = factory.SubFactory(SedeFactory)
    area = factory.SubFactory(AreaFactory, sede=factory.SelfAttribute('..sede'))
    linea = factory.SubFactory(LineaProduccionFactory, area=factory.SelfAttribute('..area'))
    maquina_principal = factory.SubFactory(MaquinaFactory, area=factory.SelfAttribute('..area'))
    modalidad = 'CONTINUA'
    turno = 'Mañana'
    fecha_jornada = factory.LazyFunction(lambda: datetime(2026, 1, 1).date())
    hora_inicio = factory.LazyFunction(timezone.now)
    estado = 'en_proceso'


class OperacionProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.OperacionProduccion'

    corrida = factory.SubFactory(CorridaProduccionFactory)
    numero_secuencia = factory.Sequence(lambda n: n + 1)
    maquina = factory.SubFactory(MaquinaFactory)
    operario = factory.SubFactory(CustomUserFactory)
    hora_inicio = factory.LazyFunction(timezone.now)
    estado = 'completada'


class PlanProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.PlanProduccion'

    codigo = factory.Sequence(lambda n: f'PLAN-TEST-{n:04d}')
    sede = factory.SubFactory(SedeFactory)
    fecha_inicio = factory.LazyFunction(lambda: datetime(2026, 1, 1).date())
    fecha_fin = factory.LazyFunction(lambda: datetime(2026, 1, 7).date())
    estado = 'borrador'
    supervisor = factory.SubFactory(CustomUserFactory)


class DetallePlanProduccionFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.DetallePlanProduccion'

    plan = factory.SubFactory(PlanProduccionFactory)
    producto_objetivo = factory.SubFactory(ProductoFactory, sede=factory.SelfAttribute('..plan.sede'))
    cantidad_planificada = Decimal('100.0000')
    cantidad_ejecutada = Decimal('0.0000')
    cantidad_aceptada = Decimal('0.0000')
    cantidad_segunda = Decimal('0.0000')
    estado = 'pendiente'


class PedidoVentaFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.PedidoVenta'

    cliente = factory.SubFactory(ClienteFactory)
    guia_remision = factory.Sequence(lambda n: f'GUIA-{n:05d}')
    estado = 'pendiente'
    esta_pagado = False
    sede = factory.SubFactory(SedeFactory)
    vendedor_asignado = factory.SubFactory(CustomUserFactory)


class DetallePedidoFactory(DjangoModelFactory):
    class Meta:
        model = 'gestion.DetallePedido'

    pedido_venta = factory.SubFactory(PedidoVentaFactory)
    producto = factory.SubFactory(ProductoFactory, sede=factory.SelfAttribute('..pedido_venta.sede'))
    cantidad = 10
    piezas = 10
    peso = Decimal('100.000')
    precio_unitario = Decimal('10.000')
    incluye_iva = True
    cantidad_fabricada = Decimal('0.000')
    estado_fabricacion = 'pendiente'


