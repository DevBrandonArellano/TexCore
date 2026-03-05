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
        area_tejeduria, _ = Area.objects.get_or_create(nombre='Tejeduria', sede=sede)
        area_empaque, _ = Area.objects.get_or_create(nombre='Empaque', sede=sede)
        
        self.stdout.write(self.style.SUCCESS('1/8: Sede and Areas (General, Tejeduria, Empaque) created.'))

        # 2. Create Bodegas
        bodega_mp, _ = Bodega.objects.get_or_create(nombre='Bodega de Materia Prima', sede=sede)
        bodega_pt, _ = Bodega.objects.get_or_create(nombre='Bodega de Producto Terminado', sede=sede)
        bodega_insumos, _ = Bodega.objects.get_or_create(nombre='Bodega de Insumos', sede=sede)
        
        self.stdout.write(self.style.SUCCESS('2/8: Bodegas created (MP, PT, Insumos).'))

        # 3. Create Products (Hilo, Insumos)
        hilo_crudo, _ = Producto.objects.get_or_create(
            codigo='HIL-CRU-01',
            defaults={
                'descripcion': 'Hilo Crudo Poliéster 20/1',
                'tipo': 'hilo',
                'unidad_medida': 'kg',
                'stock_minimo': 100,
                'precio_base': Decimal('5.00')
            }
        )
        
        # Insumos para Empaque
        etiqueta_zebra, _ = Producto.objects.get_or_create(
            codigo='INS-ETQ-10x5',
            defaults={
                'descripcion': 'Etiqueta Zebra 100x50mm',
                'tipo': 'insumo',
                'unidad_medida': 'unidades',
                'stock_minimo': 1000,
                'precio_base': Decimal('0.02')
            }
        )
        funda_plastica, _ = Producto.objects.get_or_create(
            codigo='INS-FUND-01',
            defaults={
                'descripcion': 'Funda Plástica Industrial',
                'tipo': 'insumo',
                'unidad_medida': 'unidades',
                'stock_minimo': 500,
                'precio_base': Decimal('0.10')
            }
        )
        
        self.stdout.write(self.style.SUCCESS('3/8: Yarn and Insumo products created.'))

        # 4. Create Chemical Products
        quimico_rojo, _ = Producto.objects.get_or_create(
            codigo='QMC-ROJO-S',
            defaults={
                'descripcion': 'Colorante Rojo Solido',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 10,
                'precio_base': Decimal('20.00')
            }
        )
        quimico_fijador, _ = Producto.objects.get_or_create(
            codigo='QMC-FIJ-01',
            defaults={
                'descripcion': 'Fijador de Color Universal',
                'tipo': 'quimico',
                'unidad_medida': 'kg',
                'stock_minimo': 25,
                'precio_base': Decimal('15.00')
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
        
        # Stock de Insumos (en Bodega Insumos, assuming consumption happens from origin bodega of OP?
        # Logic says OP bodega is source. Usually OP is in Planta/MP. 
        # But insumos might be in Insumos.
        # For simplicity of the current logic which checks 'bodega_origen' of OP, 
        # let's put Insumos in Bodega MP as well for now, OR rely on a more complex lookup later.
        # Requirement: "Descuento de Insumos... (1 etiqueta, 1 funda)".
        # The code I wrote checks `bodega_origen` of the OP.
        # So I will seed Insumos in `bodega_mp` for now to ensure tests and basic flows work.
        StockBodega.objects.update_or_create(
            bodega=bodega_mp, producto=etiqueta_zebra, lote=None,
            defaults={'cantidad': Decimal('5000.00')}
        )
        StockBodega.objects.update_or_create(
            bodega=bodega_mp, producto=funda_plastica, lote=None,
            defaults={'cantidad': Decimal('2000.00')}
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
        group_names = [
            'operario', 'bodeguero', 'vendedor', 'jefe_area', 
            'jefe_planta', 'admin_sede', 'ejecutivo', 'admin_sistemas',
            'empaquetado' # Nuevo Rol
        ]

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        # Ensure groups exist
        for group_name in group_names:
            group, _ = Group.objects.get_or_create(name=group_name)
            
            # Assign permissions to Vendedor
            if group_name == 'vendedor':
                ct_cliente = ContentType.objects.get(app_label='gestion', model='cliente')
                permissions = Permission.objects.filter(content_type=ct_cliente, codename__in=['add_cliente', 'change_cliente', 'view_cliente'])
                group.permissions.set(permissions)
                
            # Assign permissions to Empaquetado?
            # They need to create LoteProduccion (add_loteproduccion) and view OrdenProduccion?
            if group_name == 'empaquetado':
                pass # Logic handled in ModelPermissions or Admin setup usually.


        for group_name in group_names:
            username = f'user_{group_name}'
            # Clean up old user if exists to ensure fresh start/update
            if CustomUser.objects.filter(username=username).exists():
                 user = CustomUser.objects.get(username=username)
                 # Update password if needed or leave it. 
                 # Let's just get it.
            else:
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
                
                # Assign specific Areas
                if group_name == 'empaquetado':
                    user.area = area_empaque
                elif group_name == 'jefe_area':
                    user.area = area_tejeduria
                else:
                    user.area = area

                # Assign all warehouses to test users so they can see data
                user.bodegas_asignadas.add(bodega_mp, bodega_pt, bodega_insumos)
                
                # Special Case: Empaquetado only assigned to PT? 
                # Prompt said: "System Admin to assign specific 'Final Product' warehouses to the packaging role."
                # Here we simulate that assignment.
                if group_name == 'empaquetado':
                     pass # Already added all above, fine for dev.
            
            user.groups.add(Group.objects.get(name=group_name))
            user.save()
            
        self.stdout.write(self.style.SUCCESS('8/8: Users created and assigned to groups.'))

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))