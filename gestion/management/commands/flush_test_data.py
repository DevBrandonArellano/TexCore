"""
Elimina toda la población de datos creada para pruebas (stress_test_data y seed_data).
Deja la base limpia para recibir nuevas indicaciones.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import (
    MovimientoInventario,
    AuditoriaMovimiento,
    StockBodega,
    HistorialDespacho,
    DetalleHistorialDespacho,
    DetalleHistorialDespachoPedido,
    RequerimientoMaterial,
    OrdenCompraSugerida,
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
    MateriaPrimaLote,
    ConsumoMateriaPrima,
    DescargaQuimicoOP,
    ComponenteMezclaOP,
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

        # 0. Historial de despacho (eliminar relaciones protected con PedidoVenta)
        DetalleHistorialDespacho.objects.all().delete()
        DetalleHistorialDespachoPedido.objects.all().delete()
        HistorialDespacho.objects.all().delete()

        # 1. Datos de ventas (pedidos incluye detalles por CASCADE)
        n = PagoCliente.objects.all().delete()[0]
        self.stdout.write(f'  PagoCliente: {n} eliminados')
        n = PedidoVenta.objects.all().delete()[0]
        self.stdout.write(f'  PedidoVenta: {n} eliminados')
        n = Cliente.objects.all().delete()[0]
        self.stdout.write(f'  Cliente: {n} eliminados')

        # 2. Auditoría de movimientos
        n = AuditoriaMovimiento.objects.all().delete()[0]
        self.stdout.write(f'  AuditoriaMovimiento: {n} eliminados')

        # 3. Movimientos de inventario
        n = MovimientoInventario.objects.all().delete()[0]
        self.stdout.write(f'  MovimientoInventario: {n} eliminados')

        # 4. Stock, MRP y Materia Prima
        RequerimientoMaterial.objects.all().delete()
        OrdenCompraSugerida.objects.all().delete()
        DescargaQuimicoOP.objects.all().delete()
        ComponenteMezclaOP.objects.all().delete()
        ConsumoMateriaPrima.objects.all().delete()
        MateriaPrimaLote.objects.all().delete()
        n = StockBodega.objects.all().delete()[0]
        self.stdout.write(f'  StockBodega: {n} eliminados')

        # 5. Lotes de producción (stress + seed)
        n = LoteProduccion.objects.all().delete()[0]
        self.stdout.write(f'  LoteProduccion: {n} eliminados')

        # 6. Órdenes de producción (stress + seed)
        n = OrdenProduccion.objects.all().delete()[0]
        self.stdout.write(f'  OrdenProduccion: {n} eliminados')

        # 7. Detalles de fórmula (stress test) - DetalleFormula usa fase->formula
        n = DetalleFormula.objects.filter(
            fase__formula__codigo__startswith='FORM-STR'
        ).delete()[0]
        self.stdout.write(f'  DetalleFormula (stress): {n} eliminados')

        # 8. Fórmulas (stress test)
        n = FormulaColor.objects.filter(codigo__startswith='FORM-STR').delete()[0]
        self.stdout.write(f'  FormulaColor (stress): {n} eliminados')

        # 9. Fórmulas de seed_data (antes de borrar productos)
        DetalleFormula.objects.filter(fase__formula__codigo='FORM-ROJO-01').delete()
        n = FormulaColor.objects.filter(codigo='FORM-ROJO-01').delete()[0]
        self.stdout.write(f'  FormulaColor (seed): {n} eliminados')

        # 10. Productos (stress + seed + ventas)
        n = Producto.objects.all().delete()[0]
        self.stdout.write(f'  Producto (stress + seed): {n} eliminados')

        # 11. Proveedores (stress test + seed)
        n = Proveedor.objects.all().delete()[0]
        self.stdout.write(f'  Proveedor (stress + seed): {n} eliminados')

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
