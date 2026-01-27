from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from gestion.models import (
    CustomUser, Sede, Area, Bodega, Producto, FormulaColor, DetalleFormula, OrdenProduccion
)
from inventory.models import StockBodega, MovimientoInventario
from decimal import Decimal, ROUND_HALF_UP
import random

class Command(BaseCommand):
    help = 'Seeds the database with a large amount of data for stress testing.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Starting database stress test seeding (Improved SQL Server version)...')

        # --- Configuration ---
        NUM_USERS_PER_ROLE = 15
        NUM_YARN_PRODUCTS = 150
        NUM_CHEMICAL_PRODUCTS = 150
        NUM_PRODUCTION_ORDERS = 200
        NUM_INVENTORY_MOVEMENTS = 400

        names = ["Juan", "Maria", "Carlos", "Ana", "Luis", "Elena", "Pedro", "Lucia", "Jorge", "Rosa"]
        last_names = ["Perez", "Garcia", "Rodriguez", "Lopez", "Martinez", "Gonzalez", "Hernandez", "Sanchez"]

        # --- 1. Get Base Objects ---
        self.stdout.write('1/7: Fetching base objects...')
        sede, _ = Sede.objects.get_or_create(nombre='Sede Principal', defaults={'location': 'Quito, Ecuador'})
        area, _ = Area.objects.get_or_create(nombre='Area General', sede=sede)
        bodega_mp, _ = Bodega.objects.get_or_create(nombre='Bodega de Materia Prima', sede=sede)
        bodega_pt, _ = Bodega.objects.get_or_create(nombre='Bodega de Producto Terminado', sede=sede)
        group_names = ['operario', 'bodeguero', 'vendedor', 'jefe_area', 'jefe_planta', 'admin_sede', 'ejecutivo', 'admin_sistemas']
        groups = {name: Group.objects.get_or_create(name=name)[0] for name in group_names}
        self.stdout.write(self.style.SUCCESS('Base objects fetched.'))

        # --- 2. Create Users ---
        self.stdout.write(f'2/7: Creating users...')
        for group_name in group_names:
            for i in range(NUM_USERS_PER_ROLE):
                username = f'stress_user_{group_name}_{i}'
                if not CustomUser.objects.filter(username=username).exists():
                    user = CustomUser(
                        username=username,
                        email=f'{username}@example.com',
                        first_name=random.choice(names),
                        last_name=random.choice(last_names),
                        sede=sede if group_name != 'admin_sistemas' else None,
                        area=area if group_name != 'admin_sistemas' else None,
                    )
                    user.set_password('password123')
                    user.save()
                    user.groups.add(groups[group_name])
                    if group_name != 'admin_sistemas':
                         user.bodegas_asignadas.add(bodega_mp, bodega_pt)
        
        all_users = list(CustomUser.objects.all())
        self.stdout.write(self.style.SUCCESS('Users created.'))

        # --- 3. Create Products ---
        self.stdout.write(f'3/7: Creating products...')
        products = []
        for i in range(NUM_YARN_PRODUCTS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'HIL-STR-{i:04d}',
                defaults={
                    'descripcion': f'Hilo de prueba stress {i}',
                    'tipo': 'hilo',
                    'unidad_medida': 'kg',
                    'stock_minimo': random.randint(50, 200)
                }
            )
            products.append(p)
        for i in range(NUM_CHEMICAL_PRODUCTS):
            p, _ = Producto.objects.get_or_create(
                codigo=f'QMC-STR-{i:04d}',
                defaults={
                    'descripcion': f'Quimico de prueba stress {i}',
                    'tipo': 'quimico',
                    'unidad_medida': 'kg',
                    'stock_minimo': random.randint(10, 50)
                }
            )
            products.append(p)
        self.stdout.write(self.style.SUCCESS('Products created.'))

        # --- 4. Create Initial Stock ---
        self.stdout.write('4/7: Updating initial stock...')
        for product in products:
            qty = Decimal(random.uniform(100, 1000)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            StockBodega.objects.update_or_create(
                bodega=bodega_mp,
                producto=product,
                lote=None,
                defaults={'cantidad': qty}
            )
        self.stdout.write(self.style.SUCCESS('Initial stock updated.'))
        
        # --- 5. Create Formulas and Production Orders ---
        self.stdout.write(f'5/7: Creating formulas and orders...')
        yarn_products = [p for p in products if p.tipo == 'hilo']
        chemical_products = [p for p in products if p.tipo == 'quimico']

        for i in range(NUM_PRODUCTION_ORDERS):
            formula, _ = FormulaColor.objects.get_or_create(
                codigo=f'FORM-STR-{i:03d}',
                defaults={'nombre_color': f'Color Stress {i}'}
            )
            for chem_product in random.sample(chemical_products, random.randint(2, 4)):
                 DetalleFormula.objects.get_or_create(
                    formula_color=formula,
                    producto=chem_product,
                    defaults={'gramos_por_kilo': Decimal(random.uniform(5, 50)).quantize(Decimal('0.00'))}
                )

            OrdenProduccion.objects.get_or_create(
                codigo=f'OP-STR-{i:04d}',
                defaults={
                    'producto': random.choice(yarn_products),
                    'formula_color': formula,
                    'bodega': bodega_mp,
                    'peso_neto_requerido': Decimal(random.uniform(50, 500)).quantize(Decimal('0.00')),
                    'estado': random.choice(['pendiente', 'en_proceso', 'finalizado', 'cancelado']),
                    'sede': sede
                }
            )
        self.stdout.write(self.style.SUCCESS('Production orders created.'))

        # --- 6. Create Inventory Movements ---
        self.stdout.write(f'6/7: Creating movements...')
        # TIPO_MOVIMIENTO_CHOICES = ['COMPRA', 'PRODUCCION', 'TRANSFERENCIA', 'AJUSTE', 'VENTA', 'DEVOLUCION', 'CONSUMO']
        possible_types = ['COMPRA', 'PRODUCCION', 'TRANSFERENCIA', 'AJUSTE', 'VENTA']
        
        for i in range(NUM_INVENTORY_MOVEMENTS):
            mov_type = random.choice(possible_types)
            bodega_origen = random.choice([bodega_mp, bodega_pt]) if mov_type in ['TRANSFERENCIA', 'VENTA', 'CONSUMO', 'AJUSTE'] else None
            bodega_destino = random.choice([bodega_mp, bodega_pt]) if mov_type in ['TRANSFERENCIA', 'COMPRA', 'PRODUCCION', 'DEVOLUCION', 'AJUSTE'] else None
            
            if mov_type == 'TRANSFERENCIA' and bodega_origen == bodega_destino:
                bodega_destino = bodega_pt if bodega_origen == bodega_mp else bodega_mp

            qty = Decimal(random.uniform(10, 100)).quantize(Decimal('0.00'))
            
            MovimientoInventario.objects.create(
                tipo_movimiento=mov_type,
                producto=random.choice(products),
                cantidad=qty,
                bodega_origen=bodega_origen,
                bodega_destino=bodega_destino,
                usuario=random.choice(all_users),
                saldo_resultante=qty, # Simplification for stress test
                documento_ref=f"DOC-STR-{i:05d}"
            )
        self.stdout.write(self.style.SUCCESS('Inventory movements created.'))
        
        self.stdout.write(self.style.SUCCESS('Database stress test seeding completed successfully!'))
