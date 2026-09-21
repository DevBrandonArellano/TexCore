from decimal import Decimal
from django.test import TestCase
from gestion.models import Producto
from gestion.tests.factories import SedeFactory, ProductoFactory


class ProductoColoranteTestCase(TestCase):
    """
    Pruebas unitarias para la inclusión de 'colorante' ('Colorantes') en el catálogo de productos.
    Convención de nombres: ISTQB CTFL v4.0
    test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
    """

    def setUp(self):
        self.sede = SedeFactory(nombre="Sede Central Tintorería")

    def test_producto_dado_tipo_colorante_cuando_se_crea_entonces_persiste_correctamente(self):
        """
        GIVEN: Un producto con tipo 'colorante'
        WHEN: Se instancia y guarda en base de datos
        THEN: Persiste con éxito y su tipo es 'colorante' con display 'Colorantes'
        """
        producto = Producto.objects.create(
            codigo="COL-AZUL-001",
            descripcion="Colorante Reactivo Azul Marino RGB",
            tipo="colorante",
            unidad_medida="kg",
            stock_minimo=Decimal("25.000"),
            precio_base=Decimal("45.000"),
            sede=self.sede,
        )

        self.assertIsNotNone(producto.id)
        self.assertEqual(producto.tipo, "colorante")
        self.assertEqual(producto.get_tipo_display(), "Colorantes")

        # Recuperar desde la BD
        recuperado = Producto.objects.get(codigo="COL-AZUL-001")
        self.assertEqual(recuperado.tipo, "colorante")
        self.assertEqual(recuperado.descripcion, "Colorante Reactivo Azul Marino RGB")

    def test_producto_dado_tipo_colorante_cuando_se_consulta_por_tipo_entonces_filtra_correctamente(self):
        """
        GIVEN: Múltiples productos de distintos tipos
        WHEN: Se filtra por tipo 'colorante'
        THEN: Solo retorna los productos de tipo colorante
        """
        ProductoFactory(codigo="HILO-001", tipo="hilo", sede=self.sede)
        ProductoFactory(codigo="TELA-001", tipo="tela", sede=self.sede)
        prod_colorante = ProductoFactory(codigo="COL-001", tipo="colorante", sede=self.sede)

        qs = Producto.objects.filter(tipo="colorante", sede=self.sede)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().codigo, prod_colorante.codigo)
