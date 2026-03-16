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
    OrdenProduccion, Proveedor, Maquina, LoteProduccion
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

        group_names = ['operario', 'bodeguero', 'vendedor', 'jefe_area', 'jefe_planta', 'admin_sede', 'ejecutivo', 'admin_sistemas']
        groups = {name: Group.objects.get_or_create(name=name)[0] for name in group_names}

        # Limpiar stock y movimientos antes de repoblar
        self.stdout.write('  Limpiando stock y movimientos...')
        MovimientoInventario.objects.all().delete()
        StockBodega.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 2. Proveedores ---
        self.stdout.write('2/8: Proveedores...')
        proveedores = []
        for i in range(NUM_PROVEEDORES):
            p, _ = Proveedor.objects.get_or_create(
                nombre=f'Proveedor Stress {i+1} S.A.',
                defaults={}
            )
            proveedores.append(p)
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 3. Usuarios bodegueros ---
        self.stdout.write('3/8: Usuarios...')
        bodeguero_users = []
        for i in range(5):
            username = f'stress_bodeguero_{i}'
            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': random.choice(names),
                    'last_name': random.choice(last_names),
                    'sede': sede,
                    'area': area,
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            user.groups.add(groups['bodeguero'])
            for b in bodegas:
                user.bodegas_asignadas.add(b)
            bodeguero_users.append(user)
        all_users = list(CustomUser.objects.filter(groups__name='bodeguero')) or bodeguero_users
        if not all_users:
            all_users = list(CustomUser.objects.all()[:5])

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
        for i in range(NUM_YARN_PRODUCTS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'HIL-STR-{i:04d}',
                defaults={
                    'descripcion': f'Hilo prueba stress {i}',
                    'tipo': 'hilo',
                    'unidad_medida': 'kg',
                    'stock_minimo': Decimal(random.randint(30, 150)),
                }
            )
            products.append(p)
        for i in range(NUM_CHEMICAL_PRODUCTS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'QMC-STR-{i:04d}',
                defaults={
                    'descripcion': f'Quimico prueba stress {i}',
                    'tipo': 'quimico',
                    'unidad_medida': 'kg',
                    'stock_minimo': Decimal(random.randint(5, 40)),
                }
            )
            products.append(p)
        for i in range(NUM_INSUMOS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'INS-STR-{i:04d}',
                defaults={
                    'descripcion': f'Insumo prueba stress {i}',
                    'tipo': 'insumo',
                    'unidad_medida': 'unidades',
                    'stock_minimo': Decimal(random.randint(50, 500)),
                }
            )
            products.append(p)
        yarn_products = [p for p in products if p.tipo == 'hilo']
        chemical_products = [p for p in products if p.tipo == 'quimico']
        self.stdout.write(self.style.SUCCESS('  Ok'))

        # --- 5. Stock inicial (distribuido en múltiples bodegas) + fórmulas/OPs ---
        self.stdout.write('5/8: Stock inicial y Órdenes de Producción...')
        for product in products:
            # Distribuir stock en 2-3 bodegas según tipo
            if product.tipo == 'hilo':
                target_bodegas = random.sample(bodegas_mp + bodegas_pt, min(3, len(bodegas_mp) + len(bodegas_pt)))
            elif product.tipo == 'quimico':
                target_bodegas = random.sample(bodegas_mp + bodegas_ins, min(3, len(bodegas_mp) + len(bodegas_ins)))
            else:
                target_bodegas = random.sample(bodegas_ins + [bodega_mp], min(2, 4))
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
                defaults={'nombre_color': f'Color Stress {i}'}
            )
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
                    'estado': random.choice(['pendiente', 'en_proceso', 'finalizado']),
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
        ops_finalizadas = list(OrdenProduccion.objects.filter(estado='finalizado')[:20])
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
                    s.cantidad = product.stock_minimo - Decimal(random.randint(5, 30))
                    if s.cantidad < 0:
                        s.cantidad = Decimal('0.00')
                    s._justificacion_auditoria = JUSTIF_STRESS
                    s.save()
                    alertas_creadas += 1
                    break
        self.stdout.write(self.style.SUCCESS(f'  ~{alertas_creadas} productos bajo mínimo'))

        self.stdout.write(self.style.SUCCESS('\n✓ Simulación completada. Puedes ver los reportes en el dashboard ejecutivo.'))
