from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from gestion.models import (
    CustomUser, Sede, Area, Bodega, Producto, FormulaColor, DetalleFormula, OrdenProduccion
)
from inventory.models import StockBodega
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds the database with initial data for the entire application.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...')

        # 1. Create Sede and Area
        sede, _ = Sede.objects.get_or_create(nombre='Sede Principal', defaults={'location': 'Quito, Ecuador'})
        area, _ = Area.objects.get_or_create(nombre='Area General', sede=sede)
        self.stdout.write(self.style.SUCCESS('1/8: Sede and Area created.'))

        # 2. Create Bodegas
        bodega_mp, _ = Bodega.objects.get_or_create(nombre='Bodega de Materia Prima', sede=sede)
        bodega_pt, _ = Bodega.objects.get_or_create(nombre='Bodega de Producto Terminado', sede=sede)
        self.stdout.write(self.style.SUCCESS('2/8: Bodegas created.'))

        # 3. Create Products (Hilo)
        hilo_crudo, _ = Producto.objects.get_or_create(
            codigo='HIL-CRU-01',
            defaults={
                'descripcion': 'Hilo Crudo Poliéster 20/1',
                'tipo': 'hilo',
                'unidad_medida': 'kg',
                'stock_minimo': 100
            }
        )
        self.stdout.write(self.style.SUCCESS('3/8: Yarn products created.'))

        # 4. Create Chemical Products
        quimico_rojo, _ = Producto.objects.get_or_create(
            codigo='QMC-ROJO-S',
            defaults={
                'descripcion': 'Colorante Rojo Solido',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 10
            }
        )
        quimico_fijador, _ = Producto.objects.get_or_create(
            codigo='QMC-FIJ-01',
            defaults={
                'descripcion': 'Fijador de Color Universal',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 25
            }
        )
        self.stdout.write(self.style.SUCCESS('4/8: Chemical products created.'))

        # 5. Create Initial Stock
        StockBodega.objects.update_or_create(
            bodega=bodega_mp, producto=hilo_crudo, lote=None,
            defaults={'cantidad': Decimal('500.00')}
        )
        StockBodega.objects.update_or_create(
            bodega=bodega_mp, producto=quimico_rojo, lote=None,
            defaults={'cantidad': Decimal('50.00')}
        )
        StockBodega.objects.update_or_create(
            bodega=bodega_mp, producto=quimico_fijador, lote=None,
            defaults={'cantidad': Decimal('100.00')}
        )
        self.stdout.write(self.style.SUCCESS('5/8: Initial stock created.'))

        # 6. Create a Formula
        formula_rojo, _ = FormulaColor.objects.get_or_create(
            codigo='FORM-ROJO-01',
            defaults={'nombre_color': 'Rojo Intenso'}
        )
        DetalleFormula.objects.get_or_create(
            formula_color=formula_rojo,
            producto=quimico_rojo,
            defaults={'gramos_por_kilo': Decimal('50.0')} # 50g per kg of yarn
        )
        DetalleFormula.objects.get_or_create(
            formula_color=formula_rojo,
            producto=quimico_fijador,
            defaults={'gramos_por_kilo': Decimal('10.0')} # 10g per kg of yarn
        )
        self.stdout.write(self.style.SUCCESS('6/8: Color formula created.'))

        # 7. Create a Production Order
        OrdenProduccion.objects.get_or_create(
            codigo='OP-2025-001',
            defaults={
                'producto': hilo_crudo,
                'formula_color': formula_rojo,
                'bodega': bodega_mp,
                'peso_neto_requerido': Decimal('150.00'),
                'estado': 'en_proceso',
                'sede': sede
            }
        )
        self.stdout.write(self.style.SUCCESS('7/8: Production order created.'))

        # 8. Create users for each group
        password = 'password123'
        group_names = ['operario', 'jefe_area', 'jefe_planta', 'admin_sede', 'ejecutivo', 'admin_sistemas']

        # Ensure groups exist
        for group_name in group_names:
            Group.objects.get_or_create(name=group_name)

        for group_name in group_names:
            username = f'user_{group_name}'
            if CustomUser.objects.filter(username=username).exists():
                CustomUser.objects.get(username=username).delete()

            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=f'{username}@example.com',
                first_name=group_name.replace('_', ' ').title(),
                last_name='Test'
            )
            # Assign Sede to all except admin_sistemas
            if group_name != 'admin_sistemas':
                user.sede = sede
                user.area = area
            
            user.groups.add(Group.objects.get(name=group_name))
            user.save()
        self.stdout.write(self.style.SUCCESS('8/8: Users created and assigned to groups.'))

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))