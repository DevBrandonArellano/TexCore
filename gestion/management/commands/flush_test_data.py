"""
Elimina toda la población de datos creada para pruebas (stress_test_data y seed_data).
Deja la base limpia para recibir nuevas indicaciones.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from inventory.models import (
    MovimientoInventario,
    AuditoriaMovimiento,
    StockBodega,
    HistorialDespacho,
    DetalleHistorialDespacho,
    DetalleHistorialDespachoPedido,
)
from gestion.models import (
    Bodega,
    Sede,
    LoteProduccion,
    OrdenProduccion,
    DetalleFormula,
    FormulaColor,
    Producto,
    Proveedor,
    CustomUser,
    Maquina,
    PagoCliente,
    PedidoVenta,
    Cliente,
)


class Command(BaseCommand):
    help = 'Elimina toda la población de datos de prueba (stress_test_data + seed_data) para empezar de cero.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar la eliminación (requerido para ejecutar)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options.get('confirm'):
            self.stdout.write(
                self.style.WARNING(
                    'Para eliminar los datos de prueba, ejecuta con --confirm:\n'
                    '  python manage.py flush_test_data --confirm'
                )
            )
            return

        self.stdout.write('Eliminando datos de prueba...')

        # 0. Datos de ventas (pedidos incluye detalles por CASCADE)
        n = PagoCliente.objects.all().delete()[0]
        self.stdout.write(f'  PagoCliente: {n} eliminados')
        n = PedidoVenta.objects.all().delete()[0]
        self.stdout.write(f'  PedidoVenta: {n} eliminados')
        n = Cliente.objects.all().delete()[0]
        self.stdout.write(f'  Cliente: {n} eliminados')

        # 1. Auditoría de movimientos
        n = AuditoriaMovimiento.objects.all().delete()[0]
        self.stdout.write(f'  AuditoriaMovimiento: {n} eliminados')

        # 2. Movimientos de inventario
        n = MovimientoInventario.objects.all().delete()[0]
        self.stdout.write(f'  MovimientoInventario: {n} eliminados')

        # 3. Historial de despacho
        DetalleHistorialDespacho.objects.all().delete()
        DetalleHistorialDespachoPedido.objects.all().delete()
        n = HistorialDespacho.objects.all().delete()[0]
        self.stdout.write(f'  HistorialDespacho: {n} eliminados')

        # 4. Stock
        n = StockBodega.objects.all().delete()[0]
        self.stdout.write(f'  StockBodega: {n} eliminados')

        # 5. Lotes de producción (stress test)
        n = LoteProduccion.objects.filter(
            orden_produccion__codigo__startswith='OP-STR'
        ).delete()[0]
        self.stdout.write(f'  LoteProduccion (stress): {n} eliminados')

        # 6. Órdenes de producción (stress test)
        n = OrdenProduccion.objects.filter(codigo__startswith='OP-STR').delete()[0]
        self.stdout.write(f'  OrdenProduccion (stress): {n} eliminados')

        # 7. Detalles de fórmula (stress test) - DetalleFormula usa fase->formula
        n = DetalleFormula.objects.filter(
            fase__formula__codigo__startswith='FORM-STR'
        ).delete()[0]
        self.stdout.write(f'  DetalleFormula (stress): {n} eliminados')

        # 8. Fórmulas (stress test)
        n = FormulaColor.objects.filter(codigo__startswith='FORM-STR').delete()[0]
        self.stdout.write(f'  FormulaColor (stress): {n} eliminados')

        # 9. Órdenes y fórmulas de seed_data (antes de borrar productos)
        n = OrdenProduccion.objects.filter(codigo='OP-2025-001').delete()[0]
        self.stdout.write(f'  OrdenProduccion (seed): {n} eliminados')
        DetalleFormula.objects.filter(fase__formula__codigo='FORM-ROJO-01').delete()
        n = FormulaColor.objects.filter(codigo='FORM-ROJO-01').delete()[0]
        self.stdout.write(f'  FormulaColor (seed): {n} eliminados')

        # 10. Productos (stress + seed + ventas)
        n = Producto.objects.filter(
            Q(codigo__startswith='HIL-STR-') |
            Q(codigo__startswith='QMC-STR-') |
            Q(codigo__startswith='INS-STR-') |
            Q(codigo__startswith='VENT-STR-') |
            Q(codigo='HIL-CRU-01') |
            Q(codigo='INS-ETQ-10x5') |
            Q(codigo='INS-FUND-01') |
            Q(codigo='QMC-ROJO-S') |
            Q(codigo='QMC-FIJ-01')
        ).delete()[0]
        self.stdout.write(f'  Producto (stress + seed): {n} eliminados')

        # 11. Proveedores (stress test)
        n = Proveedor.objects.filter(nombre__startswith='Proveedor Stress').delete()[0]
        self.stdout.write(f'  Proveedor (stress): {n} eliminados')

        # 12. Usuarios bodegueros (stress test)
        users = CustomUser.objects.filter(username__startswith='stress_bodeguero_')
        for u in users:
            u.groups.clear()
            u.bodegas_asignadas.clear()
        n = users.delete()[0]
        self.stdout.write(f'  CustomUser (stress_bodeguero): {n} eliminados')

        # 13. Máquina (stress test)
        n = Maquina.objects.filter(nombre='Máquina Stress 01').delete()[0]
        self.stdout.write(f'  Maquina (stress): {n} eliminados')

        # 14. Bodegas extra (stress test) - 9 bodegas de sedes Principal 2, Calderon, Cumbaya
        bodega_nombres = [
            'Bodega MP Principal 2', 'Bodega PT Principal 2', 'Bodega Insumos Principal 2',
            'Bodega MP Calderon', 'Bodega PT Calderon', 'Bodega Insumos Calderon',
            'Bodega MP Cumbaya', 'Bodega PT Cumbaya', 'Bodega Insumos Cumbaya',
            # Legacy (por si quedaron de versión anterior)
            'Planta Norte', 'Planta Sur', 'Bodega Distribución',
            'MP Sede Norte', 'PT Sede Norte',
        ]
        n = Bodega.objects.filter(nombre__in=bodega_nombres).delete()[0]
        self.stdout.write(f'  Bodega (stress): {n} eliminadas')

        # 15. Sedes extra (stress test)
        sedes_eliminar = ['Sede Principal 2', 'Sede Calderon', 'Sede Cumbaya', 'Sede Norte']
        n = Sede.objects.filter(nombre__in=sedes_eliminar).delete()[0]
        self.stdout.write(f'  Sede (stress): {n} eliminadas')

        self.stdout.write(self.style.SUCCESS('\n✓ Datos de prueba eliminados. Base lista para nuevas indicaciones.'))
