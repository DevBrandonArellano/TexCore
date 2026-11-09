"""
ReposicionService (inventory/services/reposicion_service.py): ramas que no cubría
gestion/tests/test_produccion_stock.py.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): detalle válido / sin guardar; calidad primera / segunda;
  plan por la corrida / por el detalle directo / sin plan; producto existente / inexistente.
- Análisis de valores límite (BVA): saldo pendiente 0; peso solicitado 0; código de OP de
  más de 100 caracteres; déficit 0; lo revertido nunca deja una cantidad negativa.
- Transición de estados (STT): plan cerrado → en_ejecucion al revertir; plan en ejecución no
  cambia al generar otra orden.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestion.models import DetallePlanProduccion, LoteProduccion, PlanProduccion, ProduccionSalida
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    CorridaProduccionFactory,
    CustomUserFactory,
    DetallePlanProduccionFactory,
    OperacionProduccionFactory,
    PlanProduccionFactory,
    ProductoFactory,
    SedeFactory,
)
from inventory.services.reposicion_service import ReposicionService


class GenerarOrdenDesdePlanRamasTest(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.plan = PlanProduccionFactory(sede=self.sede, estado="en_ejecucion")
        self.detalle = DetallePlanProduccionFactory(plan=self.plan, cantidad_planificada=Decimal("100.0000"))

    def test_generar_dado_detalle_sin_guardar_cuando_genera_entonces_validation_error(self):
        with self.assertRaisesMessage(ValidationError, "detalle de plan válido"):
            ReposicionService.generar_orden_desde_plan(DetallePlanProduccion(plan=self.plan))

    def test_generar_dado_saldo_pendiente_cero_cuando_genera_entonces_meta_cumplida(self):
        DetallePlanProduccion.objects.filter(pk=self.detalle.pk).update(cantidad_aceptada=Decimal("100.0000"))
        self.detalle.refresh_from_db()
        with self.assertRaisesMessage(ValidationError, "ya ha cumplido la meta"):
            ReposicionService.generar_orden_desde_plan(self.detalle)

    def test_generar_dado_peso_solicitado_cero_cuando_genera_entonces_validation_error(self):
        with self.assertRaisesMessage(ValidationError, "mayor a 0"):
            ReposicionService.generar_orden_desde_plan(self.detalle, peso_solicitado=Decimal("0"))

    def test_generar_dado_codigo_de_mas_de_100_caracteres_cuando_genera_entonces_lo_recorta_a_100(self):
        PlanProduccion.objects.filter(pk=self.plan.pk).update(codigo="P" * 50)
        producto = self.detalle.producto_objetivo
        producto.codigo = "C" * 60
        producto.save()
        self.detalle.refresh_from_db()

        op = ReposicionService.generar_orden_desde_plan(self.detalle)

        self.assertEqual(len(op.codigo), 100)

    def test_generar_dado_plan_en_ejecucion_y_detalle_en_proceso_cuando_genera_entonces_no_cambian_de_estado(self):
        DetallePlanProduccion.objects.filter(pk=self.detalle.pk).update(estado="en_proceso")
        self.detalle.refresh_from_db()

        ReposicionService.generar_orden_desde_plan(self.detalle)

        self.plan.refresh_from_db()
        self.detalle.refresh_from_db()
        self.assertEqual((self.plan.estado, self.detalle.estado), ("en_ejecucion", "en_proceso"))


class AvancePlanRamasTest(TestCase):
    """Avance y reversión del plan a partir de las salidas de una operación MES."""

    def setUp(self):
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.bodega = BodegaFactory(sede=self.sede)
        self.plan = PlanProduccionFactory(sede=self.sede, estado="aprobado")
        self.detalle = DetallePlanProduccionFactory(plan=self.plan, cantidad_planificada=Decimal("100.0000"))
        self.producto = self.detalle.producto_objetivo

    def _operacion(self, cantidad, calidad, producto=None, **corrida):
        corrida = CorridaProduccionFactory(sede=self.sede, area=self.area, **corrida)
        operacion = OperacionProduccionFactory(corrida=corrida)
        ahora = timezone.now()
        lote = LoteProduccion.objects.create(
            codigo_lote=f"LOT-AV-{operacion.id}",
            producto=producto or self.producto,
            peso_neto_producido=Decimal(cantidad),
            turno="Mañana",
            hora_inicio=ahora,
            hora_final=ahora,
        )
        ProduccionSalida.objects.create(
            operacion=operacion,
            lote_generado=lote,
            producto=producto or self.producto,
            bodega_destino=self.bodega,
            cantidad_neta=Decimal(cantidad),
            clasificacion_calidad=calidad,
        )
        return operacion

    def _detalle(self):
        self.detalle.refresh_from_db()
        return self.detalle

    def test_avance_dado_operacion_sin_guardar_cuando_actualiza_entonces_no_hace_nada(self):
        self.assertIsNone(ReposicionService.actualizar_avance_plan(None))
        self.assertIsNone(ReposicionService.revertir_avance_plan(None))

    def test_avance_dado_salida_de_segunda_por_el_plan_cuando_actualiza_entonces_suma_a_segunda(self):
        operacion = self._operacion("30.000", "segunda", plan_produccion=self.plan)

        ReposicionService.actualizar_avance_plan(operacion)

        detalle = self._detalle()
        self.assertEqual(
            (detalle.cantidad_ejecutada, detalle.cantidad_segunda, detalle.cantidad_aceptada),
            (Decimal("30.0000"), Decimal("30.0000"), Decimal("0.0000")),
        )
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.estado, "en_ejecucion")

    def test_avance_dado_producto_que_el_plan_no_tiene_cuando_actualiza_entonces_lo_ignora(self):
        operacion = self._operacion(
            "30.000", "primera", producto=ProductoFactory(sede=self.sede), plan_produccion=self.plan
        )

        ReposicionService.actualizar_avance_plan(operacion)

        self.assertEqual(self._detalle().cantidad_ejecutada, Decimal("0.0000"))

    def test_revertir_dado_segunda_por_el_plan_cuando_revierte_entonces_descuenta_sin_quedar_negativo(self):
        DetallePlanProduccion.objects.filter(pk=self.detalle.pk).update(
            cantidad_ejecutada=Decimal("10.0000"), cantidad_segunda=Decimal("10.0000")
        )
        operacion = self._operacion("30.000", "segunda", plan_produccion=self.plan)

        ReposicionService.revertir_avance_plan(operacion)

        detalle = self._detalle()
        self.assertEqual((detalle.cantidad_ejecutada, detalle.cantidad_segunda), (Decimal("0.0000"), Decimal("0.0000")))

    def test_revertir_dado_plan_cerrado_cuando_revierte_entonces_vuelve_a_en_ejecucion(self):
        PlanProduccion.objects.filter(pk=self.plan.pk).update(estado="cerrado")
        DetallePlanProduccion.objects.filter(pk=self.detalle.pk).update(
            cantidad_ejecutada=Decimal("100.0000"), cantidad_aceptada=Decimal("100.0000")
        )
        operacion = self._operacion("40.000", "primera", detalle_plan=self.detalle)

        ReposicionService.revertir_avance_plan(operacion)

        self.plan.refresh_from_db()
        self.assertEqual(self.plan.estado, "en_ejecucion")
        self.assertEqual(self._detalle().cantidad_aceptada, Decimal("60.0000"))

    def test_revertir_dado_producto_que_el_plan_no_tiene_cuando_revierte_entonces_lo_ignora(self):
        DetallePlanProduccion.objects.filter(pk=self.detalle.pk).update(cantidad_ejecutada=Decimal("10.0000"))
        operacion = self._operacion(
            "5.000", "primera", producto=ProductoFactory(sede=self.sede), plan_produccion=self.plan
        )

        ReposicionService.revertir_avance_plan(operacion)

        self.assertEqual(self._detalle().cantidad_ejecutada, Decimal("10.0000"))


class NecesidadesYPlanDesdeAlertasTest(TestCase):
    def test_necesidades_dado_sin_sede_cuando_analiza_entonces_junta_las_sedes_activas_en_orden(self):
        sede_b, sede_a = SedeFactory(nombre="B Sede", status="activo"), SedeFactory(nombre="A Sede", status="activo")
        SedeFactory(nombre="C Inactiva", status="inactivo")
        with patch("inventory.services.mrp.necesidades_produccion", side_effect=lambda sede: [sede]) as necesidades:
            resultado = ReposicionService.analizar_necesidades_reposicion()
        self.assertEqual(resultado, [sede_a.id, sede_b.id])
        self.assertEqual(necesidades.call_count, 2)

    def test_crear_plan_dado_lista_vacia_cuando_crea_entonces_validation_error(self):
        with self.assertRaisesMessage(ValidationError, "No se proporcionaron productos"):
            ReposicionService.crear_plan_desde_alertas(sede=SedeFactory(), productos_deficit=[])

    def test_crear_plan_dado_deficit_cero_cuando_crea_entonces_omite_ese_renglon(self):
        sede = SedeFactory()
        con_deficit, sin_deficit = ProductoFactory(sede=sede), ProductoFactory(sede=sede)

        plan = ReposicionService.crear_plan_desde_alertas(
            sede=sede,
            productos_deficit=[
                {"producto_id": con_deficit.id, "deficit": "12.5"},
                {"producto_id": sin_deficit.id, "deficit": "0"},
            ],
            supervisor=CustomUserFactory(sede=sede),
            fecha_inicio=date(2026, 11, 1),
        )

        self.assertEqual(list(plan.detalles.values_list("producto_objetivo_id", flat=True)), [con_deficit.id])
        self.assertEqual(plan.fecha_fin, timezone.localdate() + timedelta(days=7))

    def test_crear_plan_dado_producto_inexistente_cuando_crea_entonces_validation_error_y_sin_plan(self):
        """Antes lanzaba Producto.DoesNotExist y la vista respondía 500 «Error interno»."""
        sede = SedeFactory()
        with self.assertRaisesMessage(ValidationError, "999999"):
            ReposicionService.crear_plan_desde_alertas(
                sede=sede, productos_deficit=[{"producto_id": 999999, "deficit": "5"}]
            )
        self.assertFalse(PlanProduccion.objects.filter(sede=sede).exists())
