from django.test import TestCase
from decimal import Decimal
from gestion.models import Bodega, Producto, Sede, PedidoVenta, DetallePedido, FormulaColor, FaseReceta, DetalleFormula
from inventory.models import RequerimientoMaterial, OrdenCompraSugerida, StockBodega
from inventory.services.mrp_engine import MRPEngine
from django.contrib.auth import get_user_model

User = get_user_model()

class MRPTest(TestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Interfibra")
        self.bodega = Bodega.objects.create(nombre="Bodega MP", sede=self.sede)
        
        # Productos
        self.producto_pt = Producto.objects.create(
            codigo="HILO-1", descripcion="Hilo Algodon", tipo="hilo", unidad_medida="kg"
        )
        self.producto_quimico = Producto.objects.create(
            codigo="QUIM-1", descripcion="Colorante Azul", tipo="quimico", unidad_medida="kg"
        )
        
        # Fórmula: 1 baño = 10 gr_l de Colorante Azul
        self.formula = FormulaColor.objects.create(
            codigo="AZUL-01", nombre_color="Azul Oscuro", tipo_sustrato="algodon", estado="aprobada"
        )
        self.fase = FaseReceta.objects.create(
            formula=self.formula, nombre="tintura", orden=1
        )
        self.detalle_formula = DetalleFormula.objects.create(
            fase=self.fase, producto=self.producto_quimico, concentracion_gr_l=Decimal('10.000'), tipo_calculo='gr_l'
        )
        
        # Pedido Venta
        # Piden 300 conos. 300 / 225 = 1.333 baños
        self.pedido = PedidoVenta.objects.create(
            sede=self.sede, estado='pendiente', guia_remision='123'
        )
        self.detalle_pedido = DetallePedido.objects.create(
            pedido_venta=self.pedido, producto=self.producto_pt, cantidad=300, piezas=1, peso=Decimal('500'), precio_unitario=Decimal('10')
        )
        
        # Stock: Solo tenemos 5 en stock de Colorante Azul
        self.stock = StockBodega.objects.create(
            bodega=self.bodega, producto=self.producto_quimico, cantidad=Decimal('5.000')
        )

    def test_mrp_calculation_pedidos(self):
        engine = MRPEngine()
        
        # Modificar las conversiones en test para coincidir con la regla de 1.333 baños
        # (engine ya tiene CONVERSION_BANOS_CONOS = 225)
        engine.ejecutar_mrp()
        
        # 1. Verificar Requerimiento (300 / 225 = 1.3333 baños * 10 = 13.333)
        req = RequerimientoMaterial.objects.filter(producto_requerido=self.producto_quimico).first()
        self.assertIsNotNone(req)
        # 300 / 225 * 10 = 13.333333333...
        expected_req = Decimal('300') / Decimal('225') * Decimal('10')
        self.assertAlmostEqual(req.cantidad_necesaria, expected_req, places=3)
        
        # 2. Verificar Orden Compra Sugerida (13.333 - 5.00 = 8.3333)
        ocs = OrdenCompraSugerida.objects.filter(producto=self.producto_quimico).first()
        self.assertIsNotNone(ocs)
        expected_ocs = expected_req - Decimal('5.000')
        self.assertAlmostEqual(ocs.cantidad_sugerida, expected_ocs, places=3)
        self.assertEqual(ocs.estado, 'PENDIENTE')
