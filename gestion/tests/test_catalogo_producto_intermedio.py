from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from gestion.models import Producto
from gestion.tests.factories import SedeFactory, ProductoFactory


class ProductoIntermedioTestCase(TestCase):
    """
    Pruebas unitarias para la inclusión de 'producto_intermedio' en el catálogo de productos.
    Convención de nombres: ISTQB CTFL v4.0
    test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
    """

    def setUp(self):
        self.sede = SedeFactory(nombre="Sede Central Test")

    def test_producto_dado_tipo_intermedio_cuando_se_crea_entonces_persiste_correctamente(self):
        """
        GIVEN: Un producto con tipo 'producto_intermedio'
        WHEN: Se instancia y guarda en base de datos
        THEN: Persiste con éxito y su tipo es 'producto_intermedio'
        """
        producto = Producto.objects.create(
            codigo="INT-MECHA-001",
            descripcion="Mecha de Algodón Peinado 100%",
            tipo="producto_intermedio",
            unidad_medida="kg",
            stock_minimo=Decimal("50.000"),
            precio_base=Decimal("3.500"),
            sede=self.sede,
        )

        self.assertIsNotNone(producto.id)
        self.assertEqual(producto.tipo, "producto_intermedio")
        self.assertEqual(producto.get_tipo_display(), "Producto Intermedio")

        # Recuperar desde la BD
        recuperado = Producto.objects.get(codigo="INT-MECHA-001")
        self.assertEqual(recuperado.tipo, "producto_intermedio")
        self.assertEqual(recuperado.descripcion, "Mecha de Algodón Peinado 100%")

    def test_producto_dado_tipo_intermedio_cuando_se_consulta_por_tipo_entonces_filtra_correctamente(self):
        """
        GIVEN: Múltiples productos de distintos tipos
        WHEN: Se filtra por tipo 'producto_intermedio'
        THEN: Solo retorna los productos de tipo intermedio
        """
        ProductoFactory(codigo="HILO-001", tipo="hilo", sede=self.sede)
        ProductoFactory(codigo="TELA-001", tipo="tela", sede=self.sede)
        prod_intermedio = ProductoFactory(codigo="INT-001", tipo="producto_intermedio", sede=self.sede)

        qs = Producto.objects.filter(tipo="producto_intermedio", sede=self.sede)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().codigo, prod_intermedio.codigo)
