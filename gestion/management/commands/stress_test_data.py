"""
Pobla la base de datos con datos de estrés para pruebas.
Simula 1 mes de uso del apartado bodeguero con movimientos aleatorios,
para poder visualizar reportes en el dashboard ejecutivo.
"""
import logging
import random
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from gestion.models import (
    Area,
    Bodega,
    Cliente,
    CustomUser,
    DetalleFormula,
    DetallePedido,
    FaseReceta,
    FormulaColor,
    LoteProduccion,
    Maquina,
    OrdenProduccion,
    PagoCliente,
    PedidoVenta,
    ProcesoTintoreria,
    Producto,
    Proveedor,
    Sede,
)
from gestion.services.versionado_formula import VersionadoFormulaService
from inventory.models import (
    DetalleHistorialDespachoPedido,
    HistorialDespacho,
    MovimientoInventario,
    StockBodega,
)
from inventory.utils import safe_get_or_create_stock


def get_stock(bodega, producto, lote=None):
    """Obtiene el stock actual de un producto en una bodega."""
    stock = StockBodega.objects.filter(bodega=bodega, producto=producto, lote=lote).first()
    return stock.cantidad if stock else Decimal('0.00')


logger = logging.getLogger(__name__)

JUSTIF_STRESS = 'Simulación stress test (datos de prueba)'


def apply_movement(stock_obj, delta):
    """Actualiza la cantidad de un StockBodega."""
    if stock_obj:
        stock_obj.cantidad += delta
        if stock_obj.cantidad < 0:
            stock_obj.cantidad = Decimal('0.00')
        stock_obj._justificacion_auditoria = JUSTIF_STRESS
        stock_obj.save()
    return stock_obj.cantidad if stock_obj else Decimal('0.00')


NUM_PROVEEDORES = 12
NUM_ORDENES_PRODUCCION = 180
NOMBRES = ["Juan", "Maria", "Carlos", "Ana", "Luis", "Elena", "Pedro", "Lucia", "Jorge", "Rosa"]
APELLIDOS = ["Perez", "Garcia", "Rodriguez", "Lopez", "Martinez", "Gonzalez", "Hernandez", "Sanchez"]

# Mantener estos nombres alineados con los roles que el frontend ofrece en Login.tsx
# y con los permisos del backend (inventory/permissions.py incluye 'despacho').
GRUPOS = [
    'operario', 'bodeguero', 'vendedor', 'jefe_area', 'jefe_planta',
    'admin_sede', 'ejecutivo', 'admin_sistemas',
    'despacho', 'empaquetado', 'tintorero'
]

# (prefijo de código, cantidad, tipo, descripción, unidad, rango stock_minimo, rango precio_base)
CATALOGO = (
    ('HIL', 150, 'hilo', 'Hilo prueba stress', 'kg', (30, 150), (2.5, 18.0)),
    ('QMC', 100, 'quimico', 'Quimico prueba stress', 'kg', (5, 40), (6.0, 55.0)),
    ('INS', 50, 'insumo', 'Insumo prueba stress', 'unidades', (50, 500), (0.5, 8.0)),
)

# Usuarios demo (los que aparecen en "credenciales de demo" del frontend):
# (username, grupo, nombre, apellido, todas las bodegas, superusuario)
USUARIOS_DEMO = (
    ('user_operario', 'operario', 'Operario', 'Demo', False, False),
    ('user_jefe_area', 'jefe_area', 'Jefe', 'Area', False, False),
    ('user_jefe_planta', 'jefe_planta', 'Jefe', 'Planta', False, False),
    ('user_vendedor', 'vendedor', 'Vendedor', 'Demo', False, False),
    ('user_admin_sede', 'admin_sede', 'Admin', 'Sede', True, False),
    ('user_admin_sistemas', 'admin_sistemas', 'Admin', 'Sistemas', True, False),
    ('user_empaquetado', 'empaquetado', 'Empaquetado', 'Demo', False, False),
    ('user_despacho', 'despacho', 'Despacho', 'Demo', True, False),
    ('user_tintorero', 'tintorero', 'Tintorero', 'Demo', False, False),
    # Super admin "admin/admin" (solo para demo local)
    ('admin', 'admin_sistemas', 'Super', 'Admin', True, True),
)

TIPOS_MOVIMIENTO = ['COMPRA', 'PRODUCCION', 'TRANSFERENCIA', 'VENTA', 'CONSUMO']
# Más compras al inicio del mes, más ventas después
PESOS_PRIMERA_SEMANA = [35, 20, 15, 20, 10]
PESOS_RESTO_DEL_MES = [20, 15, 15, 35, 15]


class _Escenario:
    """Objetos base compartidos por los pasos de la simulación."""


def _sumar_stock(bodega, producto, qty):
    stock, _ = safe_get_or_create_stock(StockBodega, bodega, producto, None, {'cantidad': Decimal('0.00')})
    stock.cantidad += qty
    stock._justificacion_auditoria = JUSTIF_STRESS
    stock.save()
    return stock.cantidad


def _descontar_disponible(bodega, producto, qty):
    """Descuenta hasta lo disponible. Devuelve (qty efectiva, saldo) o None si no hay nada que mover."""
    stock_obj = StockBodega.objects.filter(bodega=bodega, producto=producto, lote=None).first()
    if not stock_obj or stock_obj.cantidad < qty:
        qty = stock_obj.cantidad if stock_obj and stock_obj.cantidad > 0 else Decimal('1.00')
        if qty <= 0:
            return None
    saldo = Decimal('0.00')
    if stock_obj:
        stock_obj.cantidad -= qty
        stock_obj._justificacion_auditoria = JUSTIF_STRESS
        stock_obj.save()
        saldo = stock_obj.cantidad
    return qty, saldo


class Command(BaseCommand):
    help = 'Pobla la BD con simulación de 1 mes de movimientos bodegueros para reportes ejecutivos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Número de días a simular (default: 30)',
        )
        parser.add_argument(
            '--movimientos-por-dia',
            type=int,
            default=25,
            help='Promedio de movimientos por día (default: 25)',
        )

    def _reponer_materia_prima_del_operario_demo(self):
        """Va al final: el paso de alertas deja productos bajo mínimo a propósito y
        podía vaciar la materia prima de una OP del operario (el loadtest fallaba
        con «stock insuficiente»). Cada OP recibe stock en SU bodega de entrada."""
        ops = OrdenProduccion.objects.filter(
            estado='en_proceso', operario_asignado__username='user_operario',
            producto_entrada__isnull=False, bodega_entrada__isnull=False,
        ).select_related('producto_entrada', 'bodega_entrada')
        for op in ops:
            stock, _ = safe_get_or_create_stock(
                StockBodega, op.bodega_entrada, op.producto_entrada, None, {'cantidad': Decimal('0.00')}
            )
            apply_movement(stock, max(Decimal('50000.00') - stock.cantidad, Decimal('0.00')))

    @transaction.atomic
    def handle(self, *args, **options):
        dias = options['dias']
        movs_por_dia = options['movimientos_por_dia']
        self.stdout.write(f'Iniciando simulación de {dias} días (~{movs_por_dia} mov/día)...')

        e = _Escenario()
        self.stdout.write('1/9: Sedes y bodegas (4 sedes, 12 bodegas)...')
        self._crear_sedes_y_bodegas(e)
        e.groups = {name: Group.objects.get_or_create(name=name)[0] for name in GRUPOS}
        self._limpiar_inventario()

        self.stdout.write('2/9: Proveedores...')
        self._crear_proveedores(e)
        self.stdout.write(self.style.SUCCESS('  Ok'))

        self.stdout.write('3/9: Usuarios...')
        self._crear_usuarios(e)
        self.stdout.write(self.style.SUCCESS('  Ok'))

        self.stdout.write('4/9: Productos...')
        self._crear_productos(e)
        self.stdout.write(self.style.SUCCESS('  Ok'))

        self.stdout.write('5/9: Stock inicial y Órdenes de Producción...')
        self._cargar_stock_inicial(e)
        self._crear_ordenes_de_produccion(e)
        self.stdout.write(self.style.SUCCESS('  Ok'))

        self.stdout.write('6/9: Generando movimientos (simulación mensual)...')
        e.now = timezone.now()
        total_movs = self._simular_movimientos(e, dias, movs_por_dia)
        self.stdout.write(self.style.SUCCESS(f'  {total_movs} movimientos creados'))

        self.stdout.write('7/9: Lotes de producción (solo Órdenes finalizadas)...')
        self._crear_lotes_de_ops_finalizadas(e, dias)
        self.stdout.write(self.style.SUCCESS('  Ok'))

        self.stdout.write('8/9: Generando alertas de stock bajo...')
        alertas_creadas = self._generar_alertas_de_stock_bajo(e)
        self.stdout.write(self.style.SUCCESS(f'  ~{alertas_creadas} productos bajo mínimo'))

        self.stdout.write('9/9: Ventas (clientes, pedidos, pagos)...')
        self._limpiar_ventas_previas()
        self._crear_vendedores(e)
        self._crear_clientes(e)
        self._crear_pedidos(e)
        self._crear_pagos(e)

        self._reponer_materia_prima_del_operario_demo()
        self.stdout.write(self.style.SUCCESS('\n✓ Simulación completada. Inventario + Ventas listos para dashboards.'))

    # --- 1. Objetos base: 4 sedes + 12 bodegas (3 por sede) ---
    def _crear_sedes_y_bodegas(self, e):
        # Reutilizar la sede MÁS ANTIGUA ya existente (la del seed_data, donde
        # viven los usuarios demo user_jefe_planta/user_operario/etc.) como sede
        # PRIMARIA, para que el volumen de estrés quede visible al probar el
        # flujo con esos usuarios. Solo se crean sedes EXTRA (nuevas) para poder
        # ejercitar la agregación multi-sede de roles globales (ejecutivo/
        # admin_sistemas); nunca se usa una de ellas como primaria.
        sede = Sede.objects.order_by('id').first()
        if sede is None:
            sede, _ = Sede.objects.get_or_create(nombre='Sede Principal', defaults={'location': 'Quito, Ecuador'})
        sede2, _ = Sede.objects.get_or_create(nombre='Sede Principal 2', defaults={'location': 'Quito Norte, Ecuador'})
        sede_calderon, _ = Sede.objects.get_or_create(
            nombre='Sede Calderon', defaults={'location': 'Calderón, Ecuador'})
        sede_cumbaya, _ = Sede.objects.get_or_create(nombre='Sede Cumbaya', defaults={'location': 'Cumbayá, Ecuador'})
        e.sede = sede
        e.sedes = [sede, sede2, sede_calderon, sede_cumbaya]

        # Reutilizar la primera área existente de la sede primaria (del seed_data)
        # en vez de crear una nueva "Area General" desconectada.
        e.area = Area.objects.filter(sede=sede).order_by('id').first()
        if e.area is None:
            e.area, _ = Area.objects.get_or_create(nombre='Area General', sede=sede)

        # 12 bodegas: 3 por sede (MP, PT, Insumos)
        e.bodegas = []
        for s in e.sedes:
            if s.nombre == 'Sede Principal':
                nombres = ('Bodega de Materia Prima', 'Bodega de Producto Terminado', 'Bodega de Insumos')
            else:
                suf = s.nombre.replace('Sede ', '')
                nombres = (f'Bodega MP {suf}', f'Bodega PT {suf}', f'Bodega Insumos {suf}')
            e.bodegas.extend(Bodega.objects.get_or_create(nombre=n, sede=s)[0] for n in nombres)

        e.bodega_mp = e.bodegas[0]
        e.bodega_pt = e.bodegas[1]
        e.bodegas_mp = e.bodegas[0::3]   # MP por sede
        e.bodegas_pt = e.bodegas[1::3]   # PT por sede
        e.bodegas_ins = e.bodegas[2::3]  # Insumos por sede

    def _limpiar_inventario(self):
        # Limpiar stock y movimientos antes de repoblar. En batches: con
        # volumen de estrés (50k+ movimientos) un solo .all().delete() arma
        # un UPDATE en cascada (SET_NULL de FKs relacionadas) con un
        # parámetro por PK en la cláusula WHERE, y el driver ODBC de SQL
        # Server desborda su contador de parámetros de 16 bits (ver
        # ProgrammingError "-15034 parameter markers... 50502 parameters").
        self.stdout.write('  Limpiando stock y movimientos...')
        # Los despachos apuntan a los movimientos VENTA que se borran abajo: sin
        # ellos la reversión se niega (fail-loud) y el loadtest mide un falso error.
        DetalleHistorialDespachoPedido.objects.all().delete()
        HistorialDespacho.objects.all().delete()
        for modelo in (MovimientoInventario, StockBodega):
            while modelo.objects.exists():
                ids = list(modelo.objects.values_list('pk', flat=True)[:1000])
                modelo.objects.filter(pk__in=ids).delete()
        self.stdout.write(self.style.SUCCESS('  Ok'))

    # --- 2. Proveedores ---
    def _crear_proveedores(self, e):
        e.proveedores = []
        # Crear proveedores por sede para que el panel admin pueda filtrar
        for sede_obj in e.sedes:
            for i in range(max(1, NUM_PROVEEDORES // max(1, len(e.sedes)))):
                p, _ = Proveedor.objects.get_or_create(
                    nombre=f'Proveedor Stress {sede_obj.id}-{i+1} S.A.',
                    defaults={'sede': sede_obj}
                )
                if not p.sede_id:
                    p.sede = sede_obj
                    p.save(update_fields=['sede'])
                e.proveedores.append(p)

    # --- 3. Usuarios ---
    def _crear_usuarios(self, e):
        self._crear_bodegueros(e)
        for username, grupo, nombre, apellido, todas, superusuario in USUARIOS_DEMO:
            self._asegurar_usuario(
                e, username, grupo, nombre, apellido, bodegas_all=todas, is_superuser=superusuario)
        self._asignar_ejecutivo(e)

    def _crear_bodegueros(self, e):
        bodeguero_users = []
        for i in range(5):
            username = f'stress_bodeguero_{i}'
            sede_bod = random.choice(e.sedes)
            bodegas_sede_bod = list(Bodega.objects.filter(sede=sede_bod))
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': random.choice(NOMBRES),
                    'last_name': random.choice(APELLIDOS),
                    'sede': sede_bod,
                    'area': e.area,  # área base (puedes extender a áreas por sede si lo necesitas)
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            user.groups.add(e.groups['bodeguero'])
            # Bodeguero: SOLO bodegas de su sede
            if bodegas_sede_bod:
                user.bodegas_asignadas.set(bodegas_sede_bod)
            bodeguero_users.append(user)
        e.all_users = list(CustomUser.objects.filter(groups__name='bodeguero')) or bodeguero_users
        if not e.all_users:
            e.all_users = list(CustomUser.objects.all()[:5])

        # Asegurar un bodeguero "canónico" para pruebas de UI (solo bodegas de su sede)
        user_bodeguero, created = CustomUser.objects.get_or_create(
            username='user_bodeguero',
            defaults={
                'email': 'user_bodeguero@example.com',
                'first_name': 'Bodeguero',
                'last_name': 'Test',
                'sede': e.sede,
                'area': e.area,
            }
        )
        if created:
            user_bodeguero.set_password('password123')
            user_bodeguero.save()
        user_bodeguero.groups.add(e.groups['bodeguero'])
        # Bodeguero demo: SOLO bodegas de la sede principal (3 bodegas)
        user_bodeguero.bodegas_asignadas.set(Bodega.objects.filter(sede=e.sede))
        if user_bodeguero not in e.all_users:
            e.all_users.append(user_bodeguero)

    @staticmethod
    def _asegurar_usuario(e, username, group, first, last, *, bodegas_all=False, is_superuser=False):
        u, created_u = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': first,
                'last_name': last,
                'sede': e.sede,
                'area': e.area,
                'is_superuser': is_superuser,
                'is_staff': is_superuser,
            }
        )
        if created_u:
            u.set_password('password123' if username != 'admin' else 'admin')
            u.save()
        if group in e.groups:
            u.groups.add(e.groups[group])
        if bodegas_all:
            u.bodegas_asignadas.set(Bodega.objects.all())
        return u

    def _asignar_ejecutivo(self, e):
        # Crear/asignar ejecutivo a todas las bodegas (para dashboard ejecutivo)
        ejecutivo = CustomUser.objects.filter(groups__name='ejecutivo').first()
        if not ejecutivo:
            ejecutivo, _ = CustomUser.objects.get_or_create(
                username='user_ejecutivo',
                defaults={
                    'email': 'user_ejecutivo@example.com',
                    'first_name': 'Ejecutivo',
                    'last_name': 'Test',
                    'sede': e.sede,
                    'area': e.area,
                }
            )
            ejecutivo.set_password('password123')
            ejecutivo.save()
            ejecutivo.groups.add(e.groups['ejecutivo'])
        for b in e.bodegas:
            ejecutivo.bodegas_asignadas.add(b)
        self.stdout.write(self.style.SUCCESS('  Ejecutivo asignado a 12 bodegas'))

    # --- 4. Productos ---
    def _crear_productos(self, e):
        # Para que los dashboards por sede funcionen, asignamos cada producto a una sede
        # y ponemos un precio_base > 0 para que el módulo de ventas pueda usar productos reales.
        e.products = []
        for prefijo, cantidad, tipo, descripcion, unidad, (min_lo, min_hi), (precio_lo, precio_hi) in CATALOGO:
            for i in range(cantidad):
                p, _ = Producto.objects.get_or_create(
                    codigo=f'{prefijo}-STR-{i:04d}',
                    defaults={
                        'descripcion': f'{descripcion} {i}',
                        'tipo': tipo,
                        'unidad_medida': unidad,
                        'stock_minimo': Decimal(random.randint(min_lo, min_hi)),
                        'precio_base': Decimal(random.uniform(precio_lo, precio_hi)).quantize(Decimal('0.001')),
                        'sede': random.choice(e.sedes),
                    }
                )
                if p.sede_id is None:
                    p.sede = random.choice(e.sedes)
                if not p.precio_base or p.precio_base == 0:
                    p.precio_base = Decimal(random.uniform(precio_lo, precio_hi)).quantize(Decimal('0.001'))
                p.save(update_fields=['sede', 'precio_base'])
                e.products.append(p)
        e.yarn_products = [p for p in e.products if p.tipo == 'hilo']
        e.chemical_products = [p for p in e.products if p.tipo == 'quimico']

    # --- 5. Stock inicial (distribuido en múltiples bodegas) + fórmulas/OPs ---
    def _cargar_stock_inicial(self, e):
        bodegas_por_sede = {}
        for b in e.bodegas:
            bodegas_por_sede.setdefault(b.sede_id, []).append(b)
        for product in e.products:
            sede_prod = product.sede or e.sede
            bds_sede = bodegas_por_sede.get(sede_prod.id, e.bodegas)
            bds_mp_sede = [b for b in bds_sede if 'MP' in b.nombre or 'Materia Prima' in b.nombre]
            bds_pt_sede = [b for b in bds_sede if 'PT' in b.nombre or 'Producto Terminado' in b.nombre]
            bds_ins_sede = [b for b in bds_sede if 'Insumos' in b.nombre]

            # Distribuir stock en 2-3 bodegas según tipo
            if product.tipo == 'hilo':
                pool, n = (bds_mp_sede or e.bodegas_mp) + (bds_pt_sede or e.bodegas_pt), 3
            elif product.tipo == 'quimico':
                pool, n = (bds_mp_sede or e.bodegas_mp) + (bds_ins_sede or e.bodegas_ins), 3
            else:
                pool, n = (bds_ins_sede or e.bodegas_ins) + (bds_mp_sede or [e.bodega_mp]), 2
            for bodega in random.sample(pool, min(n, len(pool))):
                qty = Decimal(random.uniform(50, 400)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                stock, _ = safe_get_or_create_stock(StockBodega, bodega, product, None, {'cantidad': Decimal('0.00')})
                stock.cantidad = qty
                stock._justificacion_auditoria = JUSTIF_STRESS
                stock.save()

    def _crear_ordenes_de_produccion(self, e):
        e.maquina, _ = Maquina.objects.get_or_create(
            nombre='Máquina Stress 01',
            defaults={
                'capacidad_maxima': 500, 'eficiencia_ideal': Decimal('0.85'), 'estado': 'operativa', 'area': e.area,
            },
        )
        for i in range(min(NUM_ORDENES_PRODUCCION, 150)):
            self._crear_orden_con_formula(e, i)

        # El rol operario solo ve las OPs que tiene asignadas: sin esto, y sin
        # materia prima en la bodega de entrada, el loadtest no registra lotes.
        # Las OPs con meta se finalizan solas al llegar a su peso y get_or_create
        # no las reabre al re-sembrar; las de producción continua (sin meta)
        # siguen en proceso, así el operario tiene trabajo en corridas repetidas.
        operario_demo = CustomUser.objects.get(username='user_operario')
        formula_continua = FormulaColor.objects.get(codigo='FORM-STR-000')
        for i in range(10):
            producto_continuo = e.yarn_products[i % len(e.yarn_products)]
            OrdenProduccion.objects.get_or_create(
                codigo=f'OP-STR-CONT-{i:02d}',
                defaults={
                    'producto_entrada': producto_continuo,
                    'producto_salida': producto_continuo,
                    'formula_color': formula_continua,
                    'bodega_entrada': e.bodega_mp,
                    'bodega_salida': e.bodega_pt,
                    'area': e.area,
                    'sede': e.sede,
                    'peso_neto_requerido': None,
                    'estado': 'en_proceso',
                    'operario_asignado': operario_demo,
                }
            )
        OrdenProduccion.objects.filter(codigo__startswith='OP-STR-', estado='en_proceso').update(
            operario_asignado=operario_demo
        )

    def _crear_orden_con_formula(self, e, i):
        formula, _ = FormulaColor.objects.get_or_create(
            codigo=f'FORM-STR-{i:03d}',
            defaults={'nombre_color': f'Color Stress {i}', 'sede': random.choice(e.sedes)}
        )
        if not formula.sede_id:
            formula.sede = random.choice(e.sedes)
            formula.save(update_fields=['sede'])
        fase, _ = FaseReceta.objects.get_or_create(
            formula=formula, orden=1,
            defaults={
                'proceso': ProcesoTintoreria.obtener_legacy('tintura', formula.sede),
                'temperatura': 90, 'tiempo': 60,
            }
        )
        for chem in random.sample(e.chemical_products, min(3, len(e.chemical_products))):
            DetalleFormula.objects.get_or_create(
                fase=fase, producto=chem,
                defaults={'gramos_por_kilo': Decimal(random.uniform(5, 40)).quantize(Decimal('0.00'))}
            )
        # Sin versión oficial las OPs en_proceso/finalizada no se pueden lanzar (regla 4)
        VersionadoFormulaService.asegurar_version_oficial(formula, JUSTIF_STRESS, None)
        producto_op = random.choice(e.yarn_products)
        OrdenProduccion.objects.get_or_create(
            codigo=f'OP-STR-{i:04d}',
            defaults={
                # Tintura: mismo SKU de entrada y salida (cambia de color,
                # no de producto) — igual convención usada en el resto
                # del motor de producción para transformaciones 1:1.
                'producto_entrada': producto_op,
                'producto_salida': producto_op,
                'formula_color': formula,
                'bodega_entrada': e.bodega_mp,
                'bodega_salida': e.bodega_pt,
                'peso_neto_requerido': Decimal(random.uniform(40, 300)).quantize(Decimal('0.00')),
                # Alinear con ESTADO_CHOICES del modelo ('pendiente', 'en_proceso', 'finalizada')
                'estado': random.choice(['pendiente', 'en_proceso', 'finalizada']),
                'sede': e.sede,
                # 'area' es requerida por vistas que aíslan por
                # area__sede_id (p. ej. PlantaPulsoDiarioView) — sin esto
                # las OPs de estrés quedan invisibles ahí aunque su sede
                # sea correcta.
                'area': e.area,
            }
        )

    # --- 6. Simulación de 1 mes de movimientos ---
    def _simular_movimientos(self, e, dias, movs_por_dia):
        total_movs = 0
        for day_offset in range(dias):
            fecha_base = e.now - timedelta(days=dias - day_offset)
            num_movs_hoy = max(5, int(random.gauss(movs_por_dia, 8)))
            for _ in range(num_movs_hoy):
                if self._simular_movimiento(e, day_offset, fecha_base, total_movs):
                    total_movs += 1
        return total_movs

    def _simular_movimiento(self, e, day_offset, fecha_base, numero):
        """Un movimiento aleatorio del día con su efecto en stock. False si no hubo qué mover."""
        hora = random.randint(8, 18)
        minuto = random.randint(0, 59)
        fecha_mov = fecha_base.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if fecha_mov.tzinfo is None:
            fecha_mov = timezone.make_aware(fecha_mov)

        pesos = PESOS_PRIMERA_SEMANA if day_offset < 7 else PESOS_RESTO_DEL_MES
        tipo = random.choices(TIPOS_MOVIMIENTO, weights=pesos)[0]

        producto = random.choice(e.products)
        qty = Decimal(random.uniform(5, 80)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        if qty <= 0:
            qty = Decimal('1.00')

        efecto = self._aplicar_movimiento(e, tipo, producto, qty)
        if efecto is None:
            return False
        bodega_origen, bodega_destino, proveedor, qty, saldo_final = efecto

        mov = MovimientoInventario.objects.create(
            tipo_movimiento=tipo,
            producto=producto,
            cantidad=qty,
            bodega_origen=bodega_origen,
            bodega_destino=bodega_destino,
            usuario=random.choice(e.all_users),
            proveedor=proveedor,
            saldo_resultante=saldo_final if saldo_final >= 0 else Decimal('0.00'),
            documento_ref=f"DOC-{fecha_mov.strftime('%Y%m%d')}-{numero:05d}",
        )
        mov.fecha = fecha_mov
        mov.save(update_fields=['fecha'])
        return True

    @staticmethod
    def _aplicar_movimiento(e, tipo, producto, qty):
        """Devuelve (bodega_origen, bodega_destino, proveedor, qty, saldo) o None si no hay qué mover."""
        if tipo == 'COMPRA':
            bodega_destino = random.choice(e.bodegas_mp + e.bodegas_ins)
            proveedor = random.choice(e.proveedores)
            return None, bodega_destino, proveedor, qty, _sumar_stock(bodega_destino, producto, qty)
        if tipo == 'PRODUCCION':
            bodega_destino = random.choice(e.bodegas_pt)
            return None, bodega_destino, None, qty, _sumar_stock(bodega_destino, producto, qty)
        if tipo in ('VENTA', 'CONSUMO'):
            pool = e.bodegas_mp + e.bodegas_pt + e.bodegas_ins if tipo == 'VENTA' else e.bodegas_mp + e.bodegas_ins
            bodega_origen = random.choice(pool)
            resultado = _descontar_disponible(bodega_origen, producto, qty)
            if resultado is None:
                return None
            qty, saldo = resultado
            return bodega_origen, None, None, qty, saldo
        # TRANSFERENCIA
        orig = random.choice(e.bodegas)
        dest = random.choice([b for b in e.bodegas if b != orig])
        stock_orig = StockBodega.objects.filter(bodega=orig, producto=producto, lote=None).first()
        if not stock_orig:
            return None
        qty = min(qty, stock_orig.cantidad)
        if qty <= 0:
            return None
        stock_orig.cantidad -= qty
        stock_orig._justificacion_auditoria = JUSTIF_STRESS
        stock_orig.save()
        return orig, dest, None, qty, _sumar_stock(dest, producto, qty)

    # --- 7. Lotes solo para OPs en estado finalizado ---
    def _crear_lotes_de_ops_finalizadas(self, e, dias):
        # El modelo usa 'finalizada' como valor de estado, no 'finalizado'
        for op in list(OrdenProduccion.objects.filter(estado='finalizada')[:20]):
            try:
                self._crear_lote_con_stock(e, op, dias)
            except Exception:
                logger.exception('Stress: no se pudo cargar el stock de los lotes generados')

    @staticmethod
    def _crear_lote_con_stock(e, op, dias):
        dia = random.randint(1, dias)
        inicio = e.now - timedelta(days=dia)
        final = inicio + timedelta(hours=random.randint(2, 8))
        lote, _creado = LoteProduccion.objects.get_or_create(
            codigo_lote=f'LOT-{op.codigo}-001',
            defaults={
                'orden_produccion': op,
                'peso_neto_producido': op.peso_neto_requerido or Decimal('100.00'),
                'operario': random.choice(e.all_users) if e.all_users else None,
                'maquina': e.maquina,
                'turno': random.choice(['Mañana', 'Tarde', 'Noche']),
                'hora_inicio': inicio,
                'hora_final': final,
            }
        )
        # Sin StockBodega asociado, el lote no es "escaneable" ni
        # "despachable" (ValidateLoteAPIView/process-despacho filtran
        # por StockBodega(lote=..., cantidad__gt=0)) — se necesita
        # para stress testing de escaneo/despacho, no solo para
        # trazabilidad.
        producto_salida = op.producto_salida or op.producto_entrada
        if producto_salida and op.bodega_salida:
            stock, _ = safe_get_or_create_stock(
                StockBodega, op.bodega_salida, producto_salida, lote,
                {'cantidad': Decimal('0.00')}
            )
            stock.cantidad = lote.peso_neto_producido
            stock._justificacion_auditoria = JUSTIF_STRESS
            stock.save()

    # --- 8. Bajar stock de algunos productos para generar alertas ---
    @staticmethod
    def _generar_alertas_de_stock_bajo(e):
        alertas_creadas = 0
        for product in random.sample(e.products, min(45, len(e.products))):
            for s in StockBodega.objects.filter(producto=product, lote=None):
                if s.cantidad >= product.stock_minimo and product.stock_minimo > 0:
                    # Bajar por debajo del mínimo, pero evitando quedarnos exactamente en 0:
                    # deja un pequeño saldo para que no aparezca como stock cero absoluto.
                    nueva_cantidad = product.stock_minimo - Decimal(random.randint(5, 30))
                    s.cantidad = nueva_cantidad if nueva_cantidad > 0 else Decimal('1.00')
                    s._justificacion_auditoria = JUSTIF_STRESS
                    s.save()
                    alertas_creadas += 1
                    break
        return alertas_creadas

    # --- 9. Ventas (clientes + pedidos) para panel ejecutivo ---
    @staticmethod
    def _limpiar_ventas_previas():
        # Importante: si ejecutas este comando múltiples veces, los datos de ventas se acumulan
        # y el dashboard ejecutivo (que trae /pedidos-venta/?limit=100) puede dejar fuera pedidos del vendedor demo.
        # Limpiamos únicamente los datos "stress" identificables para mantener la demo consistente.
        try:
            # Borrar primero pedidos stress (cascada elimina DetallePedido)
            for prefijo in ('GR-STR-', 'GR-DEMO-', 'GR-STRESS-'):
                PedidoVenta.objects.filter(guia_remision__startswith=prefijo).delete()
            # Borrar pagos de clientes stress
            PagoCliente.objects.filter(comprobante__startswith='COMP-STR-').delete()
            # Borrar clientes stress (solo los que creamos aquí)
            Cliente.objects.filter(nombre_razon_social__startswith='Cliente Stress ').delete()
        except Exception:
            logger.exception('Stress: no se pudieron limpiar los datos de una corrida anterior')

    @staticmethod
    def _crear_vendedores(e):
        e.vendedores = list(CustomUser.objects.filter(groups__name='vendedor'))
        # Garantizar vendedores por sede (evitar asignaciones cruzadas entre sedes)
        for sede_obj in e.sedes:
            for i in range(2):
                uname = f'stress_vendedor_{sede_obj.id}_{i}'
                v, created = CustomUser.objects.get_or_create(
                    username=uname,
                    defaults={
                        'email': f'{uname}@example.com',
                        'first_name': 'Vendedor',
                        'last_name': f'Stress {sede_obj.id}-{i}',
                        'sede': sede_obj,
                        'area': e.area,
                    }
                )
                if created:
                    v.set_password('password123')
                    v.save()
                v.groups.add(e.groups['vendedor'])
                if v not in e.vendedores:
                    e.vendedores.append(v)

        # Asegurar que el vendedor demo principal exista y tenga cartera/pedidos
        # (panel vendedor filtra por vendedor_asignado)
        e.vendedor_demo = CustomUser.objects.filter(username='user_vendedor').first()
        if e.vendedor_demo and e.vendedor_demo not in e.vendedores:
            e.vendedores.append(e.vendedor_demo)

    @staticmethod
    def _crear_clientes(e):
        # Crear clientes (ligados a sede y vendedor) evitando asignación cruzada por sede
        vendedor_demo = e.vendedor_demo
        e.clientes = []
        for i in range(40):
            ruc = f'179{i:08d}001'
            # Elegir sede del cliente
            sede_cli = random.choice(e.sedes)
            vendedores_sede = [v for v in e.vendedores if v.sede_id == sede_cli.id]
            vendedor_default = random.choice(vendedores_sede) if vendedores_sede else random.choice(e.vendedores)
            de_la_cartera_demo = bool(vendedor_demo) and i < 12
            c, _created_cli = Cliente.objects.get_or_create(
                ruc_cedula=ruc,
                defaults={
                    'nombre_razon_social': f'Cliente Stress {i+1} S.A.',
                    'direccion_envio': f'Calle {i+1}, Av. Principal',
                    'nivel_precio': random.choice(['mayorista', 'normal']),
                    'tiene_beneficio': random.random() < 0.25,
                    'limite_credito': Decimal(random.randint(2000, 30000)),
                    'plazo_credito_dias': random.choice([0, 8, 15, 30, 45, 60]),
                    'sede': sede_cli,
                    # Si es parte de la cartera demo, forzar vendedor demo y su sede; caso
                    # contrario, vendedor de la misma sede
                    'vendedor_asignado': vendedor_demo if de_la_cartera_demo else vendedor_default,
                    'is_active': True,
                }
            )
            # Si ya existía, forzamos cartera del vendedor demo para que el dashboard no quede vacío
            if de_la_cartera_demo:
                changed = c.vendedor_asignado_id != vendedor_demo.id
                c.vendedor_asignado = vendedor_demo
                if vendedor_demo.sede and c.sede_id != vendedor_demo.sede_id:
                    c.sede = vendedor_demo.sede
                    changed = True
                if changed:
                    c.save(update_fields=['vendedor_asignado', 'sede'])
            e.clientes.append(c)

        # Asegurar coherencia total: todo cliente asignado al vendedor demo debe quedar en su misma sede,
        # porque el panel vendedor aplica multi-tenancy por sede.
        if vendedor_demo and vendedor_demo.sede_id:
            Cliente.objects.filter(vendedor_asignado=vendedor_demo).exclude(sede_id=vendedor_demo.sede_id).update(
                sede_id=vendedor_demo.sede_id
            )

    @staticmethod
    def _crear_pedido(e, cliente, vendedor, guia, estados, fecha_ped, max_items, rango_peso, margen_max):
        plazo = cliente.plazo_credito_dias or 0
        pedido = PedidoVenta.objects.create(
            cliente=cliente,
            guia_remision=guia,
            estado=random.choice(estados),
            esta_pagado=random.random() < 0.55,
            sede=cliente.sede or e.sede,
            vendedor_asignado=vendedor,
            fecha_vencimiento=(fecha_ped.date() + timedelta(days=plazo)) if plazo else fecha_ped.date(),
        )
        PedidoVenta.objects.filter(pk=pedido.pk).update(fecha_pedido=fecha_ped)
        # El número de ítems se sortea después de crear el pedido (orden de sorteo estable).
        n_items = random.randint(1, max_items)
        for p in random.sample(e.productos_venta, min(n_items, len(e.productos_venta))):
            peso = Decimal(random.uniform(*rango_peso)).quantize(Decimal('0.001'))
            precio = (p.precio_base or Decimal('1.000')) * Decimal(random.uniform(1.0, margen_max))
            DetallePedido.objects.create(
                pedido_venta=pedido,
                producto=p,
                cantidad=random.randint(1, 10),
                piezas=random.randint(1, 5),
                peso=peso,
                precio_unitario=precio.quantize(Decimal('0.001')),
                incluye_iva=True,
            )

    def _crear_pedidos(self, e):
        # Crear pedidos/detalles en últimos 60 días
        hoy = timezone.now()
        e.productos_venta = [p for p in e.products if p.tipo in ['hilo', 'tela', 'subproducto']] or e.products[:50]
        # Primero, pedidos generales para poblar los gráficos gerenciales
        for i in range(120):
            cliente = random.choice(e.clientes)
            vendedor = cliente.vendedor_asignado or random.choice(e.vendedores)
            fecha_ped = hoy - timedelta(days=random.randint(0, 60))
            self._crear_pedido(
                e, cliente, vendedor, f'GR-STR-{hoy.year}-{10000 + i}',
                ['pendiente', 'despachado', 'facturado'], fecha_ped, 4, (5, 150), 1.4)

        # Asegurar muchos pedidos MUY recientes para el vendedor demo, para que siempre aparezcan en el
        # límite de 100 registros del dashboard ejecutivo.
        if not e.vendedor_demo:
            return
        demo_clientes = list(Cliente.objects.filter(vendedor_asignado=e.vendedor_demo, is_active=True)[:8])
        if not demo_clientes:
            return
        for i in range(80):
            cliente = random.choice(demo_clientes)
            fecha_ped = hoy - timedelta(days=random.randint(0, 7))
            # Para reportes ejecutivos, típicamente interesa facturado
            self._crear_pedido(
                e, cliente, e.vendedor_demo, f'GR-DEMO-{hoy.year}-{20000 + i}',
                ['facturado', 'despachado'], fecha_ped, 3, (5, 120), 1.35)

    @staticmethod
    def _crear_pagos(e):
        # Crear algunos pagos y reconciliar
        try:
            from gestion.utils import PaymentReconciler
            for cliente in random.sample(e.clientes, min(15, len(e.clientes))):
                # paga una fracción aleatoria del total (para que existan saldos y gráficos)
                total_cli = Decimal('0.00')
                for p in PedidoVenta.objects.filter(cliente=cliente).prefetch_related('detalles'):
                    for d in p.detalles.all():
                        total_cli += (d.peso * d.precio_unitario) * \
                            (Decimal('1.15') if d.incluye_iva else Decimal('1.00'))
                if total_cli > 0:
                    monto_pago = (total_cli * Decimal(random.uniform(0.2, 0.8))).quantize(Decimal('0.001'))
                    PagoCliente.objects.create(
                        cliente=cliente,
                        monto=monto_pago,
                        metodo_pago=random.choice(['transferencia', 'efectivo', 'cheque']),
                        comprobante=f'COMP-STR-{random.randint(1000, 9999)}',
                        sede=cliente.sede or e.sede,
                    )
                    PaymentReconciler.reconcile_client_orders(cliente)
        except Exception:
            # Si algo falla en reconciliación, no detenemos el stress (solo afecta métricas de cartera/pagos)
            logger.exception('Stress: falló la reconciliación de pagos generados')
