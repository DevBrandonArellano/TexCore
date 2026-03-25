from django.test import TestCase
from decimal import Decimal
from gestion.models import Bodega, Producto, LoteProduccion, Sede, Proveedor, Cliente, AuditLog
from gestion.middleware import _local
from inventory.models import StockBodega, MovimientoInventario, RequerimientoMaterial, OrdenCompraSugerida
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditAndMRPTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testadmin', password='password')
        _local.user = self.user
        _local.ip_address = '127.0.0.1'

        self.sede = Sede.objects.create(nombre="Interfibra")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)
        
        self.producto_mp = Producto.objects.create(
            codigo="MP-01", descripcion="Algodon Crudo", tipo="insumo", unidad_medida="kg"
        )
        self.producto_pt = Producto.objects.create(
            codigo="PT-01", descripcion="Tela Algodon", tipo="tela", unidad_medida="kg"
        )
        
        self.cliente = Cliente(
            ruc_cedula="123456789", nombre_razon_social="Cliente A", limite_credito=Decimal('1000.00')
        )
        self.cliente._justificacion_auditoria = "Alta inicial"
        self.cliente.save()

    def test_audit_log_creation(self):
        # Update limit without justification shouldn't throw error if we don't handle it in view, 
        # wait, the logic says if not is_new and requiere_just_aud and not hasattr(): raise error
        
        # We try to update
        self.cliente.limite_credito = Decimal('2000.00')
        with self.assertRaises(ValidationError):
            self.cliente.save()
            
        # Give justification
        self.cliente._justificacion_auditoria = "Aumento de linea"
        self.cliente.save()
        
        # Check audit log
        log = AuditLog.objects.filter(accion='UPDATE').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.justificacion, "Aumento de linea")
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.usuario, self.user)
        self.assertIn('limite_credito', log.valor_nuevo)
        self.assertEqual(log.valor_nuevo['limite_credito'], '2000.00')

    def tearDown(self):
        if hasattr(_local, 'user'):
            del _local.user
        if hasattr(_local, 'ip_address'):
            del _local.ip_address
