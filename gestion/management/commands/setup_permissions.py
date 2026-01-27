from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from gestion.models import (
    Sede, Area, CustomUser, Producto, Batch, ProcessStep, Bodega,
    FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido
)
from inventory.models import StockBodega, MovimientoInventario

class Command(BaseCommand):
    help = 'Sets up initial groups and permissions for the application.'

    def handle(self, *args, **options):
        self.stdout.write('Setting up groups and permissions...')

        # Define roles and their associated permissions for the current models
        permissions_map = {
            'operario': {
                'models': [LoteProduccion, MovimientoInventario],
                'perms': ['add', 'change', 'view'],
            },
            'bodeguero': {
                'models': [StockBodega, MovimientoInventario, Producto, Bodega, LoteProduccion],
                'perms': ['add', 'change', 'view'],
            },
            'jefe_area': {
                'models': [Area, Producto, CustomUser, StockBodega, MovimientoInventario, OrdenProduccion, LoteProduccion],
                'perms': ['add', 'change', 'view'],
            },
            'jefe_planta': {
                'models': [Area, Producto, Bodega, FormulaColor, DetalleFormula, OrdenProduccion, LoteProduccion, StockBodega, MovimientoInventario],
                'perms': ['add', 'change', 'view', 'delete'],
            },
            'admin_sede': {
                'models': [Sede, Area, CustomUser, Producto, Bodega, OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Cliente, StockBodega, MovimientoInventario],
                'perms': ['add', 'change', 'view', 'delete'],
            },
            'ejecutivo': {
                'models': [Producto, Cliente, PedidoVenta, DetallePedido, OrdenProduccion, StockBodega],
                'perms': ['view'],
            },
            'vendedor': {
                'models': [Cliente, PedidoVenta, DetallePedido, Producto],
                'perms': ['add', 'change', 'view'],
            },
            'admin_sistemas': {
                'models': [Sede, Area, CustomUser, Producto, Batch, ProcessStep, Bodega, FormulaColor, DetalleFormula, Cliente, OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, StockBodega, MovimientoInventario],
                'perms': ['add', 'change', 'view', 'delete'],
            },
        }


        for role_name, config in permissions_map.items():
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {role_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Group {role_name} already exists.'))

            # Clear existing permissions for the group to avoid duplicates on re-run
            group.permissions.clear()

            for model_class in config['models']:
                content_type = ContentType.objects.get_for_model(model_class)
                for perm_type in config['perms']:
                    codename = f'{perm_type}_{model_class._meta.model_name}'
                    try:
                        permission = Permission.objects.get(content_type=content_type, codename=codename)
                        group.permissions.add(permission)
                        self.stdout.write(self.style.SUCCESS(f'  Added permission {codename} to {role_name}'))
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'  Permission {codename} for {model_class._meta.model_name} does not exist. Skipping.'))

        self.stdout.write(self.style.SUCCESS('Groups and permissions setup completed!'))
