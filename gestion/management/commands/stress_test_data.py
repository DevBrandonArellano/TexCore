"""
Pobla la base de datos con datos de estrés para pruebas.
Simula 1 mes de uso del apartado bodeguero con movimientos aleatorios,
para poder visualizar reportes en el dashboard ejecutivo.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta
from gestion.models import (
    CustomUser, Sede, Area, Bodega, Producto, FormulaColor, FaseReceta, DetalleFormula,
    OrdenProduccion, Proveedor, Maquina, LoteProduccion,
    Cliente, PedidoVenta, DetallePedido, PagoCliente
)
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock
from decimal import Decimal, ROUND_HALF_UP
import random


def get_stock(bodega, producto, lote=None):
    """Obtiene el stock actual de un producto en una bodega."""
    try:
        qs = StockBodega.objects.filter(bodega=bodega, producto=producto, lote=lote)
        return qs.first().cantidad if qs.exists() else Decimal('0.00')
    except Exception:
        return Decimal('0.00')


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

    @transaction.atomic
    def handle(self, *args, **options):
        dias = options['dias']
        movs_por_dia = options['movimientos_por_dia']
        self.stdout.write(f'Iniciando simulación de {dias} días (~{movs_por_dia} mov/día)...')

        # --- Configuración ---
        NUM_PROVEEDORES = 12
        NUM_YARN_PRODUCTS = 150
        NUM_CHEMICAL_PRODUCTS = 100
        NUM_INSUMOS = 50
        NUM_ORDENES_PRODUCCION = 180

        names = ["Juan", "Maria", "Carlos", "Ana", "Luis", "Elena", "Pedro", "Lucia", "Jorge", "Rosa"]
        last_names = ["Perez", "Garcia", "Rodriguez", "Lopez", "Martinez", "Gonzalez", "Hernandez", "Sanchez"]

        # --- 1. Objetos base: 4 sedes + 12 bodegas (3 por sede) ---
        self.stdout.write('1/8: Sedes y bodegas (4 sedes, 12 bodegas)...')
        sede, _ = Sede.objects.get_or_create(nombre='Sede Principal', defaults={'location': 'Quito, Ecuador'})
        sede2, _ = Sede.objects.get_or_create(nombre='Sede Principal 2', defaults={'location': 'Quito Norte, Ecuador'})
        sede_calderon, _ = Sede.objects.get_or_create(nombre='Sede Calderon', defaults={'location': 'Calderón, Ecuador'})
        sede_cumbaya, _ = Sede.objects.get_or_create(nombre='Sede Cumbaya', defaults={'location': 'Cumbayá, Ecuador'})
        sedes = [sede, sede2, sede_calderon, sede_cumbaya]

        area, _ = Area.objects.get_or_create(nombre='Area General', sede=sede)

        # 12 bodegas: 3 por sede (MP, PT, Insumos)
        bodegas = []
        for s in sedes:
            if s.nombre == 'Sede Principal':
                n1, n2, n3 = 'Bodega de Materia Prima', 'Bodega de Producto Terminado', 'Bodega de Insumos'
            else:
                suf = s.nombre.replace('Sede ', '')
                n1, n2, n3 = f'Bodega MP {suf}', f'Bodega PT {suf}', f'Bodega Insumos {suf}'
            b1, _ = Bodega.objects.get_or_create(nombre=n1, sede=s)
            b2, _ = Bodega.objects.get_or_create(nombre=n2, sede=s)
            b3, _ = Bodega.objects.get_or_create(nombre=n3, sede=s)
            bodegas.extend([b1, b2, b3])

        bodega_mp, bodega_pt, bodega_insumos = bodegas[0], bodegas[1], bodegas[2]
        bodegas_mp = [b for i, b in enumerate(bodegas) if i % 3 == 0]   # MP por sede
        bodegas_pt = [b for i, b in enumerate(bodegas) if i % 3 == 1]   # PT por sede
        bodegas_ins = [b for i, b in enumerate(bodegas) if i % 3 == 2]  # Insumos por sede

        # Mantener estos nombres alineados con los roles que el frontend ofrece en Login.tsx
        # y con los permisos del backend (inventory/permissions.py incluye 'despacho').
        group_names = [
            'operario', 'bodeguero', 'vendedor', 'jefe_area', 'jefe_planta',
            'admin_sede', 'ejecutivo', 'admin_sistemas',
            'despacho', 'empaquetado', 'tintorero'
        ]
        groups = {name: Group.objects.get_or_create(name=name)[0] for name in group_names}

        # Limpiar stock y movimientos antes de repoblar
        self.stdout.write('  Limpiando stock y movimientos...')
        MovimientoInventario.objects.all().delete()
        StockBodega.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 2. Proveedores ---
        self.stdout.write('2/8: Proveedores...')
        proveedores = []
        # Crear proveedores por sede para que el panel admin pueda filtrar
        for sede_obj in sedes:
            for i in range(max(1, NUM_PROVEEDORES // max(1, len(sedes)))):
                p, _ = Proveedor.objects.get_or_create(
                    nombre=f'Proveedor Stress {sede_obj.id}-{i+1} S.A.',
                    defaults={'sede': sede_obj}
                )
                if not p.sede_id:
                    p.sede = sede_obj
                    p.save(update_fields=['sede'])
                proveedores.append(p)
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 3. Usuarios bodegueros ---
        self.stdout.write('3/8: Usuarios...')
        bodeguero_users = []
        for i in range(5):
            username = f'stress_bodeguero_{i}'
            sede_bod = random.choice(sedes)
            bodegas_sede_bod = list(Bodega.objects.filter(sede=sede_bod))
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': random.choice(names),
                    'last_name': random.choice(last_names),
                    'sede': sede_bod,
                    'area': area,  # área base (puedes extender a áreas por sede si lo necesitas)
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            user.groups.add(groups['bodeguero'])
            # Bodeguero: SOLO bodegas de su sede
            if bodegas_sede_bod:
                user.bodegas_asignadas.set(bodegas_sede_bod)
            bodeguero_users.append(user)
        all_users = list(CustomUser.objects.filter(groups__name='bodeguero')) or bodeguero_users
        if not all_users:
            all_users = list(CustomUser.objects.all()[:5])

        # Asegurar un bodeguero "canónico" para pruebas de UI (solo bodegas de su sede)
        user_bodeguero, created = CustomUser.objects.get_or_create(
            username='user_bodeguero',
            defaults={
                'email': 'user_bodeguero@example.com',
                'first_name': 'Bodeguero',
                'last_name': 'Test',
                'sede': sede,
                'area': area,
            }
        )
        if created:
            user_bodeguero.set_password('password123')
            user_bodeguero.save()
        user_bodeguero.groups.add(groups['bodeguero'])
        # Bodeguero demo: SOLO bodegas de la sede principal (3 bodegas)
        user_bodeguero.bodegas_asignadas.set(Bodega.objects.filter(sede=sede))
        if user_bodeguero not in all_users:
            all_users.append(user_bodeguero)

        # Crear usuarios demo adicionales (los que aparecen en "credenciales de demo" del frontend)
        def ensure_user(username: str, group: str, first: str, last: str, *,
                        sede_obj=None, area_obj=None, bodegas_all: bool = False, is_superuser: bool = False):
            u, created_u = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': first,
                    'last_name': last,
                    'sede': sede_obj,
                    'area': area_obj,
                    'is_superuser': is_superuser,
                    'is_staff': is_superuser,
                }
            )
            if created_u:
                u.set_password('password123' if username != 'admin' else 'admin')
                u.save()
            if group in groups:
                u.groups.add(groups[group])
            if bodegas_all:
                u.bodegas_asignadas.set(Bodega.objects.all())
            return u

        # Operario / Jefaturas
        ensure_user('user_operario', 'operario', 'Operario', 'Demo', sede_obj=sede, area_obj=area)
        ensure_user('user_jefe_area', 'jefe_area', 'Jefe', 'Area', sede_obj=sede, area_obj=area)
        ensure_user('user_jefe_planta', 'jefe_planta', 'Jefe', 'Planta', sede_obj=sede, area_obj=area)

        # Ventas / Admins
        ensure_user('user_vendedor', 'vendedor', 'Vendedor', 'Demo', sede_obj=sede, area_obj=area)
        ensure_user('user_admin_sede', 'admin_sede', 'Admin', 'Sede', sede_obj=sede, area_obj=area, bodegas_all=True)
        ensure_user('user_admin_sistemas', 'admin_sistemas', 'Admin', 'Sistemas', sede_obj=sede, area_obj=area, bodegas_all=True)

        # Operaciones adicionales
        ensure_user('user_empaquetado', 'empaquetado', 'Empaquetado', 'Demo', sede_obj=sede, area_obj=area)
        ensure_user('user_despacho', 'despacho', 'Despacho', 'Demo', sede_obj=sede, area_obj=area)
        ensure_user('user_tintorero', 'tintorero', 'Tintorero', 'Demo', sede_obj=sede, area_obj=area)

        # Super admin "admin/admin" (solo para demo local)
        ensure_user('admin', 'admin_sistemas', 'Super', 'Admin', sede_obj=sede, area_obj=area, bodegas_all=True, is_superuser=True)

        # Crear/asignar ejecutivo a todas las bodegas (para dashboard ejecutivo)
        ejecutivo = CustomUser.objects.filter(groups__name='ejecutivo').first()
        if not ejecutivo:
            ejecutivo, _ = CustomUser.objects.get_or_create(
                username='user_ejecutivo',
                defaults={
                    'email': 'user_ejecutivo@example.com',
                    'first_name': 'Ejecutivo',
                    'last_name': 'Test',
                    'sede': sede,
                    'area': area,
                }
            )
            ejecutivo.set_password('password123')
            ejecutivo.save()
            ejecutivo.groups.add(groups['ejecutivo'])
        for b in bodegas:
            ejecutivo.bodegas_asignadas.add(b)
        self.stdout.write(self.style.SUCCESS('  Ejecutivo asignado a 12 bodegas'))

        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 4. Productos ---
        self.stdout.write('4/8: Productos...')
        products = []
        # Para que los dashboards por sede funcionen, asignamos cada producto a una sede
        # y ponemos un precio_base > 0 para que el módulo de ventas pueda usar productos reales.
        for i in range(NUM_YARN_PRODUCTS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'HIL-STR-{i:04d}',
                defaults={
                    'descripcion': f'Hilo prueba stress {i}',
                    'tipo': 'hilo',
                    'unidad_medida': 'kg',
                    'stock_minimo': Decimal(random.randint(30, 150)),
                    'precio_base': Decimal(random.uniform(2.5, 18.0)).quantize(Decimal('0.001')),
                    'sede': random.choice(sedes),
                }
            )
            if p.sede_id is None:
                p.sede = random.choice(sedes)
            if not p.precio_base or p.precio_base == 0:
                p.precio_base = Decimal(random.uniform(2.5, 18.0)).quantize(Decimal('0.001'))
            p.save(update_fields=['sede', 'precio_base'])
            products.append(p)
        for i in range(NUM_CHEMICAL_PRODUCTS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'QMC-STR-{i:04d}',
                defaults={
                    'descripcion': f'Quimico prueba stress {i}',
                    'tipo': 'quimico',
                    'unidad_medida': 'kg',
                    'stock_minimo': Decimal(random.randint(5, 40)),
                    'precio_base': Decimal(random.uniform(6.0, 55.0)).quantize(Decimal('0.001')),
                    'sede': random.choice(sedes),
                }
            )
            if p.sede_id is None:
                p.sede = random.choice(sedes)
            if not p.precio_base or p.precio_base == 0:
                p.precio_base = Decimal(random.uniform(6.0, 55.0)).quantize(Decimal('0.001'))
            p.save(update_fields=['sede', 'precio_base'])
            products.append(p)
        for i in range(NUM_INSUMOS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'INS-STR-{i:04d}',
                defaults={
                    'descripcion': f'Insumo prueba stress {i}',
                    'tipo': 'insumo',
                    'unidad_medida': 'unidades',
                    'stock_minimo': Decimal(random.randint(50, 500)),
                    'precio_base': Decimal(random.uniform(0.5, 8.0)).quantize(Decimal('0.001')),
                    'sede': random.choice(sedes),
                }
            )
            if p.sede_id is None:
                p.sede = random.choice(sedes)
            if not p.precio_base or p.precio_base == 0:
                p.precio_base = Decimal(random.uniform(0.5, 8.0)).quantize(Decimal('0.001'))
            p.save(update_fields=['sede', 'precio_base'])
            products.append(p)
        yarn_products = [p for p in products if p.tipo == 'hilo']
        chemical_products = [p for p in products if p.tipo == 'quimico']
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 5. Stock inicial (distribuido en múltiples bodegas) + fórmulas/OPs ---
        self.stdout.write('5/8: Stock inicial y Órdenes de Producción...')
        bodegas_por_sede = {}
        for b in bodegas:
            bodegas_por_sede.setdefault(b.sede_id, []).append(b)
        for product in products:
            sede_prod = product.sede or sede
            bds_sede = bodegas_por_sede.get(sede_prod.id, bodegas)
            bds_mp_sede = [b for b in bds_sede if 'MP' in b.nombre or 'Materia Prima' in b.nombre]
            bds_pt_sede = [b for b in bds_sede if 'PT' in b.nombre or 'Producto Terminado' in b.nombre]
            bds_ins_sede = [b for b in bds_sede if 'Insumos' in b.nombre]

            # Distribuir stock en 2-3 bodegas según tipo
            if product.tipo == 'hilo':
                pool = (bds_mp_sede or bodegas_mp) + (bds_pt_sede or bodegas_pt)
                target_bodegas = random.sample(pool, min(3, len(pool)))
            elif product.tipo == 'quimico':
                pool = (bds_mp_sede or bodegas_mp) + (bds_ins_sede or bodegas_ins)
                target_bodegas = random.sample(pool, min(3, len(pool)))
            else:
                pool = (bds_ins_sede or bodegas_ins) + (bds_mp_sede or [bodega_mp])
                target_bodegas = random.sample(pool, min(2, len(pool)))
            for bodega in target_bodegas:
                qty = Decimal(random.uniform(50, 400)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                stock, _ = safe_get_or_create_stock(StockBodega, bodega, product, None, {'cantidad': Decimal('0.00')})
                stock.cantidad = qty
                stock._justificacion_auditoria = JUSTIF_STRESS
                stock.save()

        maquina, _ = Maquina.objects.get_or_create(
            nombre='Máquina Stress 01',
            defaults={'capacidad_maxima': 500, 'eficiencia_ideal': Decimal('0.85'), 'estado': 'operativa', 'area': area}
        )

        for i in range(min(NUM_ORDENES_PRODUCCION, 150)):
            formula, _ = FormulaColor.objects.get_or_create(
                codigo=f'FORM-STR-{i:03d}',
                defaults={'nombre_color': f'Color Stress {i}', 'sede': random.choice(sedes)}
            )
            if not formula.sede_id:
                formula.sede = random.choice(sedes)
                formula.save(update_fields=['sede'])
            fase, _ = FaseReceta.objects.get_or_create(
                formula=formula, orden=1,
                defaults={'nombre': 'tintura', 'temperatura': 90, 'tiempo': 60}
            )
            for chem in random.sample(chemical_products, min(3, len(chemical_products))):
                DetalleFormula.objects.get_or_create(
                    fase=fase, producto=chem,
                    defaults={'gramos_por_kilo': Decimal(random.uniform(5, 40)).quantize(Decimal('0.00'))}
                )
            OrdenProduccion.objects.get_or_create(
                codigo=f'OP-STR-{i:04d}',
                defaults={
                    'producto': random.choice(yarn_products),
                    'formula_color': formula,
                    'bodega': bodega_mp,
                    'peso_neto_requerido': Decimal(random.uniform(40, 300)).quantize(Decimal('0.00')),
                    # Alinear con ESTADO_CHOICES del modelo ('pendiente', 'en_proceso', 'finalizada')
                    'estado': random.choice(['pendiente', 'en_proceso', 'finalizada']),
                    'sede': sede
                }
            )
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 6. Simulación de 1 mes de movimientos ---
        self.stdout.write('6/8: Generando movimientos (simulación mensual)...')
        now = timezone.now()
        total_movs = 0

        # Tipos y pesos para distribución realista
        tipos_entrada = ['COMPRA', 'PRODUCCION', 'DEVOLUCION']
        tipos_salida = ['VENTA', 'CONSUMO', 'TRANSFERENCIA']
        tipos_transfer = ['TRANSFERENCIA']

        for day_offset in range(dias):
            fecha_base = now - timedelta(days=dias - day_offset)
            num_movs_hoy = max(5, int(random.gauss(movs_por_dia, 8)))

            for _ in range(num_movs_hoy):
                hora = random.randint(8, 18)
                minuto = random.randint(0, 59)
                fecha_mov = fecha_base.replace(hour=hora, minute=minuto, second=0, microsecond=0)
                if fecha_mov.tzinfo is None:
                    fecha_mov = timezone.make_aware(fecha_mov)

                # Decidir tipo (más compras al inicio, más ventas después)
                r = random.random()
                if day_offset < 7:
                    tipo = random.choices(
                        ['COMPRA', 'PRODUCCION', 'TRANSFERENCIA', 'VENTA', 'CONSUMO'],
                        weights=[35, 20, 15, 20, 10]
                    )[0]
                else:
                    tipo = random.choices(
                        ['COMPRA', 'PRODUCCION', 'TRANSFERENCIA', 'VENTA', 'CONSUMO'],
                        weights=[20, 15, 15, 35, 15]
                    )[0]

                producto = random.choice(products)
                qty = Decimal(random.uniform(5, 80)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                if qty <= 0:
                    qty = Decimal('1.00')

                bodega_origen = None
                bodega_destino = None
                proveedor = None
                saldo_final = Decimal('0.00')

                if tipo == 'COMPRA':
                    bodega_destino = random.choice(bodegas_mp + bodegas_ins)
                    proveedor = random.choice(proveedores)
                    stock, created = safe_get_or_create_stock(StockBodega, bodega_destino, producto, None, {'cantidad': Decimal('0.00')})
                    stock.cantidad += qty
                    stock._justificacion_auditoria = JUSTIF_STRESS
                    stock.save()
                    saldo_final = stock.cantidad

                elif tipo == 'PRODUCCION':
                    bodega_destino = random.choice(bodegas_pt)
                    stock, created = safe_get_or_create_stock(StockBodega, bodega_destino, producto, None, {'cantidad': Decimal('0.00')})
                    stock.cantidad += qty
                    stock._justificacion_auditoria = JUSTIF_STRESS
                    stock.save()
                    saldo_final = stock.cantidad

                elif tipo == 'DEVOLUCION':
                    bodega_destino = random.choice(bodegas)
                    stock, created = safe_get_or_create_stock(StockBodega, bodega_destino, producto, None, {'cantidad': Decimal('0.00')})
                    stock.cantidad += qty
                    stock._justificacion_auditoria = JUSTIF_STRESS
                    stock.save()
                    saldo_final = stock.cantidad

                elif tipo == 'VENTA':
                    bodega_origen = random.choice(bodegas_mp + bodegas_pt + bodegas_ins)
                    stock_obj = StockBodega.objects.filter(bodega=bodega_origen, producto=producto, lote=None).first()
                    if not stock_obj or stock_obj.cantidad < qty:
                        qty = stock_obj.cantidad if stock_obj and stock_obj.cantidad > 0 else Decimal('1.00')
                        if qty <= 0:
                            continue
                    if stock_obj:
                        stock_obj.cantidad -= qty
                        stock_obj._justificacion_auditoria = JUSTIF_STRESS
                        stock_obj.save()
                        saldo_final = stock_obj.cantidad

                elif tipo == 'CONSUMO':
                    bodega_origen = random.choice(bodegas_mp + bodegas_ins)
                    stock_obj = StockBodega.objects.filter(bodega=bodega_origen, producto=producto, lote=None).first()
                    if not stock_obj or stock_obj.cantidad < qty:
                        qty = stock_obj.cantidad if stock_obj and stock_obj.cantidad > 0 else Decimal('1.00')
                        if qty <= 0:
                            continue
                    if stock_obj:
                        stock_obj.cantidad -= qty
                        stock_obj._justificacion_auditoria = JUSTIF_STRESS
                        stock_obj.save()
                        saldo_final = stock_obj.cantidad

                elif tipo == 'TRANSFERENCIA':
                    orig = random.choice(bodegas)
                    dest = random.choice([b for b in bodegas if b != orig])
                    stock_orig = StockBodega.objects.filter(bodega=orig, producto=producto, lote=None).first()
                    if not stock_orig:
                        continue
                    if stock_orig.cantidad < qty:
                        qty = stock_orig.cantidad
                    if qty <= 0:
                        continue
                    bodega_origen = orig
                    bodega_destino = dest
                    stock_orig.cantidad -= qty
                    stock_orig._justificacion_auditoria = JUSTIF_STRESS
                    stock_orig.save()
                    stock_dest, _ = safe_get_or_create_stock(StockBodega, dest, producto, None, {'cantidad': Decimal('0.00')})
                    stock_dest.cantidad += qty
                    stock_dest._justificacion_auditoria = JUSTIF_STRESS
                    stock_dest.save()
                    saldo_final = stock_dest.cantidad

                mov = MovimientoInventario.objects.create(
                    tipo_movimiento=tipo,
                    producto=producto,
                    cantidad=qty,
                    bodega_origen=bodega_origen,
                    bodega_destino=bodega_destino,
                    usuario=random.choice(all_users),
                    proveedor=proveedor,
                    saldo_resultante=saldo_final if saldo_final >= 0 else Decimal('0.00'),
                    documento_ref=f"DOC-{fecha_mov.strftime('%Y%m%d')}-{total_movs:05d}",
                )
                mov.fecha = fecha_mov
                mov.save(update_fields=['fecha'])
                total_movs += 1

        self.stdout.write(self.style.SUCCESS(f'  {total_movs} movimientos creados'))

        # --- 7. Crear lotes solo para OPs en estado finalizado ---
        self.stdout.write('7/8: Lotes de producción (solo Órdenes finalizadas)...')
        # El modelo usa 'finalizada' como valor de estado, no 'finalizado'
        ops_finalizadas = list(OrdenProduccion.objects.filter(estado='finalizada')[:20])
        for op in ops_finalizadas:
            try:
                dia = random.randint(1, dias)
                inicio = now - timedelta(days=dia)
                final = inicio + timedelta(hours=random.randint(2, 8))
                LoteProduccion.objects.get_or_create(
                    codigo_lote=f'LOT-{op.codigo}-001',
                    defaults={
                        'orden_produccion': op,
                        'peso_neto_producido': op.peso_neto_requerido or Decimal('100.00'),
                        'operario': random.choice(all_users) if all_users else None,
                        'maquina': maquina,
                        'turno': random.choice(['Mañana', 'Tarde', 'Noche']),
                        'hora_inicio': inicio,
                        'hora_final': final,
                    }
                )
            except Exception:
                pass
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 8. Bajar stock de algunos productos para generar alertas ---
        self.stdout.write('8/8: Generando alertas de stock bajo...')
        alertas_creadas = 0
        for product in random.sample(products, min(45, len(products))):
            stocks = StockBodega.objects.filter(producto=product, lote=None)
            for s in stocks:
                if s.cantidad >= product.stock_minimo and product.stock_minimo > 0:
                    # Bajar por debajo del mínimo, pero evitando quedarnos exactamente en 0
                    nueva_cantidad = product.stock_minimo - Decimal(random.randint(5, 30))
                    if nueva_cantidad <= 0:
                        # Deja un pequeño saldo para que no aparezca como stock cero absoluto
                        nueva_cantidad = Decimal('1.00')
                    s.cantidad = nueva_cantidad
                    s._justificacion_auditoria = JUSTIF_STRESS
                    s.save()
                    alertas_creadas += 1
                    break
        self.stdout.write(self.style.SUCCESS(f'  ~{alertas_creadas} productos bajo mínimo'))

        # --- 9. Ventas (clientes + pedidos) para panel ejecutivo ---
        self.stdout.write('9/9: Ventas (clientes, pedidos, pagos)...')
        # Importante: si ejecutas este comando múltiples veces, los datos de ventas se acumulan
        # y el dashboard ejecutivo (que trae /pedidos-venta/?limit=100) puede dejar fuera pedidos del vendedor demo.
        # Limpiamos únicamente los datos "stress" identificables para mantener la demo consistente.
        try:
            # Borrar primero pedidos stress (cascada elimina DetallePedido)
            PedidoVenta.objects.filter(guia_remision__startswith='GR-STR-').delete()
            PedidoVenta.objects.filter(guia_remision__startswith='GR-DEMO-').delete()
            PedidoVenta.objects.filter(guia_remision__startswith='GR-STRESS-').delete()
            # Borrar pagos de clientes stress
            PagoCliente.objects.filter(comprobante__startswith='COMP-STR-').delete()
            # Borrar clientes stress (solo los que creamos aquí)
            Cliente.objects.filter(nombre_razon_social__startswith='Cliente Stress ').delete()
        except Exception:
            pass

        vendedores = list(CustomUser.objects.filter(groups__name='vendedor'))
        # Garantizar vendedores por sede (evitar asignaciones cruzadas entre sedes)
        for sede_obj in sedes:
            for i in range(2):
                uname = f'stress_vendedor_{sede_obj.id}_{i}'
                v, created = CustomUser.objects.get_or_create(
                    username=uname,
                    defaults={
                        'email': f'{uname}@example.com',
                        'first_name': 'Vendedor',
                        'last_name': f'Stress {sede_obj.id}-{i}',
                        'sede': sede_obj,
                        'area': area,
                    }
                )
                if created:
                    v.set_password('password123')
                    v.save()
                v.groups.add(groups['vendedor'])
                if v not in vendedores:
                    vendedores.append(v)

        # Asegurar que el vendedor demo principal exista y tenga cartera/pedidos (panel vendedor filtra por vendedor_asignado)
        vendedor_demo = CustomUser.objects.filter(username='user_vendedor').first()
        if vendedor_demo and vendedor_demo not in vendedores:
            vendedores.append(vendedor_demo)

        # Crear clientes (ligados a sede y vendedor) evitando asignación cruzada por sede
        clientes = []
        for i in range(40):
            ruc = f'179{i:08d}001'
            # Elegir sede del cliente
            sede_cli = random.choice(sedes)
            vendedores_sede = [v for v in vendedores if v.sede_id == sede_cli.id]
            vendedor_default = random.choice(vendedores_sede) if vendedores_sede else random.choice(vendedores)
            c, created_cli = Cliente.objects.get_or_create(
                ruc_cedula=ruc,
                defaults={
                    'nombre_razon_social': f'Cliente Stress {i+1} S.A.',
                    'direccion_envio': f'Calle {i+1}, Av. Principal',
                    'nivel_precio': random.choice(['mayorista', 'normal']),
                    'tiene_beneficio': random.random() < 0.25,
                    'limite_credito': Decimal(random.randint(2000, 30000)),
                    'plazo_credito_dias': random.choice([0, 8, 15, 30, 45, 60]),
                    'sede': sede_cli,
                    # Si es parte de la cartera demo, forzar vendedor demo y su sede; caso contrario, vendedor de la misma sede
                    'vendedor_asignado': (vendedor_demo if (vendedor_demo and i < 12) else vendedor_default),
                    'is_active': True,
                }
            )
            # Si ya existía, forzamos cartera del vendedor demo para que el dashboard no quede vacío
            if vendedor_demo and i < 12:
                changed = False
                if c.vendedor_asignado_id != vendedor_demo.id:
                    c.vendedor_asignado = vendedor_demo
                    changed = True
                if vendedor_demo.sede and c.sede_id != vendedor_demo.sede_id:
                    c.sede = vendedor_demo.sede
                    changed = True
                if changed:
                    c.save(update_fields=['vendedor_asignado', 'sede'])
            clientes.append(c)

        # Asegurar coherencia total: todo cliente asignado al vendedor demo debe quedar en su misma sede,
        # porque el panel vendedor aplica multi-tenancy por sede.
        if vendedor_demo and vendedor_demo.sede_id:
            Cliente.objects.filter(vendedor_asignado=vendedor_demo).exclude(sede_id=vendedor_demo.sede_id).update(
                sede_id=vendedor_demo.sede_id
            )

        # Crear pedidos/detalles en últimos 60 días
        hoy = timezone.now()
        productos_venta = [p for p in products if p.tipo in ['hilo', 'tela', 'subproducto']]
        if not productos_venta:
            productos_venta = products[:50]
        # Primero, pedidos generales para poblar los gráficos gerenciales
        for i in range(120):
            cliente = random.choice(clientes)
            vendedor = cliente.vendedor_asignado or random.choice(vendedores)
            dias_atras = random.randint(0, 60)
            fecha_ped = hoy - timedelta(days=dias_atras)
            plazo = cliente.plazo_credito_dias or 0

            pedido = PedidoVenta.objects.create(
                cliente=cliente,
                guia_remision=f'GR-STR-{hoy.year}-{10000 + i}',
                estado=random.choice(['pendiente', 'despachado', 'facturado']),
                esta_pagado=random.random() < 0.55,
                sede=cliente.sede or sede,
                vendedor_asignado=vendedor,
                fecha_vencimiento=(fecha_ped.date() + timedelta(days=plazo)) if plazo else fecha_ped.date(),
            )
            PedidoVenta.objects.filter(pk=pedido.pk).update(fecha_pedido=fecha_ped)

            num_items = random.randint(1, 4)
            prods = random.sample(productos_venta, min(num_items, len(productos_venta)))
            for p in prods:
                peso = Decimal(random.uniform(5, 150)).quantize(Decimal('0.001'))
                precio = (p.precio_base or Decimal('1.000')) * Decimal(random.uniform(1.0, 1.4))
                DetallePedido.objects.create(
                    pedido_venta=pedido,
                    producto=p,
                    cantidad=random.randint(1, 10),
                    piezas=random.randint(1, 5),
                    peso=peso,
                    precio_unitario=precio.quantize(Decimal('0.001')),
                    incluye_iva=True,
                )

        # Asegurar muchos pedidos MUY recientes para el vendedor demo, para que siempre aparezcan en el
        # límite de 100 registros del dashboard ejecutivo.
        if vendedor_demo:
            demo_clientes = list(Cliente.objects.filter(vendedor_asignado=vendedor_demo, is_active=True)[:8])
            for i in range(80):
                if not demo_clientes:
                    break
                cliente = random.choice(demo_clientes)
                dias_atras = random.randint(0, 7)
                fecha_ped = hoy - timedelta(days=dias_atras)
                plazo = cliente.plazo_credito_dias or 0
                pedido = PedidoVenta.objects.create(
                    cliente=cliente,
                    guia_remision=f'GR-DEMO-{hoy.year}-{20000 + i}',
                    # Para reportes ejecutivos, típicamente interesa facturado
                    estado=random.choice(['facturado', 'despachado']),
                    esta_pagado=random.random() < 0.55,
                    sede=cliente.sede or sede,
                    vendedor_asignado=vendedor_demo,
                    fecha_vencimiento=(fecha_ped.date() + timedelta(days=plazo)) if plazo else fecha_ped.date(),
                )
                PedidoVenta.objects.filter(pk=pedido.pk).update(fecha_pedido=fecha_ped)
                prods = random.sample(productos_venta, min(random.randint(1, 3), len(productos_venta)))
                for p in prods:
                    peso = Decimal(random.uniform(5, 120)).quantize(Decimal('0.001'))
                    precio = (p.precio_base or Decimal('1.000')) * Decimal(random.uniform(1.0, 1.35))
                    DetallePedido.objects.create(
                        pedido_venta=pedido,
                        producto=p,
                        cantidad=random.randint(1, 10),
                        piezas=random.randint(1, 5),
                        peso=peso,
                        precio_unitario=precio.quantize(Decimal('0.001')),
                        incluye_iva=True,
                    )

        # Crear algunos pagos y reconciliar
        try:
            from gestion.utils import PaymentReconciler
            for cliente in random.sample(clientes, min(15, len(clientes))):
                # paga una fracción aleatoria del total (para que existan saldos y gráficos)
                pedidos_cli = PedidoVenta.objects.filter(cliente=cliente).prefetch_related('detalles')
                total_cli = Decimal('0.00')
                for p in pedidos_cli:
                    for d in p.detalles.all():
                        total_cli += (d.peso * d.precio_unitario) * (Decimal('1.15') if d.incluye_iva else Decimal('1.00'))
                if total_cli > 0:
                    monto_pago = (total_cli * Decimal(random.uniform(0.2, 0.8))).quantize(Decimal('0.001'))
                    PagoCliente.objects.create(
                        cliente=cliente,
                        monto=monto_pago,
                        metodo_pago=random.choice(['transferencia', 'efectivo', 'cheque']),
                        comprobante=f'COMP-STR-{random.randint(1000, 9999)}',
                        sede=cliente.sede or sede,
                    )
                    PaymentReconciler.reconcile_client_orders(cliente)
        except Exception:
            # Si algo falla en reconciliación, no detenemos el stress (solo afecta métricas de cartera/pagos)
            pass

        self.stdout.write(self.style.SUCCESS('\n✓ Simulación completada. Inventario + Ventas listos para dashboards.'))
