from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from gestion.models import (
    Sede, Area, CustomUser, Producto, Batch, Inventory, ProcessStep,
    MaterialMovement, Chemical, FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido
)

class Command(BaseCommand):
    help = 'Sets up initial groups and permissions for the application.'

    def handle(self, *args, **options):
        self.stdout.write('Setting up groups and permissions...')

        # Define roles and their associated permissions
        # For simplicity, we'll define permissions for common models.
        # You can expand this list as needed.
        permissions_map = {
            'operario': {
                'models': [Producto, Batch, Inventory, MaterialMovement, OrdenProduccion, LoteProduccion],
                'perms': ['add', 'change', 'view'], # Operarios can add, change, view their related data
            },
            'jefe_area': {
                'models': [Sede, Area, Producto, Batch, Inventory, MaterialMovement, OrdenProduccion, LoteProduccion, CustomUser],
                'perms': ['add', 'change', 'view'],
            },
            'jefe_planta': {
                'models': [Sede, Area, Producto, Batch, Inventory, MaterialMovement, Chemical, FormulaColor, DetalleFormula, OrdenProduccion, LoteProduccion, CustomUser],
                'perms': ['add', 'change', 'view'],
            },
            'admin_sede': {
                'models': [Sede, Area, CustomUser, Producto, Batch, Inventory, MaterialMovement, OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Cliente],
                'perms': ['add', 'change', 'view', 'delete'], # Admins can do everything
            },
            'ejecutivo': {
                'models': [Producto, Cliente, PedidoVenta, DetallePedido, OrdenProduccion],
                'perms': ['add', 'change', 'view'],
            },
            'admin_sistemas': {
                'models': [Sede, Area, CustomUser, Producto, Batch, Inventory, ProcessStep, MaterialMovement, Chemical, FormulaColor, DetalleFormula, Cliente, OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido],
                'perms': ['add', 'change', 'view', 'delete'], # System admins have full control
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
