"""
Simulación de varios años de operación de varias empresas (sedes) con la capa de servicios real.

Pensada para probar el aplicativo con un volumen parecido al de producción: por defecto
4 empresas que producen 1000 t de hilo teñido al año cada una, durante 3 años.

Recorre el calendario día a día (lunes a sábado) y, por cada sede, hace lo que haría el
personal en el sistema, con los mismos servicios que usan las vistas:

  bodeguero    -> recepción semanal de hilo crudo (F0-001) y compra mensual de químicos
  bodeguero    -> abastece la línea de tintura (protocolo de 3 fases)
  jefe_planta  -> crea la OP de un baño de máquina y la lanza (fija la versión de la fórmula)
  tintorero    -> descarga los químicos del baño según la fórmula
  operario     -> registra el lote (consumo, merma vendible, entrada a PT y MES)
  operario     -> trazabilidad del lote con los lotes de MP del proveedor (FIFO)
  jefe_area    -> costeo del lote
  vendedor     -> pedidos sobre los lotes en stock de producto terminado
  despacho     -> despacho por escaneo (el endpoint real, ProcessDespachoAPIView)
  vendedor     -> cobranza según el plazo de crédito del cliente (con pagos atrasados)

Una OP es un baño de máquina (~550 kg) y produce un lote (la partida de tintura). Las
fechas de todo lo registrado (Kardex, auditoría, pedidos, pagos, MES) son las del día
simulado: el comando adelanta el reloj de Django mientras trabaja.

Uso:
  python manage.py simular_operacion                         # 4 sedes, 1000 t/año, 3 años
  python manage.py simular_operacion --dias 14 --sedes 1     # prueba corta
"""
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO
from random import Random
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from gestion import middleware
from gestion.models import (
    Area,
    Bodega,
    Cliente,
    CostoHoraMaquina,
    CustomUser,
    DetalleFormula,
    DetallePedido,
    FaseReceta,
    FormulaColor,
    Maquina,
    OrdenProduccion,
    PagoCliente,
    PedidoVenta,
    ProcesoTintoreria,
    Producto,
    Proveedor,
    Sede,
    TarifaOperario,
)
from gestion.services.costeo_service import CostoLoteService
from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.services.materia_prima_service import MateriaPrimaService
from gestion.services.registro_lote import RegistroLoteService
from gestion.services.versionado_formula import VersionadoFormulaService
from gestion.utils import PaymentReconciler
from inventory.models import MovimientoInventario, StockBodega
from inventory.services.transicion_bodega_service import TransicionBodegaService
from inventory.utils import safe_get_or_create_stock
from inventory.views.despacho_views import ProcessDespachoAPIView

logger = logging.getLogger(__name__)

PASSWORD = 'password123'
PREFIJO_SEDE = 'Empresa Textil'
DOS = Decimal('0.01')
TRES = Decimal('0.001')
RELACION_BANO = Decimal('8')          # litros de baño por kg de hilo
DIAS_COBERTURA_MP = 12                # la compra semanal cubre la semana y un colchón
DIAS_COBERTURA_QUIMICOS = 40
ZONA_PLANTA = ZoneInfo('America/Guayaquil')   # los turnos son en hora local de la planta

# (código, descripción, costo $/kg, participación en la producción)
CRUDOS = [
    ('HC-ALG-20', 'Hilo algodón crudo 20/1', '7.20', 35),
    ('HC-ALG-30', 'Hilo algodón crudo 30/1', '7.90', 25),
    ('HC-POL-150', 'Hilo poliéster crudo 150D', '5.10', 25),
    ('HC-MIX-24', 'Hilo mezcla 65/35 crudo 24/1', '6.30', 15),
]
# (sufijo, color, % de colorante sobre el peso, participación)
COLORES = [
    ('NEG', 'Negro', '6.0', 22),
    ('AZM', 'Azul marino', '4.5', 18),
    ('BLA', 'Blanco óptico', '0.4', 14),
    ('GRI', 'Gris', '1.2', 12),
    ('ROJ', 'Rojo', '3.0', 10),
    ('BEI', 'Beige', '0.8', 9),
    ('VIN', 'Vino', '4.0', 8),
    ('VER', 'Verde', '2.5', 7),
]
# (código, descripción, costo $/kg)
AUXILIARES = [
    ('QA-DET', 'Detergente industrial', '2.40'),
    ('QA-HUM', 'Humectante', '3.10'),
    ('QA-FIJ', 'Fijador de color', '4.80'),
    ('QA-SUA', 'Suavizante catiónico', '3.60'),
]
# fase legacy -> [(producto, tipo de cálculo, dosis)]; 'COLORANTE' se reemplaza por el del color
RECETA = [
    ('pre_tratamiento', 95, 30, [('QA-DET', 'gr_l', '1.0'), ('QA-HUM', 'gr_l', '0.5')]),
    ('tintura', 60, 90, [('COLORANTE', 'pct', None), ('QA-FIJ', 'pct', '1.5')]),
    ('lavado', 80, 30, [('QA-DET', 'gr_l', '0.8')]),
    ('suavizado', 40, 20, [('QA-SUA', 'pct', '1.0')]),
]
TURNOS = [('Matutino', 6), ('Vespertino', 14), ('Nocturno', 22)]
# Los 11 grupos RBAC: con LOADTEST_PREFIJO_USUARIOS=e1_ la prueba de carga entra como la empresa 1.
ROLES = ['admin_sistemas', 'admin_sede', 'ejecutivo', 'bodeguero', 'jefe_planta', 'jefe_area', 'tintorero',
         'vendedor', 'despacho', 'empaquetado']
NOMBRES_CLIENTES = [
    'Confecciones', 'Tejidos', 'Textiles', 'Moda', 'Hilados', 'Prendas', 'Calcetería', 'Uniformes',
]
CIUDADES = ['Quito', 'Guayaquil', 'Cuenca', 'Ambato', 'Atuntaqui', 'Riobamba', 'Ibarra', 'Loja']


def _dec(valor, paso=DOS) -> Decimal:
    return Decimal(str(valor)).quantize(paso, rounding=ROUND_HALF_UP)


class _Reloj:
    """Reloj de la simulación: reemplaza timezone.now() mientras el comando trabaja."""

    def __init__(self):
        self.ahora = timezone.now()

    def poner(self, dia: date, hora: int, minuto: int = 0):
        medianoche = datetime(dia.year, dia.month, dia.day, tzinfo=ZONA_PLANTA)
        self.ahora = medianoche + timedelta(hours=hora, minutes=minuto)
        return self.ahora


@dataclass
class _Planta:
    """Estado en memoria de una sede durante la simulación."""

    numero: int
    sede: Sede
    bodegas: dict
    maquinas: list
    usuarios: dict
    operarios: list
    proveedores: list
    crudos: dict                      # código -> Producto
    tenidos: dict                     # (crudo, color) -> Producto
    formulas: dict                    # sufijo de color -> FormulaColor
    quimicos: dict                    # código -> Producto
    clientes: list
    kg_diarios: Decimal
    secuencia_op: int = 0
    secuencia_pedido: int = 0
    secuencia_mp: int = 0
    mes_quimicos: tuple = ()
    por_vender: Decimal = Decimal('0')    # objetivo de venta acumulado (kg)
    mp_lotes: dict = field(default_factory=lambda: defaultdict(deque))   # crudo -> deque[[id, disponible]]
    lotes_en_stock: dict = field(default_factory=lambda: defaultdict(deque))  # producto_id -> deque[(código, kg)]
    despachos: list = field(default_factory=list)   # (fecha, pedido_id, [códigos])
    cobros: list = field(default_factory=list)      # (fecha, cliente, monto)


class Command(BaseCommand):
    help = 'Simula años de operación de varias sedes con los servicios reales (volumen de producción).'

    def add_arguments(self, parser):
        parser.add_argument('--sedes', type=int, default=4, help='Empresas (sedes) a simular (default: 4).')
        parser.add_argument('--anios', type=int, default=3, help='Años hacia atrás desde --hasta (default: 3).')
        parser.add_argument('--dias', type=int, default=0, help='Simular solo N días (prueba corta).')
        parser.add_argument('--toneladas-anuales', type=int, default=1000,
                            help='Producción anual por sede en toneladas (default: 1000).')
        parser.add_argument('--kg-por-bano', type=int, default=550,
                            help='Carga promedio de un baño de máquina en kg (default: 550).')
        parser.add_argument('--pct-venta', type=int, default=95,
                            help='Porcentaje de la producción que se vende (default: 95).')
        parser.add_argument('--hasta', type=date.fromisoformat, default=None,
                            help='Último día simulado, AAAA-MM-DD (default: ayer).')
        parser.add_argument('--semilla', type=int, default=2026, help='Semilla aleatoria (reproducible).')
        parser.add_argument('--sin-costeo', action='store_true', help='No calcular el costo de cada lote.')

    # ------------------------------------------------------------------ main
    def handle(self, *args, **opts):
        if Sede.objects.filter(nombre__startswith=PREFIJO_SEDE).exists():
            raise CommandError(
                f'Ya existen sedes "{PREFIJO_SEDE} …": la simulación ya se ejecutó en esta base. '
                'Rehaga la base para volver a simular.'
            )
        self.rng = Random(opts['semilla'])
        self.opts = opts
        self.reloj = _Reloj()
        hasta = opts['hasta'] or (timezone.localdate() - timedelta(days=1))
        dias = opts['dias'] or opts['anios'] * 365
        desde = hasta - timedelta(days=dias - 1)
        self.despachador = ProcessDespachoAPIView.as_view()
        self.fabrica = APIRequestFactory()

        call_command('setup_permissions', stdout=StringIO())
        # Carga masiva: cada evento de auditoría escribe una línea INFO; en 3 años son millones
        # de líneas que solo hacen lento el comando. Se silencia INFO mientras corre.
        logging.disable(logging.INFO)
        try:
            self._ejecutar(opts, desde, hasta)
        finally:
            logging.disable(logging.NOTSET)

    def _ejecutar(self, opts, desde, hasta):
        with mock.patch('django.utils.timezone.now', side_effect=lambda: self.reloj.ahora):
            self.reloj.poner(desde, 5)
            with transaction.atomic():
                plantas = [self._crear_planta(n, desde) for n in range(1, opts['sedes'] + 1)]
            self._simular(plantas, desde, hasta)
            with transaction.atomic():
                for planta in plantas:
                    self._dejar_ops_en_proceso(planta, hasta)
        middleware._local.__dict__.pop('user', None)
        self._resumen(plantas, desde, hasta)

    def _simular(self, plantas, desde, hasta):
        inicio = time.monotonic()
        total = (hasta - desde).days + 1
        dia = desde
        while dia <= hasta:
            with transaction.atomic():
                for planta in plantas:
                    self._trabajar_dia(planta, dia, primer_dia=dia == desde)
            hecho = (dia - desde).days + 1
            if dia.day == 1 or dia == hasta:
                transcurrido = time.monotonic() - inicio
                restante = transcurrido / hecho * (total - hecho)
                self.stdout.write(
                    f'  {dia:%Y-%m}  {hecho}/{total} días  {transcurrido / 60:5.1f} min  '
                    f'(faltan ~{restante / 60:.0f} min)'
                )
            dia += timedelta(days=1)

    def _trabajar_dia(self, planta, dia, primer_dia):
        if dia.weekday() == 6:      # domingo: solo cobranza
            self._cobrar(planta, dia)
            return
        if primer_dia or dia.weekday() == 0:
            self._comprar_materia_prima(planta, dia, semanas=2 if primer_dia else 1)
        if planta.mes_quimicos != (dia.year, dia.month):
            self._comprar_quimicos(planta, dia)
            planta.mes_quimicos = (dia.year, dia.month)
        # Ventas, despachos y cobros del día trabajan con los lotes de días anteriores:
        # así ninguna venta queda en el Kardex antes de la producción de su lote.
        self._vender(planta, dia)
        self._despachar(planta, dia)
        self._cobrar(planta, dia)
        banos = self._planificar_banos(planta)
        self._abastecer_linea(planta, dia, banos)
        for i, (crudo, color, kg) in enumerate(banos):
            self._producir_bano(planta, dia, i, len(banos), crudo, color, kg)

    # -------------------------------------------------------------- maestros
    def _actuar(self, usuario):
        middleware._local.user = usuario

    def _crear_planta(self, n, desde):
        sede = Sede.objects.create(nombre=f'{PREFIJO_SEDE} {n}', location=f'{CIUDADES[n - 1]}, Ecuador')
        areas = {nombre: Area.objects.create(nombre=nombre, sede=sede) for nombre in ('Tintura', 'Bodegas', 'Ventas')}
        bodegas = {
            clave: Bodega.objects.create(nombre=f'{nombre} E{n}', sede=sede)
            for clave, nombre in [('mp', 'Materia Prima'), ('linea', 'Línea Tintura'), ('transito', 'Tránsito'),
                                  ('quimicos', 'Químicos'), ('pt', 'Producto Terminado'), ('merma', 'Merma')]
        }
        usuarios = {rol: self._usuario(f'e{n}_{rol}', rol, sede, areas, bodegas) for rol in ROLES}
        operarios = [self._usuario(f'e{n}_operario' if i == 1 else f'e{n}_operario{i}', 'operario', sede, areas,
                                   bodegas) for i in range(1, 7)]
        self._actuar(usuarios['jefe_planta'])
        crudos, tenidos, quimicos = self._crear_productos(n, sede)
        maquinas = self._crear_maquinas(n, areas['Tintura'], bodegas, quimicos['MERMA'], operarios, desde)
        formulas = self._crear_formulas(n, sede, quimicos, usuarios['tintorero'])
        proveedores = [Proveedor.objects.create(nombre=f'{nombre} (E{n})', sede=sede) for nombre in (
            'Hilanderías del Pacífico S.A.', 'Fibras Andinas Cía. Ltda.', 'Importadora de Hilados del Sur')]
        self._actuar(usuarios['vendedor'])
        clientes = self._crear_clientes(n, sede, usuarios['vendedor'])
        kg_diarios = _dec(Decimal(self.opts['toneladas_anuales']) * 1000 / 313)   # 313 días laborables
        self.stdout.write(f'  Sede {sede.nombre}: {len(clientes)} clientes, {len(maquinas)} máquinas, '
                          f'{kg_diarios} kg/día')
        return _Planta(n, sede, bodegas, maquinas, usuarios, operarios, proveedores, crudos, tenidos,
                       formulas, quimicos, clientes, kg_diarios)

    def _usuario(self, username, rol, sede, areas, bodegas):
        area = areas['Tintura'] if rol in ('operario', 'tintorero', 'jefe_area') else (
            areas['Ventas'] if rol in ('vendedor', 'despacho') else areas['Bodegas'])
        usuario = CustomUser.objects.create_user(
            username=username, password=PASSWORD, email=f'{username}@simulacion.local',
            first_name=rol.replace('_', ' ').title(), last_name=f'E{sede.nombre[-1]}', sede=sede, area=area,
        )
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        usuario.bodegas_asignadas.set(bodegas.values())
        return usuario

    def _crear_productos(self, n, sede):
        crudos = {
            codigo: Producto.objects.create(
                codigo=codigo, sede=sede, descripcion=desc, tipo='materia_prima', unidad_medida='kg',
                stock_minimo=Decimal('2000'), precio_base=Decimal(costo), pais_origen='Ecuador')
            for codigo, desc, costo, _ in CRUDOS
        }
        tenidos = {}
        for codigo, desc, costo, _ in CRUDOS:
            for sufijo, color, _pct, _ in COLORES:
                tenidos[(codigo, sufijo)] = Producto.objects.create(
                    codigo=f'{codigo.replace("HC-", "HT-")}-{sufijo}', sede=sede, tipo='hilo', unidad_medida='kg',
                    descripcion=f'{desc.replace(" crudo", "")} {color}', stock_minimo=Decimal('500'),
                    precio_base=_dec(Decimal(costo) * Decimal('1.85')))
        quimicos = {
            codigo: Producto.objects.create(codigo=codigo, sede=sede, descripcion=desc, tipo='quimico',
                                            unidad_medida='kg', stock_minimo=Decimal('100'),
                                            precio_base=Decimal(costo))
            for codigo, desc, costo in AUXILIARES
        }
        for sufijo, color, _pct, _ in COLORES:
            quimicos[f'QC-{sufijo}'] = Producto.objects.create(
                codigo=f'QC-{sufijo}', sede=sede, descripcion=f'Colorante {color}', tipo='quimico',
                unidad_medida='kg', stock_minimo=Decimal('50'), precio_base=Decimal('18.50'))
        quimicos['MERMA'] = Producto.objects.create(
            codigo='SUB-MERMA', sede=sede, descripcion='Merma de hilo (segunda)', tipo='subproducto',
            unidad_medida='kg', stock_minimo=Decimal('0'), precio_base=Decimal('1.80'))
        return crudos, tenidos, quimicos

    def _crear_maquinas(self, n, area, bodegas, merma, operarios, desde):
        maquinas = []
        for i in range(1, 5):
            maquina = Maquina.objects.create(
                nombre=f'Autoclave E{n}-{i}', area=area, capacidad_maxima=Decimal('600'),
                volumen_bano_litros=Decimal('6000'), eficiencia_ideal=Decimal('0.88'), estado='operativa',
                bodega_entrada=bodegas['linea'], bodega_salida=bodegas['pt'],
                producto_merma=merma, bodega_merma=bodegas['merma'])
            maquina.operarios.set(operarios)
            CostoHoraMaquina.objects.create(maquina=maquina, vigente_desde=desde, costo_hora=Decimal('9.50'))
            maquinas.append(maquina)
        for operario in operarios:
            TarifaOperario.objects.create(operario=operario, vigente_desde=desde, sede=area.sede,
                                          tipo_contrato='tiempo', tarifa_hora=Decimal('3.10'))
        return maquinas

    def _crear_formulas(self, n, sede, quimicos, tintorero):
        self._actuar(tintorero)
        formulas = {}
        for sufijo, color, pct, _ in COLORES:
            formula = FormulaColor.objects.create(
                codigo=f'F-E{n}-{sufijo}', sede=sede, nombre_color=color, tipo_sustrato='mixto',
                estado='en_pruebas', creado_por=tintorero, observaciones='Receta de producción (simulación).')
            for orden, (fase_legacy, temperatura, minutos, insumos) in enumerate(RECETA, start=1):
                fase = FaseReceta.objects.create(
                    formula=formula, orden=orden, temperatura=temperatura, tiempo=minutos,
                    proceso=ProcesoTintoreria.obtener_legacy(fase_legacy, sede))
                for orden_adicion, (codigo, tipo, dosis) in enumerate(insumos, start=1):
                    producto = quimicos[f'QC-{sufijo}' if codigo == 'COLORANTE' else codigo]
                    valor = Decimal(pct if codigo == 'COLORANTE' else dosis)
                    DetalleFormula.objects.create(
                        fase=fase, producto=producto, tipo_calculo=tipo, orden_adicion=orden_adicion,
                        concentracion_gr_l=valor if tipo == 'gr_l' else None,
                        porcentaje=valor if tipo == 'pct' else None)
            VersionadoFormulaService.asegurar_version_oficial(
                formula, 'Aprobación de la receta de producción.', tintorero)
            formulas[sufijo] = formula
        return formulas

    def _crear_clientes(self, n, sede, vendedor):
        clientes = []
        for i in range(1, 41):
            mayorista = i % 3 == 0
            clientes.append(Cliente.objects.create(
                ruc_cedula=f'17{n}{i:07d}001', sede=sede, vendedor_asignado=vendedor, is_active=True,
                nombre_razon_social=f'{self.rng.choice(NOMBRES_CLIENTES)} {CIUDADES[i % 8]} {n}-{i:02d} S.A.',
                direccion_envio=f'{CIUDADES[i % 8]}, Ecuador', nivel_precio='mayorista' if mayorista else 'normal',
                limite_credito=Decimal(self.rng.choice([20000, 50000, 120000, 250000])),
                plazo_credito_dias=self.rng.choice([0, 15, 30, 30, 45, 60])))
        return clientes

    # -------------------------------------------------------------- compras
    def _proporcion(self, tabla):
        total = sum(fila[-1] for fila in tabla)
        return {fila[0]: Decimal(fila[-1]) / total for fila in tabla}

    def _comprar_materia_prima(self, planta, dia, semanas):
        self.reloj.poner(dia, 5)
        self._actuar(planta.usuarios['bodeguero'])
        dias = DIAS_COBERTURA_MP * semanas
        for codigo, share in self._proporcion(CRUDOS).items():
            producto = planta.crudos[codigo]
            stock = StockBodega.objects.filter(bodega__in=[planta.bodegas['mp'], planta.bodegas['linea']],
                                               producto=producto, lote__isnull=True)
            existente = sum((s.cantidad for s in stock), Decimal('0'))
            faltante = planta.kg_diarios * share * dias * Decimal('1.04') - existente
            if faltante > 0:
                self._recibir_materia_prima(planta, dia, codigo, int(faltante / 1000) + 1)

    def _recibir_materia_prima(self, planta, dia, codigo, toneladas):
        """Recepción F0-001 en pallets de 1 t, repartidos en uno a tres lotes de proveedor."""
        producto = planta.crudos[codigo]
        for parte in self._partir(toneladas):
            planta.secuencia_mp += 1
            mp = MateriaPrimaService.registrar_entrada(
                proveedor=self.rng.choice(planta.proveedores), producto=producto,
                lote_proveedor=f'LP-E{planta.numero}-{planta.secuencia_mp:06d}',
                cantidad_kg=Decimal(parte * 1000), costo_unitario=_dec(producto.precio_base * Decimal(
                    self.rng.uniform(0.95, 1.06)), TRES), bodega_recepcion=planta.bodegas['mp'],
                fecha_recepcion=dia, usuario=planta.usuarios['bodeguero'],
                numero_documento=f'FAC-{planta.numero}{planta.secuencia_mp:07d}', pais='Ecuador',
                calidad=self.rng.choice(['A', 'A', 'B']))
            planta.mp_lotes[codigo].append([mp.id, Decimal(parte * 1000)])

    def _partir(self, toneladas):
        if toneladas <= 0:
            return []
        partes = min(toneladas, self.rng.randint(1, 3))
        base, resto = divmod(toneladas, partes)
        return [base + (1 if i < resto else 0) for i in range(partes)]

    def _comprar_quimicos(self, planta, dia):
        """Repone cada químico hasta cubrir DIAS_COBERTURA_QUIMICOS de consumo esperado."""
        self.reloj.poner(dia, 5, 10)
        self._actuar(planta.usuarios['bodeguero'])
        for codigo in planta.quimicos:
            if codigo != 'MERMA':
                self._reponer_quimico(planta, dia, codigo, f'OC-QUIM-E{planta.numero}-{dia:%Y%m}')

    def _reponer_quimico(self, planta, dia, codigo, documento, minimo=Decimal('0')):
        """Compra el químico hasta cubrir DIAS_COBERTURA_QUIMICOS de consumo (y al menos `minimo`)."""
        objetivo = max(self._consumo_diario_quimico(codigo, planta.kg_diarios) * DIAS_COBERTURA_QUIMICOS, minimo)
        stock, _ = safe_get_or_create_stock(StockBodega, bodega=planta.bodegas['quimicos'],
                                            producto=planta.quimicos[codigo], lote=None)
        faltante = _dec(objetivo - stock.cantidad, TRES)
        if faltante <= 0:
            return
        compra = _dec(faltante + 25 - faltante % 25, TRES)   # sacos de 25 kg
        stock.cantidad += compra
        stock._justificacion_auditoria = f'Compra de químicos {dia:%Y-%m-%d}'
        stock.save()
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=planta.quimicos[codigo], bodega_destino=planta.bodegas['quimicos'],
            cantidad=compra, usuario=planta.usuarios['bodeguero'], proveedor=planta.proveedores[0],
            documento_ref=documento, saldo_resultante=stock.cantidad)

    def _asegurar_quimicos_del_bano(self, planta, dia, color, kg):
        """Compra urgente si algún químico del baño no alcanza para dos baños como este."""
        pct_colorante = next(Decimal(c[2]) for c in COLORES if c[0] == color)
        necesidad = defaultdict(Decimal, {f'QC-{color}': kg * pct_colorante / 100})
        for _fase, _t, _m, insumos in RECETA:
            for insumo, tipo, dosis in insumos:
                if insumo != 'COLORANTE':
                    por_litro = kg * RELACION_BANO * Decimal(dosis) / 1000
                    necesidad[insumo] += por_litro if tipo == 'gr_l' else kg * Decimal(dosis) / 100
        for codigo, kg_quimico in necesidad.items():
            stock = StockBodega.objects.filter(bodega=planta.bodegas['quimicos'], producto=planta.quimicos[codigo],
                                               lote__isnull=True).first()
            if stock is None or stock.cantidad < kg_quimico * 2:
                self._actuar(planta.usuarios['bodeguero'])
                self._reponer_quimico(planta, dia, codigo, f'OC-QUIM-URG-E{planta.numero}-{dia:%Y%m%d}',
                                      minimo=kg_quimico * 10)

    def _consumo_diario_quimico(self, codigo, kg_diarios):
        """kg del químico por día: g/L × litros del baño, o % sobre el peso del hilo."""
        litros = kg_diarios * RELACION_BANO
        total = Decimal('0')
        participacion = self._proporcion(COLORES)
        for _fase, _t, _m, insumos in RECETA:
            for insumo, tipo, dosis in insumos:
                if insumo == 'COLORANTE':
                    sufijo = codigo.removeprefix('QC-')
                    pct = next((Decimal(c[2]) for c in COLORES if c[0] == sufijo), None)
                    if pct is not None and codigo.startswith('QC-'):
                        total += kg_diarios * participacion[sufijo] * pct / 100
                elif insumo == codigo:
                    total += litros * Decimal(dosis) / 1000 if tipo == 'gr_l' else kg_diarios * Decimal(dosis) / 100
        return total

    # -------------------------------------------------------------- producción
    def _planificar_banos(self, planta):
        """Baños del día: la producción diaria repartida por hilo y color, en cargas de ~550 kg."""
        objetivo = planta.kg_diarios * Decimal(str(self.rng.uniform(0.85, 1.15)))
        banos, acumulado = [], Decimal('0')
        crudos, pesos_crudo = zip(*[(c[0], c[3]) for c in CRUDOS], strict=True)
        colores, pesos_color = zip(*[(c[0], c[3]) for c in COLORES], strict=True)
        while acumulado < objetivo:
            kg = _dec(self.opts['kg_por_bano'] * self.rng.uniform(0.82, 1.08))
            banos.append((self.rng.choices(crudos, pesos_crudo)[0], self.rng.choices(colores, pesos_color)[0], kg))
            acumulado += kg
        return banos

    def _abastecer_linea(self, planta, dia, banos):
        """El bodeguero lleva a la línea el hilo crudo que necesitan los baños del día."""
        self.reloj.poner(dia, 5, 30)
        bodeguero = planta.usuarios['bodeguero']
        self._actuar(bodeguero)
        necesidad = defaultdict(Decimal)
        for crudo, _color, kg in banos:
            necesidad[crudo] += kg * Decimal('1.04')       # carga + merma
        for crudo, kg in necesidad.items():
            producto = planta.crudos[crudo]
            en_linea = StockBodega.objects.filter(bodega=planta.bodegas['linea'], producto=producto,
                                                  lote__isnull=True).first()
            falta = _dec(kg - (en_linea.cantidad if en_linea else 0), TRES)
            if falta <= 0:
                continue
            en_mp = StockBodega.objects.filter(bodega=planta.bodegas['mp'], producto=producto,
                                               lote__isnull=True).first()
            disponible = en_mp.cantidad if en_mp else Decimal('0')
            if disponible < falta:      # compra urgente: la semana consumió más de este hilo
                self._recibir_materia_prima(planta, dia, crudo, int((falta - disponible) / 1000) + 2)
            mov = TransicionBodegaService.iniciar_transicion(
                producto=producto, bodega_origen=planta.bodegas['mp'], bodega_destino=planta.bodegas['linea'],
                bodega_transicion=planta.bodegas['transito'], cantidad=falta, usuario=bodeguero,
                documento_ref=f'ABAST-E{planta.numero}-{dia:%Y%m%d}')
            TransicionBodegaService.completar_transicion(mov, bodeguero)

    def _producir_bano(self, planta, dia, indice, total, crudo, color, kg):
        planta.secuencia_op += 1
        turno, hora_turno = TURNOS[min(indice * len(TURNOS) // total, len(TURNOS) - 1)]
        minuto_inicio = (indice * 1440 // total) % 480
        inicio = self.reloj.poner(dia, hora_turno, minuto_inicio)
        maquina = planta.maquinas[planta.secuencia_op % len(planta.maquinas)]
        operario = planta.operarios[(planta.secuencia_op + indice) % len(planta.operarios)]
        producto = planta.tenidos[(crudo, color)]

        self._actuar(planta.usuarios['jefe_planta'])
        orden = OrdenProduccion.objects.create(
            codigo=f'E{planta.numero}-{planta.secuencia_op:06d}', sede=planta.sede, area=maquina.area,
            producto_entrada=planta.crudos[crudo], producto_salida=producto, formula_color=planta.formulas[color],
            bodega_entrada=planta.bodegas['linea'], bodega_salida=planta.bodegas['pt'],
            bodega_quimicos=planta.bodegas['quimicos'], peso_neto_requerido=kg, litros_bano=kg * RELACION_BANO,
            maquina_asignada=maquina, operario_asignado=operario, prioridad='normal', estado='pendiente',
            fecha_inicio_planificada=dia, fecha_fin_planificada=dia)
        orden.estado = 'en_proceso'              # lanzar: fija la versión oficial de la fórmula
        orden._justificacion_auditoria = 'Lanzamiento de la OP a producción.'
        orden.save()

        self._asegurar_quimicos_del_bano(planta, dia, color, kg)
        self._actuar(planta.usuarios['tintorero'])
        DescargaQuimicosService.descargar_para_op(orden, planta.usuarios['tintorero'])

        merma = _dec(kg * Decimal(str(self.rng.uniform(0.015, 0.035))))
        final = self.reloj.poner(dia, hora_turno, minuto_inicio + self.rng.randint(240, 330))
        self._actuar(operario)
        lote = RegistroLoteService.registrar_lote(orden, {
            'peso_neto_producido': kg - merma, 'peso_merma': merma, 'tipo_merma': 'maquina',
            'clasificacion_calidad': self.rng.choices(['primera', 'segunda'], [96, 4])[0],
            'maquina': maquina, 'operario': operario.id, 'turno': turno, 'hora_inicio': inicio, 'hora_final': final,
            'presentacion': 'cono', 'unidades_empaque': 1, 'tara': Decimal('12.5'),
            'peso_bruto': kg - merma + Decimal('12.5'),
        }, operario, completar_orden=True)
        self._trazar_materia_prima(planta, crudo, lote, kg, operario)
        if not self.opts['sin_costeo']:
            self._actuar(planta.usuarios['jefe_area'])
            CostoLoteService.calcular_costo(lote, planta.usuarios['jefe_area'])
        planta.lotes_en_stock[producto.id].append((lote.codigo_lote, kg - merma))

    def _trazar_materia_prima(self, planta, crudo, lote, kg, usuario):
        """Vincula el lote con los lotes de MP del proveedor, en orden de llegada (FIFO)."""
        consumos, pendiente = [], kg
        cola = planta.mp_lotes[crudo]
        while pendiente > 0 and cola:
            mp_id, disponible = cola[0]
            usado = min(disponible, pendiente)
            consumos.append({'materia_prima_lote_id': mp_id, 'cantidad_kg': usado})
            pendiente -= usado
            cola[0][1] -= usado
            if cola[0][1] <= 0:
                cola.popleft()
        if consumos:
            MateriaPrimaService.consumir_materia_prima(lote, consumos, usuario)

    def _dejar_ops_en_proceso(self, planta, dia):
        """Al cierre queda una OP de producción continua por máquina, con hilo en la línea:
        así el operario (y la prueba de carga) tiene órdenes en las que registrar lotes."""
        self.reloj.poner(dia, 21)
        bodeguero = planta.usuarios['bodeguero']
        self._actuar(bodeguero)
        crudos = [c[0] for c in CRUDOS]
        for crudo in crudos:
            self._recibir_materia_prima(planta, dia, crudo, 20)
            mov = TransicionBodegaService.iniciar_transicion(
                producto=planta.crudos[crudo], bodega_origen=planta.bodegas['mp'],
                bodega_destino=planta.bodegas['linea'], bodega_transicion=planta.bodegas['transito'],
                cantidad=Decimal('20000'), usuario=bodeguero, documento_ref=f'ABAST-CONT-E{planta.numero}')
            TransicionBodegaService.completar_transicion(mov, bodeguero)
        self._actuar(planta.usuarios['jefe_planta'])
        for i, maquina in enumerate(planta.maquinas):
            crudo, color = crudos[i % len(crudos)], COLORES[i % len(COLORES)][0]
            orden = OrdenProduccion.objects.create(
                codigo=f'E{planta.numero}-CONT-{i + 1:02d}', sede=planta.sede, area=maquina.area,
                producto_entrada=planta.crudos[crudo], producto_salida=planta.tenidos[(crudo, color)],
                formula_color=planta.formulas[color], bodega_entrada=planta.bodegas['linea'],
                bodega_salida=planta.bodegas['pt'], bodega_quimicos=planta.bodegas['quimicos'],
                peso_neto_requerido=None, maquina_asignada=maquina, operario_asignado=planta.operarios[0],
                prioridad='normal', estado='pendiente', fecha_inicio_planificada=dia,
                observaciones='Producción continua al cierre de la simulación.')
            orden.estado = 'en_proceso'
            orden._justificacion_auditoria = 'Lanzamiento de la OP a producción.'
            orden.save()

    # -------------------------------------------------------------- ventas
    def _vender(self, planta, dia):
        """El vendedor toma pedidos sobre los lotes en stock hasta cubrir la venta del día."""
        self.reloj.poner(dia, 10)
        vendedor = planta.usuarios['vendedor']
        self._actuar(vendedor)
        # Objetivo acumulado: un pedido grande que hoy se pasa del objetivo se descuenta
        # mañana, así la venta del período respeta --pct-venta.
        planta.por_vender += planta.kg_diarios * Decimal(self.opts['pct_venta']) / 100 * Decimal(
            str(self.rng.uniform(0.7, 1.3)))
        while planta.por_vender > 0:
            disponibles = [pid for pid, cola in planta.lotes_en_stock.items() if cola]
            if not disponibles:
                return
            pedido_kg = self._crear_pedido(planta, dia, vendedor, disponibles)
            if pedido_kg == 0:
                return
            planta.por_vender -= pedido_kg

    def _crear_pedido(self, planta, dia, vendedor, disponibles):
        cliente = self.rng.choice(planta.clientes)
        planta.secuencia_pedido += 1
        pedido = PedidoVenta.objects.create(
            cliente=cliente, sede=planta.sede, vendedor_asignado=vendedor, estado='pendiente',
            guia_remision=f'GR-E{planta.numero}-{planta.secuencia_pedido:06d}',
            fecha_vencimiento=dia + timedelta(days=cliente.plazo_credito_dias), valor_retencion=Decimal('0'))
        codigos, total_kg, total_valor = [], Decimal('0'), Decimal('0')
        for producto_id in self.rng.sample(disponibles, k=min(len(disponibles), self.rng.randint(1, 3))):
            cola = planta.lotes_en_stock[producto_id]
            lotes = [cola.popleft() for _ in range(min(len(cola), self.rng.randint(1, 4)))]
            peso = sum((kg for _, kg in lotes), Decimal('0'))
            producto = Producto.objects.get(pk=producto_id)
            # Nunca por debajo del precio base (regla de DetallePedidoSerializer); el mayorista
            # recibe menos recargo.
            margen = Decimal('1.0') if cliente.nivel_precio == 'mayorista' else Decimal('1.04')
            detalle = DetallePedido.objects.create(
                pedido_venta=pedido, producto=producto, cantidad=len(lotes), piezas=len(lotes) * 24, peso=peso,
                precio_unitario=_dec(producto.precio_base * margen * Decimal(str(self.rng.uniform(1.0, 1.06))),
                                     TRES), incluye_iva=True)
            codigos += [codigo for codigo, _ in lotes]
            total_kg += peso
            total_valor += detalle.total_con_iva
        espera = self.rng.choice([0, 1, 1, 2, 3])
        planta.despachos.append((dia + timedelta(days=espera), pedido.id, codigos))
        atraso = self.rng.choices([0, 10, 45, 120], [80, 12, 6, 2])[0]
        cobro = dia + timedelta(days=espera + cliente.plazo_credito_dias + atraso)
        planta.cobros.append((cobro, cliente, _dec(total_valor, TRES)))
        return total_kg

    def _despachar(self, planta, dia):
        self.reloj.poner(dia, 15)
        despachador = planta.usuarios['despacho']
        self._actuar(despachador)
        pendientes = [d for d in planta.despachos if d[0] <= dia]
        planta.despachos = [d for d in planta.despachos if d[0] > dia]
        for _fecha, pedido_id, codigos in pendientes:
            request = self.fabrica.post('/api/inventory/process-despacho/', {
                'pedidos': [pedido_id], 'lotes': codigos, 'observaciones': 'Despacho por escaneo',
            }, format='json')
            force_authenticate(request, user=despachador)
            respuesta = self.despachador(request)
            if respuesta.status_code != 200:
                raise CommandError(f'Despacho del pedido {pedido_id} falló ({respuesta.status_code}): '
                                   f'{respuesta.data}')

    def _cobrar(self, planta, dia):
        self.reloj.poner(dia, 11)
        vencidos = [c for c in planta.cobros if c[0] <= dia]
        if not vencidos:
            return
        planta.cobros = [c for c in planta.cobros if c[0] > dia]
        self._actuar(planta.usuarios['vendedor'])
        por_cliente = defaultdict(Decimal)
        for _fecha, cliente, monto in vencidos:
            por_cliente[cliente] += monto
        for cliente, monto in por_cliente.items():
            PagoCliente.objects.create(
                cliente=cliente, monto=monto, sede=planta.sede,
                metodo_pago=self.rng.choice(['transferencia', 'transferencia', 'cheque', 'efectivo']),
                comprobante=f'TRF-{planta.numero}-{cliente.id}-{dia:%Y%m%d}')
            PaymentReconciler.reconcile_client_orders(cliente)

    # -------------------------------------------------------------- resumen
    def _resumen(self, plantas, desde, hasta):
        from django.db.models import Count, Sum

        sedes = [p.sede for p in plantas]
        lotes = OrdenProduccion.objects.filter(sede__in=sedes).aggregate(
            n=Count('lotes'), kg=Sum('lotes__peso_neto_producido'))
        stock = StockBodega.objects.filter(bodega__sede__in=sedes).aggregate(kg=Sum('cantidad'))
        self.stdout.write(self.style.SUCCESS(
            f'\nSimulación {desde} → {hasta} ({len(plantas)} sedes)\n'
            f'  Lotes producidos: {lotes["n"]:,}  ({(lotes["kg"] or 0) / 1000:,.1f} t)\n'
            f'  Pedidos: {PedidoVenta.objects.filter(sede__in=sedes).count():,}\n'
            f'  Movimientos de inventario: {MovimientoInventario.objects.count():,}\n'
            f'  Stock final en bodegas: {(stock["kg"] or 0) / 1000:,.1f} t\n'
            f'  Usuarios: e<N>_<rol> (contraseña {PASSWORD})'))
