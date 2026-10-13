"""
Motor MRP por sede (TEX-27, ADR-012).

Reglas:
- Comprados (materia prima, químico, colorante, insumo) → sugerencia de compra:
  lo que piden las órdenes abiertas + stock mínimo − disponible.
- Fabricados (hilo, tela, subproducto) → necesidad de producción para el Plan MTS:
  pedidos pendientes + demanda interna + stock mínimo − disponible − en producción.
- Disponible = stock de las bodegas de la sede − stock comprometido.
- Una orden abierta pide lo que le falta de su producto de entrada (relación 1:1) y sus
  químicos si todavía no se descargaron, con la misma dosificación que la descarga.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): comprado / fabricado; con / sin litros; descargada / no.
- Análisis de valores límite (BVA): disponible igual al mínimo, una unidad por debajo.
- Tabla de decisión (TD): cubierto = max(despachado, reservado).
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from gestion.models import AuditLog, DescargaQuimicoOP, DetallePedido, OrdenProduccion, PedidoVenta, VersionFormula
from gestion.services.versionado_formula import VersionadoFormulaService
from gestion.tests.factories import (
    BodegaFactory,
    CustomUserFactory,
    DetalleFormulaFactory,
    FaseRecetaFactory,
    FormulaColorFactory,
    LoteProduccionFactory,
    OrdenProduccionFactory,
    ProductoFactory,
    SedeFactory,
)
from inventory.models import (
    DetalleHistorialDespacho,
    HistorialDespacho,
    MRPEjecucion,
    OrdenCompraSugerida,
    RequerimientoMaterial,
    StockBodega,
)
from inventory.services.mrp import (
    MRPEngine,
    es_comprado,
    necesidades_produccion,
    requerimientos_de_orden,
    stock_disponible_por_producto,
)
from inventory.services.reposicion_service import ReposicionService


class _EscenarioMRP(TestCase):
    """Sede con una orden de hilo que consume materia prima y lleva una fórmula con un
    químico en g/L y un colorante (también tipo químico) en %."""

    def setUp(self):
        self.sede = SedeFactory(nombre='Sede MRP')
        self.bodega_mp = BodegaFactory(sede=self.sede, nombre='Materia Prima')
        self.bodega_q = BodegaFactory(sede=self.sede, nombre='Químicos')
        self.materia_prima = ProductoFactory(
            sede=self.sede, codigo='MP-ALG', descripcion='Algodón crudo', tipo='materia_prima',
            stock_minimo=Decimal('20'),
        )
        self.hilo = ProductoFactory(sede=self.sede, codigo='HI-AZ', descripcion='Hilo azul', tipo='hilo',
                                    stock_minimo=Decimal('0'))
        self.quimico = ProductoFactory(sede=self.sede, codigo='Q-IGU', descripcion='Igualante', tipo='quimico',
                                       stock_minimo=Decimal('0'))
        # Las fórmulas solo admiten productos de tipo químico (DetalleFormula.limit_choices_to).
        self.colorante = ProductoFactory(sede=self.sede, codigo='C-AZ', descripcion='Colorante azul',
                                         tipo='quimico', stock_minimo=Decimal('0'))
        self.formula = FormulaColorFactory(sede=self.sede, estado='en_pruebas')
        fase = FaseRecetaFactory(formula=self.formula, nombre='tintura', orden=1)
        DetalleFormulaFactory(fase=fase, producto=self.quimico, tipo_calculo='gr_l',
                              concentracion_gr_l=Decimal('2.000'), orden_adicion=1)
        DetalleFormulaFactory(fase=fase, producto=self.colorante, tipo_calculo='pct', concentracion_gr_l=None,
                              porcentaje=Decimal('1.500'), orden_adicion=2)
        # Una orden con fórmula solo se lanza con versión oficial, y la congela al lanzarse.
        tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        version = VersionadoFormulaService.crear_version(self.formula, 'Receta aprobada en laboratorio', tintorero)
        VersionadoFormulaService.marcar_oficial(self.formula, version.numero, tintorero)
        self.orden = self._orden()

    def _orden(self, **cambios):
        datos = {
            'sede': self.sede, 'estado': 'en_proceso', 'producto_entrada': self.materia_prima,
            'producto_salida': self.hilo, 'bodega_entrada': self.bodega_mp, 'formula_color': self.formula,
            'peso_neto_requerido': Decimal('100.00'), 'litros_bano': Decimal('800.00'),
            'fecha_inicio_planificada': date(2026, 10, 20),
        }
        datos.update(cambios)
        return OrdenProduccionFactory(**datos)

    def _stock(self, producto, cantidad, bodega=None, comprometido='0'):
        return StockBodega.objects.create(
            bodega=bodega or self.bodega_mp, producto=producto,
            cantidad=Decimal(cantidad), stock_comprometido=Decimal(comprometido),
        )

    def _sugerencias(self, sede=None):
        return {s.producto.codigo: s for s in OrdenCompraSugerida.objects.filter(sede=sede or self.sede)}


class ReglasMRPTestCase(_EscenarioMRP):
    def test_clasificacion_dado_tipo_de_producto_cuando_evalua_entonces_separa_comprados_de_fabricados(self):
        for tipo in ('materia_prima', 'quimico', 'colorante', 'insumo'):
            self.assertTrue(es_comprado(ProductoFactory.build(tipo=tipo)), tipo)
        for tipo in ('hilo', 'tela', 'subproducto'):
            self.assertFalse(es_comprado(ProductoFactory.build(tipo=tipo)), tipo)

    def test_disponible_dado_stock_comprometido_y_otra_sede_cuando_calcula_entonces_solo_lo_libre_de_la_sede(self):
        self._stock(self.materia_prima, '50', comprometido='15')
        self._stock(self.materia_prima, '10', bodega=self.bodega_q)
        self._stock(self.materia_prima, '999', bodega=BodegaFactory(sede=SedeFactory()))

        disponible = stock_disponible_por_producto(self.sede.id)

        self.assertEqual(disponible[self.materia_prima.id], Decimal('45'))


class RequerimientosDeOrdenTestCase(_EscenarioMRP):
    def _por_codigo(self, analisis):
        return {r.producto.codigo: r for r in analisis.requerimientos}

    def test_requerimientos_dado_litros_y_lotes_producidos_cuando_calcula_entonces_gr_l_pct_y_base_pendiente(self):
        LoteProduccionFactory(orden_produccion=self.orden, peso_neto_producido=Decimal('40.000'))

        reqs = self._por_codigo(requerimientos_de_orden(self.orden))

        self.assertEqual(reqs['MP-ALG'].cantidad_kg, Decimal('60.000'))  # 100 − 40 producidos
        self.assertTrue(reqs['MP-ALG'].es_base)
        self.assertEqual(reqs['Q-IGU'].cantidad_kg, Decimal('1.600'))  # 2 g/L × 800 L
        self.assertEqual(reqs['C-AZ'].cantidad_kg, Decimal('1.500'))  # 1,5 % de 100 kg

    def test_requerimientos_dado_orden_sin_litros_cuando_calcula_entonces_usa_la_relacion_1_a_10(self):
        orden = self._orden(litros_bano=None)
        reqs = self._por_codigo(requerimientos_de_orden(orden))
        self.assertEqual(reqs['Q-IGU'].cantidad_kg, Decimal('2.000'))  # 2 g/L × (100 kg × 10 L)

    def test_requerimientos_dado_version_congelada_cuando_la_receta_viva_cambia_entonces_usa_la_congelada(self):
        version = VersionFormula.objects.create(
            formula=self.formula, numero=2, motivo='Versión congelada de la orden',
            snapshot={'formula': {}, 'fases': [{'orden': 1, 'detalles': [{
                'producto_id': self.quimico.id, 'producto_codigo': 'Q-IGU', 'producto_descripcion': 'Igualante',
                'tipo_calculo': 'gr_l', 'concentracion_gr_l': '5.000', 'porcentaje': None, 'orden_adicion': 1,
            }]}]},
        )
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(version_formula=version)
        self.orden.refresh_from_db()

        reqs = self._por_codigo(requerimientos_de_orden(self.orden))

        self.assertEqual(reqs['Q-IGU'].cantidad_kg, Decimal('4.000'))  # 5 g/L × 800 L de la versión
        self.assertNotIn('C-AZ', reqs)

    def test_requerimientos_dado_quimicos_ya_descargados_cuando_calcula_entonces_los_marca_como_descontados(self):
        DescargaQuimicoOP.objects.create(
            orden_produccion=self.orden, producto=self.quimico, bodega=self.bodega_q, tipo_calculo='gr_l',
            cantidad_calculada_kg=Decimal('1.6'), estado='aplicada',
        )

        reqs = self._por_codigo(requerimientos_de_orden(self.orden))

        self.assertTrue(reqs['Q-IGU'].ya_descontado)
        self.assertTrue(reqs['C-AZ'].ya_descontado)
        self.assertFalse(reqs['MP-ALG'].ya_descontado)

    def test_requerimientos_dado_descarga_revertida_cuando_calcula_entonces_los_quimicos_vuelven_a_pedirse(self):
        DescargaQuimicoOP.objects.create(
            orden_produccion=self.orden, producto=self.quimico, bodega=self.bodega_q, tipo_calculo='gr_l',
            cantidad_calculada_kg=Decimal('1.6'), estado='revertida',
        )
        reqs = self._por_codigo(requerimientos_de_orden(self.orden))
        self.assertFalse(reqs['Q-IGU'].ya_descontado)

    def test_requerimientos_dado_orden_sin_peso_cuando_calcula_entonces_advierte_y_no_pide_nada(self):
        orden = self._orden(peso_neto_requerido=None, codigo='OP-CONT-01')

        analisis = requerimientos_de_orden(orden)

        self.assertEqual(analisis.requerimientos, [])
        self.assertEqual(len(analisis.advertencias), 1)
        self.assertIn('OP-CONT-01', analisis.advertencias[0])

    def test_requerimientos_dado_insumo_en_litros_cuando_calcula_entonces_lo_excluye_con_advertencia(self):
        self.quimico.unidad_medida = 'l'
        self.quimico.save()

        analisis = requerimientos_de_orden(self.orden)

        self.assertNotIn('Q-IGU', self._por_codigo(analisis))
        self.assertTrue(any('Q-IGU' in a and 'kg' in a for a in analisis.advertencias))

    def test_requerimientos_dado_orden_completada_en_peso_cuando_calcula_entonces_la_base_queda_en_cero(self):
        LoteProduccionFactory(orden_produccion=self.orden, peso_neto_producido=Decimal('120.000'))
        reqs = self._por_codigo(requerimientos_de_orden(self.orden))
        self.assertNotIn('MP-ALG', reqs)


class MotorMRPTestCase(_EscenarioMRP):
    def test_motor_dado_orden_abierta_cuando_ejecuta_entonces_sugiere_compra_con_su_desglose(self):
        LoteProduccionFactory(orden_produccion=self.orden, peso_neto_producido=Decimal('40.000'))
        self._stock(self.materia_prima, '10')
        self._stock(self.quimico, '1.0', bodega=self.bodega_q)

        ejecucion = MRPEngine.ejecutar(self.sede)

        self.assertEqual(ejecucion.estado, MRPEjecucion.ESTADO_COMPLETADA)
        sugerencias = self._sugerencias()
        mp = sugerencias['MP-ALG']
        self.assertEqual((mp.requerido, mp.stock_minimo, mp.stock_disponible, mp.cantidad_sugerida),
                         (Decimal('60.000'), Decimal('20.000'), Decimal('10.000'), Decimal('70.000')))
        self.assertEqual(sugerencias['Q-IGU'].cantidad_sugerida, Decimal('0.600'))  # 1,6 − 1,0
        self.assertEqual(sugerencias['C-AZ'].cantidad_sugerida, Decimal('1.500'))
        self.assertNotIn('HI-AZ', sugerencias)  # el hilo se fabrica, no se compra
        self.assertEqual(ejecucion.sugerencias_compra, 3)

    def test_motor_dado_orden_abierta_cuando_ejecuta_entonces_guarda_requerimientos_por_orden_y_fecha(self):
        MRPEngine.ejecutar(self.sede)

        reqs = RequerimientoMaterial.objects.filter(sede=self.sede)
        self.assertEqual(reqs.count(), 3)
        self.assertTrue(all(r.orden_produccion_id == self.orden.id for r in reqs))
        self.assertTrue(all(r.fecha_requerida == date(2026, 10, 20) for r in reqs))

    def test_motor_dado_stock_suficiente_cuando_ejecuta_entonces_no_sugiere_compra(self):
        self._stock(self.materia_prima, '200')
        self._stock(self.quimico, '50', bodega=self.bodega_q)
        self._stock(self.colorante, '50', bodega=self.bodega_q)

        MRPEngine.ejecutar(self.sede)

        self.assertEqual(self._sugerencias(), {})

    def test_motor_dado_disponible_igual_al_minimo_sin_ordenes_cuando_ejecuta_entonces_no_sugiere(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado='finalizada')
        self._stock(self.materia_prima, '20')  # exactamente el mínimo
        MRPEngine.ejecutar(self.sede)
        self.assertNotIn('MP-ALG', self._sugerencias())

    def test_motor_dado_disponible_un_kilo_bajo_el_minimo_sin_ordenes_cuando_ejecuta_entonces_sugiere_un_kilo(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado='finalizada')
        self._stock(self.materia_prima, '19')
        MRPEngine.ejecutar(self.sede)
        self.assertEqual(self._sugerencias()['MP-ALG'].cantidad_sugerida, Decimal('1.000'))

    def test_motor_dado_stock_comprometido_cuando_ejecuta_entonces_no_lo_cuenta_como_disponible(self):
        self._stock(self.materia_prima, '200', comprometido='190')
        MRPEngine.ejecutar(self.sede)
        self.assertEqual(self._sugerencias()['MP-ALG'].cantidad_sugerida, Decimal('110.000'))  # 100 + 20 − 10

    def test_motor_dado_quimicos_ya_descargados_cuando_ejecuta_entonces_no_los_vuelve_a_pedir(self):
        DescargaQuimicoOP.objects.create(
            orden_produccion=self.orden, producto=self.quimico, bodega=self.bodega_q, tipo_calculo='gr_l',
            cantidad_calculada_kg=Decimal('1.6'), estado='aplicada',
        )
        MRPEngine.ejecutar(self.sede)
        sugerencias = self._sugerencias()
        self.assertNotIn('Q-IGU', sugerencias)
        self.assertNotIn('C-AZ', sugerencias)

    def test_motor_dado_corrida_continua_sin_peso_cuando_ejecuta_entonces_no_aborta_y_la_advierte(self):
        self._orden(peso_neto_requerido=None, codigo='E1-CONT-01')

        ejecucion = MRPEngine.ejecutar(self.sede)

        self.assertEqual(ejecucion.estado, MRPEjecucion.ESTADO_COMPLETADA)
        self.assertTrue(any('E1-CONT-01' in a for a in ejecucion.advertencias))
        self.assertIn('MP-ALG', self._sugerencias())  # la otra orden sí se calculó

    def test_motor_dado_orden_finalizada_cuando_ejecuta_entonces_no_la_considera(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado='finalizada')
        MRPEngine.ejecutar(self.sede)
        self.assertFalse(RequerimientoMaterial.objects.filter(sede=self.sede).exists())

    def test_motor_dado_producto_de_entrada_fabricado_cuando_ejecuta_entonces_no_lo_sugiere_comprar(self):
        self._orden(producto_entrada=self.hilo, producto_salida=ProductoFactory(sede=self.sede, tipo='tela'),
                    formula_color=None)
        MRPEngine.ejecutar(self.sede)
        self.assertNotIn('HI-AZ', self._sugerencias())

    def test_motor_dado_otra_sede_cuando_ejecuta_una_entonces_no_toca_los_resultados_de_la_otra(self):
        otra = SedeFactory()
        OrdenCompraSugerida.objects.create(
            ejecucion=MRPEngine.ejecutar(otra), producto=self.materia_prima, sede=otra, requerido=Decimal('1'),
            stock_minimo=Decimal('0'), stock_disponible=Decimal('0'), cantidad_sugerida=Decimal('1'),
        )

        MRPEngine.ejecutar(self.sede)

        self.assertEqual(OrdenCompraSugerida.objects.filter(sede=otra).count(), 1)

    def test_motor_dado_segunda_ejecucion_cuando_recalcula_entonces_reemplaza_los_resultados_de_la_sede(self):
        MRPEngine.ejecutar(self.sede)
        segunda = MRPEngine.ejecutar(self.sede)

        self.assertEqual(OrdenCompraSugerida.objects.filter(sede=self.sede).count(), 3)
        self.assertTrue(all(s.ejecucion_id == segunda.id for s in OrdenCompraSugerida.objects.filter(sede=self.sede)))
        self.assertEqual(MRPEjecucion.objects.filter(sede=self.sede).count(), 2)

    def test_motor_dado_error_inesperado_cuando_ejecuta_entonces_registra_fallida_y_conserva_lo_anterior(self):
        MRPEngine.ejecutar(self.sede)
        with patch('inventory.services.mrp.motor.requerimientos_de_orden', side_effect=RuntimeError('boom')), \
                self.assertLogs('inventory.mrp', level='ERROR'):
            fallida = MRPEngine.ejecutar(self.sede)

        self.assertEqual(fallida.estado, MRPEjecucion.ESTADO_FALLIDA)
        self.assertTrue(fallida.mensaje_error)
        self.assertNotIn('boom', fallida.mensaje_error)  # el detalle interno queda en el log
        self.assertEqual(OrdenCompraSugerida.objects.filter(sede=self.sede).count(), 3)

    def test_motor_dado_ejecucion_cuando_termina_entonces_registra_usuario_y_conteos(self):
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        ejecucion = MRPEngine.ejecutar(self.sede, bodeguero)
        self.assertEqual(ejecucion.iniciada_por, bodeguero)
        self.assertEqual(ejecucion.requerimientos, 3)
        self.assertLessEqual(ejecucion.inicio, ejecucion.fin)

    def test_motor_dado_resultados_calculados_cuando_ejecuta_entonces_audita_la_ejecucion_y_no_cada_fila(self):
        MRPEngine.ejecutar(self.sede)
        MRPEngine.ejecutar(self.sede)

        auditados = AuditLog.objects.filter(content_type__in=[
            ContentType.objects.get_for_model(RequerimientoMaterial),
            ContentType.objects.get_for_model(OrdenCompraSugerida),
        ])
        self.assertFalse(auditados.exists())
        self.assertEqual(AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(MRPEjecucion)).count(), 2)

    def test_motor_dado_mas_ordenes_cuando_ejecuta_entonces_las_consultas_crecen_acotadas_por_orden(self):
        def consultas():
            with CaptureQueriesContext(connection) as ctx:
                MRPEngine.ejecutar(self.sede)
            return len(ctx.captured_queries)

        base = consultas()
        for _ in range(5):
            self._orden()
        self.assertLessEqual(consultas() - base, 5 * 4)


class NecesidadesProduccionTestCase(_EscenarioMRP):
    """Necesidad de producción de productos fabricados (alimenta el Plan MTS)."""

    def setUp(self):
        super().setUp()
        # La orden del escenario es de hilo: 100 kg pendientes en producción.
        self.pedido = PedidoVenta.objects.create(sede=self.sede, estado='pendiente', guia_remision='GR-MRP-1')
        self.detalle = DetallePedido.objects.create(
            pedido_venta=self.pedido, producto=self.hilo, cantidad=1, piezas=1,
            peso=Decimal('300'), precio_unitario=Decimal('1'),
        )

    def _despachar(self, peso, es_devolucion=False):
        historial = HistorialDespacho.objects.create(total_bultos=1, total_peso=Decimal(peso))
        DetalleHistorialDespacho.objects.create(
            historial=historial, producto=self.hilo, peso=Decimal(peso), pedido=self.pedido,
            es_devolucion=es_devolucion,
        )

    def _necesidad(self, codigo='HI-AZ'):
        return next((n for n in necesidades_produccion(self.sede.id) if n['producto_codigo'] == codigo), None)

    def test_necesidad_dado_pedido_despacho_stock_y_produccion_cuando_calcula_entonces_neta_todo(self):
        self.hilo.stock_minimo = Decimal('10')
        self.hilo.save()
        self._despachar('30')
        self._stock(self.hilo, '20')

        n = self._necesidad()

        # pedidos 300 − 30 despachado = 270; + mínimo 10 − disponible 20 − en producción 100 = 160
        self.assertEqual(n['demanda_pedidos'], Decimal('270.0000'))
        self.assertEqual(n['en_produccion'], Decimal('100.0000'))
        self.assertEqual(n['stock_actual'], Decimal('20.0000'))
        self.assertEqual(n['deficit'], Decimal('160.0000'))

    def test_necesidad_dado_reservado_mayor_que_despachado_cuando_calcula_entonces_cubre_con_el_mayor(self):
        DetallePedido.objects.filter(pk=self.detalle.pk).update(cantidad_fabricada=Decimal('80'))
        self._despachar('30')
        self.assertEqual(self._necesidad()['demanda_pedidos'], Decimal('220.0000'))  # 300 − max(30, 80)

    def test_necesidad_dado_despacho_revertido_cuando_calcula_entonces_no_cuenta_como_despachado(self):
        self._despachar('30', es_devolucion=True)
        self.assertEqual(self._necesidad()['demanda_pedidos'], Decimal('300.0000'))

    def test_necesidad_dado_pedido_despachado_cuando_calcula_entonces_no_genera_demanda(self):
        PedidoVenta.objects.filter(pk=self.pedido.pk).update(estado='despachado')
        self.assertIsNone(self._necesidad())  # sin pedidos ni mínimo: la producción en curso sobra

    def test_necesidad_dado_cobertura_completa_cuando_calcula_entonces_no_aparece(self):
        self._stock(self.hilo, '250')
        self.assertIsNone(self._necesidad())  # 300 − 250 − 100 < 0

    def test_necesidad_dado_producto_de_entrada_fabricado_cuando_calcula_entonces_es_demanda_interna(self):
        tela = ProductoFactory(sede=self.sede, codigo='TE-01', tipo='tela', stock_minimo=Decimal('0'))
        self._orden(producto_entrada=self.hilo, producto_salida=tela, formula_color=None,
                    peso_neto_requerido=Decimal('50'))
        self.assertEqual(self._necesidad()['demanda_interna'], Decimal('50.0000'))

    def test_necesidad_dado_productos_comprados_bajo_minimo_cuando_calcula_entonces_no_los_propone_producir(self):
        codigos = {n['producto_codigo'] for n in necesidades_produccion(self.sede.id)}
        self.assertNotIn('MP-ALG', codigos)  # materia prima bajo su mínimo: se compra, no se produce

    def test_necesidad_dado_corrida_sin_peso_cuando_calcula_entonces_no_suma_en_produccion(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(peso_neto_requerido=None)
        self.assertEqual(self._necesidad()['en_produccion'], Decimal('0.0000'))

    def test_necesidad_dado_mas_pedidos_cuando_calcula_entonces_las_consultas_no_crecen(self):
        def consultas():
            with CaptureQueriesContext(connection) as ctx:
                necesidades_produccion(self.sede.id)
            return len(ctx.captured_queries)

        base = consultas()
        for i in range(10):
            pedido = PedidoVenta.objects.create(sede=self.sede, estado='pendiente', guia_remision=f'GR-{i}')
            DetallePedido.objects.create(pedido_venta=pedido, producto=self.hilo, cantidad=1, piezas=1,
                                         peso=Decimal('5'), precio_unitario=Decimal('1'))
        self.assertEqual(consultas(), base)

    def test_reposicion_dado_sede_cuando_analiza_entonces_delega_en_la_necesidad_de_produccion(self):
        self.assertEqual(ReposicionService.analizar_necesidades_reposicion(sede_id=self.sede.id),
                         necesidades_produccion(self.sede.id))
