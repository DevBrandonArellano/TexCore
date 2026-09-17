from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from gestion.models import LoteProduccion, MateriaPrimaLote
from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory,
    OrdenProduccionFactory, ProveedorFactory
)


class LoteUniversalTestCase(TestCase):
    """
    Pruebas unitarias para la unificación de lote con producto y materia prima directa.
    Estándar ISTQB CTFL v4.0:
    test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
    """

    def setUp(self):
        self.sede = SedeFactory(nombre="Sede Lote Universal Test")
        self.bodega = BodegaFactory(sede=self.sede)
        self.operario = CustomUserFactory(sede=self.sede)
        self.producto_hilo = ProductoFactory(codigo="HIL-2026", tipo="hilo", sede=self.sede)
        self.producto_fibra = ProductoFactory(codigo="FIB-2026", tipo="materia_prima", sede=self.sede)
        self.proveedor = ProveedorFactory(sede=self.sede, nombre="Proveedor Fibras SA")

    def test_lote_dado_orden_produccion_cuando_se_guarda_sin_producto_entonces_deriva_producto_de_la_orden(self):
        """
        GIVEN: Una orden de producción con producto_salida asignado
        WHEN: Se crea un LoteProduccion sin pasar 'producto' explícitamente
        THEN: clean() autoderiva el campo 'producto' desde producto_salida de la OP
        """
        op = OrdenProduccionFactory(
            sede=self.sede,
            codigo="OP-AUTO-DERIV",
            producto_entrada=self.producto_fibra,
            producto_salida=self.producto_hilo,
            peso_neto_requerido=Decimal("500.00"),
        )

        ahora = timezone.now()
        lote = LoteProduccion.objects.create(
            orden_produccion=op,
            codigo_lote="LOT-DERIV-01",
            peso_neto_producido=Decimal("100.000"),
            operario=self.operario,
            turno="Mañana",
            hora_inicio=ahora,
            hora_final=ahora,
        )

        self.assertIsNotNone(lote.producto)
        self.assertEqual(lote.producto.id, self.producto_hilo.id)
        self.assertEqual(lote.producto.codigo, "HIL-2026")

    def test_lote_dado_sin_orden_cuando_se_especifica_producto_entonces_persiste_correctamente(self):
        """
        GIVEN: Un lote independiente sin orden de producción (escenario Producción Continua)
        WHEN: Se crea especificando el 'producto' directamente
        THEN: Persiste con orden_produccion=None y conserva su FK al producto
        """
        ahora = timezone.now()
        lote_continuo = LoteProduccion.objects.create(
            orden_produccion=None,
            producto=self.producto_hilo,
            codigo_lote="LOT-CONT-99",
            peso_neto_producido=Decimal("150.000"),
            operario=self.operario,
            turno="Noche",
            hora_inicio=ahora,
            hora_final=ahora,
        )

        self.assertIsNone(lote_continuo.orden_produccion)
        self.assertEqual(lote_continuo.producto.id, self.producto_hilo.id)
        self.assertEqual(lote_continuo.codigo_lote, "LOT-CONT-99")

    def test_lote_dado_materia_prima_proveedor_cuando_se_asocia_entonces_conserva_relacion_directa(self):
        """
        GIVEN: Un lote de proveedor registrado en MateriaPrimaLote
        WHEN: Se vincula directamente a un LoteProduccion
        THEN: La relación materia_prima_lote queda registrada y accesible bidireccionalmente
        """
        ahora = timezone.now()
        mp_lote = MateriaPrimaLote.objects.create(
            producto=self.producto_fibra,
            proveedor=self.proveedor,
            lote_proveedor="LOT-PROV-888",
            fecha_recepcion=ahora.date(),
            cantidad_kg=Decimal("1000.000"),
            costo_unitario=Decimal("2.500"),
            bodega_recepcion=self.bodega,
            sede=self.sede,
        )

        lote_planta = LoteProduccion.objects.create(
            orden_produccion=None,
            producto=self.producto_fibra,
            materia_prima_lote=mp_lote,
            codigo_lote="LOT-PROV-888-REC",
            peso_neto_producido=Decimal("1000.000"),
            operario=self.operario,
            turno="N/A",
            hora_inicio=ahora,
            hora_final=ahora,
        )

        self.assertEqual(lote_planta.materia_prima_lote.id, mp_lote.id)
        self.assertEqual(mp_lote.lotes_derivados.first().id, lote_planta.id)
