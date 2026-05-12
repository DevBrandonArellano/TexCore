"""
Tests de Integración — EmpaqueService
=====================================
Cobertura:
    1. Fallback de configuración (Sede → Producto → Global → Defaults)
    2. La suma de pesos de los bultos coincide con el total del lote
    3. No se permite generar bultos duplicados (idempotencia con error)
    4. Excepciones personalizadas se levantan correctamente
    5. Lote sin peso válido es rechazado
    6. Auditoría: cada bulto creado deja rastro en AuditLog

Marco: Django TestCase (DB real, transacciones revertidas por test).
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from gestion.models import (
    AuditLog,
    BultoEmpaque,
    ConfiguracionEmpaque,
    LoteProduccion,
    OrdenProduccion,
)
from gestion.services.empaque_service import (
    BultosYaGenerados,
    EmpaqueService,
    LoteSinPesoValido,
)
from gestion.tests.factories import (
    BodegaFactory,
    CustomUserFactory,
    MaquinaFactory,
    OrdenProduccionFactory,
    ProductoFactory,
    SedeFactory,
)


# ---------------------------------------------------------------------------
# Helper de construcción de Lote (no hay LoteFactory aún en factories.py)
# ---------------------------------------------------------------------------

def _crear_lote(*, peso=Decimal("100.000"), sede=None, producto=None, codigo="L-001"):
    """Construye un OrdenProduccion + LoteProduccion mínimos para tests."""
    sede = sede or SedeFactory()
    producto = producto or ProductoFactory(sede=sede)
    bodega = BodegaFactory(sede=sede)
    orden = OrdenProduccionFactory(
        sede=sede, producto=producto, bodega=bodega,
        peso_neto_requerido=peso,
    )
    operario = CustomUserFactory(sede=sede)
    maquina = MaquinaFactory()
    ahora = timezone.now()
    lote = LoteProduccion.objects.create(
        orden_produccion=orden,
        codigo_lote=codigo,
        peso_neto_producido=peso,
        operario=operario,
        maquina=maquina,
        turno="diurno",
        hora_inicio=ahora - timedelta(hours=1),
        hora_final=ahora,
        peso_bruto=peso + Decimal("2.000"),
        tara=Decimal("2.000"),
    )
    return lote


# ---------------------------------------------------------------------------
# 1. Fallback de configuración
# ---------------------------------------------------------------------------

class FallbackConfiguracionTest(TestCase):
    """Valida la jerarquía de resolución de ConfiguracionEmpaque."""

    def test_default_15x15_sin_configuracion(self):
        lote = _crear_lote()
        service = EmpaqueService()
        config = service._resolver_config(lote)
        self.assertEqual(config.bultos_por_lote, 15)
        self.assertEqual(config.unidades_por_bulto, 15)
        self.assertEqual(config.tara_bulto, Decimal("0"))

    def test_global_supera_defaults(self):
        ConfiguracionEmpaque.objects.create(
            producto=None, sede=None,
            bultos_por_lote=10, unidades_por_bulto=12, tara_bulto=Decimal("0.500"),
        )
        lote = _crear_lote()
        config = EmpaqueService()._resolver_config(lote)
        self.assertEqual(config.bultos_por_lote, 10)
        self.assertEqual(config.unidades_por_bulto, 12)
        self.assertEqual(config.tara_bulto, Decimal("0.500"))

    def test_solo_sede_supera_global(self):
        sede = SedeFactory()
        ConfiguracionEmpaque.objects.create(
            producto=None, sede=None, bultos_por_lote=10, unidades_por_bulto=10,
        )
        ConfiguracionEmpaque.objects.create(
            producto=None, sede=sede, bultos_por_lote=20, unidades_por_bulto=8,
        )
        lote = _crear_lote(sede=sede)
        config = EmpaqueService()._resolver_config(lote)
        self.assertEqual(config.bultos_por_lote, 20)
        self.assertEqual(config.unidades_por_bulto, 8)

    def test_solo_producto_supera_global(self):
        sede = SedeFactory()
        producto = ProductoFactory(sede=sede)
        ConfiguracionEmpaque.objects.create(
            producto=None, sede=None, bultos_por_lote=10, unidades_por_bulto=10,
        )
        ConfiguracionEmpaque.objects.create(
            producto=producto, sede=None, bultos_por_lote=18, unidades_por_bulto=6,
        )
        lote = _crear_lote(sede=sede, producto=producto)
        config = EmpaqueService()._resolver_config(lote)
        self.assertEqual(config.bultos_por_lote, 18)
        self.assertEqual(config.unidades_por_bulto, 6)

    def test_producto_sede_es_la_mas_especifica(self):
        sede = SedeFactory()
        producto = ProductoFactory(sede=sede)
        ConfiguracionEmpaque.objects.create(
            producto=None, sede=None, bultos_por_lote=10, unidades_por_bulto=10,
        )
        ConfiguracionEmpaque.objects.create(
            producto=producto, sede=None, bultos_por_lote=18, unidades_por_bulto=6,
        )
        ConfiguracionEmpaque.objects.create(
            producto=None, sede=sede, bultos_por_lote=20, unidades_por_bulto=8,
        )
        ConfiguracionEmpaque.objects.create(
            producto=producto, sede=sede, bultos_por_lote=25, unidades_por_bulto=5,
        )
        lote = _crear_lote(sede=sede, producto=producto)
        config = EmpaqueService()._resolver_config(lote)
        self.assertEqual(config.bultos_por_lote, 25)
        self.assertEqual(config.unidades_por_bulto, 5)


# ---------------------------------------------------------------------------
# 2. Conservación de peso
# ---------------------------------------------------------------------------

class ConservacionPesoTest(TestCase):
    """La suma de los pesos de los bultos debe igualar el peso del lote."""

    def setUp(self):
        self.usuario = CustomUserFactory()

    @patch("gestion.services.empaque_service.PrintingService.generate_zpl_labels_batch", return_value="ZPL_OK")
    def test_suma_exacta_peso_divisible(self, _mock_zpl):
        # 150 / 15 = 10 exacto
        lote = _crear_lote(peso=Decimal("150.000"))
        EmpaqueService().generar_bultos(lote, self.usuario)

        suma = sum((b.peso_neto for b in lote.bultos.all()), Decimal("0"))
        self.assertEqual(suma, Decimal("150.000"))

    @patch("gestion.services.empaque_service.PrintingService.generate_zpl_labels_batch", return_value="ZPL_OK")
    def test_suma_exacta_con_residuo_redondeo(self, _mock_zpl):
        # 100 / 15 = 6.666... → último bulto absorbe el residuo
        lote = _crear_lote(peso=Decimal("100.000"))
        EmpaqueService().generar_bultos(lote, self.usuario)

        bultos = list(lote.bultos.order_by("correlativo"))
        suma = sum((b.peso_neto for b in bultos), Decimal("0"))
        self.assertEqual(suma, Decimal("100.000"))
        # Los primeros 14 son iguales, el último absorbe diferencia
        self.assertTrue(all(b.peso_neto == bultos[0].peso_neto for b in bultos[:14]))
        self.assertNotEqual(bultos[-1].peso_neto, bultos[0].peso_neto)

    @patch("gestion.services.empaque_service.PrintingService.generate_zpl_labels_batch", return_value="ZPL_OK")
    def test_config_personalizada_genera_bultos_correctos(self, _mock_zpl):
        sede = SedeFactory()
        ConfiguracionEmpaque.objects.create(
            producto=None, sede=sede,
            bultos_por_lote=20, unidades_por_bulto=8, tara_bulto=Decimal("0.250"),
        )
        lote = _crear_lote(peso=Decimal("80.000"), sede=sede)
        resultado = EmpaqueService().generar_bultos(lote, self.usuario)

        self.assertEqual(resultado.bultos_generados, 20)
        self.assertEqual(lote.bultos.count(), 20)
        self.assertEqual(
            sum((b.peso_neto for b in lote.bultos.all()), Decimal("0")),
            Decimal("80.000"),
        )
        # Tara aplicada desde la configuración
        self.assertTrue(all(b.tara == Decimal("0.250") for b in lote.bultos.all()))


# ---------------------------------------------------------------------------
# 3. Idempotencia y excepciones
# ---------------------------------------------------------------------------

class IdempotenciaYExcepcionesTest(TestCase):
    def setUp(self):
        self.usuario = CustomUserFactory()

    @patch("gestion.services.empaque_service.PrintingService.generate_zpl_labels_batch", return_value="ZPL_OK")
    def test_no_permite_duplicar_bultos(self, _mock_zpl):
        lote = _crear_lote()
        service = EmpaqueService()
        service.generar_bultos(lote, self.usuario)
        with self.assertRaises(BultosYaGenerados):
            service.generar_bultos(lote, self.usuario)

    def test_lote_sin_peso_lanza_excepcion(self):
        lote = _crear_lote(peso=Decimal("0"))
        with self.assertRaises(LoteSinPesoValido):
            EmpaqueService().generar_bultos(lote, self.usuario)

    def test_obtener_etiquetas_sin_bultos_falla(self):
        lote = _crear_lote()
        with self.assertRaises(BultosYaGenerados):
            EmpaqueService().obtener_etiquetas(lote)


# ---------------------------------------------------------------------------
# 4. Auditoría — cada BultoEmpaque deja rastro en AuditLog
# ---------------------------------------------------------------------------

class AuditoriaBultoEmpaqueTest(TestCase):
    @patch("gestion.services.empaque_service.PrintingService.generate_zpl_labels_batch", return_value="ZPL_OK")
    def test_creacion_registra_audit_log(self, _mock_zpl):
        usuario = CustomUserFactory()
        lote = _crear_lote()
        EmpaqueService().generar_bultos(lote, usuario)

        ct = ContentType.objects.get_for_model(BultoEmpaque)
        bulto_ids = list(lote.bultos.values_list("id", flat=True))
        logs = AuditLog.objects.filter(content_type=ct, object_id__in=bulto_ids, accion="CREATE")
        self.assertEqual(logs.count(), 15)
        self.assertTrue(all(l.justificacion and lote.codigo_lote in l.justificacion for l in logs))


# ---------------------------------------------------------------------------
# 5. Generación ZPL masiva — integración con PrintingService
# ---------------------------------------------------------------------------

class GeneracionZPLMasivaTest(TestCase):
    @patch("gestion.services.empaque_service.PrintingService.generate_zpl_labels_batch")
    def test_invoca_printing_service_con_payload_correcto(self, mock_zpl):
        mock_zpl.return_value = "^XA...^XZ"
        usuario = CustomUserFactory()
        lote = _crear_lote()
        resultado = EmpaqueService().generar_bultos(lote, usuario)

        self.assertEqual(resultado.zpl_unificado, "^XA...^XZ")
        mock_zpl.assert_called_once()
        # El payload enviado debe ser una lista de dicts con la estructura esperada
        payload_enviado = mock_zpl.call_args.args[0]
        self.assertEqual(len(payload_enviado), 15)
        for item in payload_enviado:
            self.assertIn("producto_desc", item)
            self.assertIn("lote_codigo", item)
            self.assertIn("peso_neto", item)
            self.assertIn("qr_data", item)

    @patch("gestion.services.empaque_service.PrintingService.generate_zpl_labels_batch", return_value=None)
    def test_servicio_caido_no_aborta_generacion(self, _mock_zpl):
        """Si printing_service está caído, los bultos se persisten igual y zpl=None."""
        usuario = CustomUserFactory()
        lote = _crear_lote()
        resultado = EmpaqueService().generar_bultos(lote, usuario)

        self.assertEqual(resultado.bultos_generados, 15)
        self.assertIsNone(resultado.zpl_unificado)
