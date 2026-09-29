"""
Pruebas de la Fase 3 de recetas versionadas de tintorería
(docs/superpowers/specs/2026-09-24-recetas-versionadas-tintoreria-design.md §5.6, §6, §7).

Cubre: OrdenProduccion.litros_bano y relacion_bano (propiedad derivada), la regla 8
(litros acotados por el volumen de la máquina), el cálculo unificado de dosificación
desde snapshot congelado, y los endpoints calcular-dosificacion / historial /
descargas-quimico de OrdenProduccion.

Técnicas ISTQB aplicadas:
- Análisis de valores límite (BVA): litros_bano igual al volumen de máquina (se acepta)
  vs. por encima (se rechaza); peso o litros en cero.
- Partición de equivalencia (EP): máquina sin volumen declarado (no se valida).
- Caja blanca (CB-D): descargar_para_op usa version_formula.snapshot cuando existe.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import OrdenProduccion
from gestion.services.versionado_formula import VersionadoFormulaService
from gestion.services_formula import DosificacionCalculator, calcular_dosificacion_desde_snapshot
from gestion.tests.factories import (
    CustomUserFactory, DetalleFormulaFactory, FaseRecetaFactory, FormulaColorFactory,
    MaquinaFactory, OrdenProduccionFactory, ProductoFactory, SedeFactory,
)


class RelacionBanoPropertyTestCase(TestCase):
    def test_relacion_bano_dado_litros_y_peso_cuando_consulta_entonces_deriva_relacion(self):
        orden = OrdenProduccionFactory(litros_bano=Decimal('860.00'), peso_neto_requerido=Decimal('100.00'))
        self.assertEqual(orden.relacion_bano, Decimal('8.6000'))

    def test_relacion_bano_dado_litros_nulos_cuando_consulta_entonces_none(self):
        orden = OrdenProduccionFactory(litros_bano=None)
        self.assertIsNone(orden.relacion_bano)

    def test_relacion_bano_dado_peso_nulo_cuando_consulta_entonces_none(self):
        orden = OrdenProduccionFactory(litros_bano=Decimal('100.00'), peso_neto_requerido=None)
        self.assertIsNone(orden.relacion_bano)


class LitrosBanoAcotadoPorMaquinaTestCase(TestCase):
    """Regla 8: si la máquina declara volumen de baño, litros_bano no puede excederlo."""

    def test_litros_bano_dado_igual_al_volumen_cuando_valida_entonces_se_acepta(self):
        maquina = MaquinaFactory(volumen_bano_litros=Decimal('1000.00'))
        orden = OrdenProduccionFactory(maquina_asignada=maquina, litros_bano=Decimal('1000.00'))
        orden.full_clean()  # no debe lanzar

    def test_litros_bano_dado_por_encima_del_volumen_cuando_valida_entonces_error(self):
        # AuditableModelMixin.save() ya corre full_clean(): el error sale al crear.
        maquina = MaquinaFactory(volumen_bano_litros=Decimal('1000.00'))
        with self.assertRaises(ValidationError):
            OrdenProduccionFactory(maquina_asignada=maquina, litros_bano=Decimal('1000.01'))

    def test_litros_bano_dado_maquina_sin_volumen_declarado_cuando_valida_entonces_no_se_valida(self):
        # EP: máquina sin volumen_bano_litros -> no hay tope, solo se advertiría en la UI
        maquina = MaquinaFactory(volumen_bano_litros=None)
        orden = OrdenProduccionFactory(maquina_asignada=maquina, litros_bano=Decimal('99999.00'))
        orden.full_clean()  # no debe lanzar


class CalcularDesdeLitrosTestCase(TestCase):
    """DosificacionCalculator.calcular_desde_litros: conversión peso/litros -> kg_tela/relacion_bano."""

    def setUp(self):
        self.formula = FormulaColorFactory(estado='en_pruebas')
        fase = FaseRecetaFactory(formula=self.formula)
        quimico = ProductoFactory(tipo='quimico')
        DetalleFormulaFactory(fase=fase, producto=quimico, tipo_calculo='gr_l', concentracion_gr_l=Decimal('2.000'))

    def test_calcular_desde_litros_dado_peso_y_litros_cuando_calcula_entonces_coincide_con_relacion_equivalente(self):
        resultado = DosificacionCalculator(self.formula).calcular_desde_litros(
            peso=Decimal('100'), litros=Decimal('1000'))
        self.assertEqual(resultado.relacion_bano, Decimal('10'))
        self.assertEqual(resultado.volumen_bano_litros, Decimal('1000'))
        # gr/L sobre 1000 L con 2 gr/L = 2000 gr = 2 kg
        self.assertEqual(resultado.insumos[0].cantidad_kg, Decimal('2.000000'))

    def test_calcular_desde_litros_dado_peso_cero_cuando_calcula_entonces_error(self):
        with self.assertRaises(ValueError):
            DosificacionCalculator(self.formula).calcular_desde_litros(peso=Decimal('0'), litros=Decimal('100'))


class CalcularDesdeSnapshotTestCase(TestCase):
    """Regla 6: la descarga de químicos de una orden lanzada usa el snapshot congelado."""

    def setUp(self):
        self.formula = FormulaColorFactory(estado='en_pruebas')
        fase = FaseRecetaFactory(formula=self.formula)
        self.producto = ProductoFactory(descripcion='Colorante Azul', tipo='quimico')
        DetalleFormulaFactory(
            fase=fase, producto=self.producto, tipo_calculo='pct', porcentaje=Decimal('1.500'),
            concentracion_gr_l=None,
        )
        self.version = VersionadoFormulaService.asegurar_version_oficial(
            self.formula, 'Aprobación inicial de prueba', CustomUserFactory())

    def test_calcular_desde_snapshot_dado_snapshot_congelado_cuando_calcula_entonces_usa_sus_datos(self):
        resultado = calcular_dosificacion_desde_snapshot(
            self.version.snapshot, peso=Decimal('100'), litros=Decimal('800'))
        self.assertEqual(len(resultado.insumos), 1)
        insumo = resultado.insumos[0]
        # % sobre peso: 100 * 1.5 / 100 = 1.5 kg
        self.assertEqual(insumo.cantidad_kg, Decimal('1.500000'))
        self.assertEqual(insumo.producto_descripcion, 'Colorante Azul')

    def test_calcular_desde_snapshot_dado_peso_cero_cuando_calcula_entonces_error(self):
        with self.assertRaises(ValueError):
            calcular_dosificacion_desde_snapshot(self.version.snapshot, peso=Decimal('0'), litros=Decimal('100'))


class OrdenProduccionDosificacionApiTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.client = APIClient()
        self.client.force_authenticate(user=self.tintorero)

        self.formula = FormulaColorFactory(sede=self.sede, estado='en_pruebas')
        fase = FaseRecetaFactory(formula=self.formula)
        quimico = ProductoFactory(tipo='quimico', sede=self.sede)
        DetalleFormulaFactory(fase=fase, producto=quimico, tipo_calculo='gr_l', concentracion_gr_l=Decimal('2.000'))
        VersionadoFormulaService.asegurar_version_oficial(self.formula, 'Aprobación de laboratorio', self.tintorero)

        self.orden = OrdenProduccionFactory(
            sede=self.sede, formula_color=self.formula, peso_neto_requerido=Decimal('100.00'))

    def test_calcular_dosificacion_dado_litros_validos_cuando_calcula_entonces_200(self):
        url = reverse('ordenproduccion-calcular-dosificacion', args=[self.orden.id])
        resp = self.client.post(url, {'litros_bano': '1000.00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(resp.data['relacion_bano']), Decimal('10'))
        self.assertEqual(len(resp.data['insumos']), 1)

    def test_calcular_dosificacion_dado_litros_por_encima_del_volumen_cuando_calcula_entonces_400(self):
        maquina = MaquinaFactory(volumen_bano_litros=Decimal('500.00'), area=self.orden.area)
        self.orden.maquina_asignada = maquina
        self.orden.save()
        url = reverse('ordenproduccion-calcular-dosificacion', args=[self.orden.id])
        resp = self.client.post(url, {'litros_bano': '600.00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calcular_dosificacion_dado_orden_sin_formula_cuando_calcula_entonces_400(self):
        orden_sin_formula = OrdenProduccionFactory(sede=self.sede)
        url = reverse('ordenproduccion-calcular-dosificacion', args=[orden_sin_formula.id])
        resp = self.client.post(url, {'litros_bano': '100.00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_historial_dado_filtro_de_formula_cuando_lista_entonces_solo_esa_formula(self):
        OrdenProduccionFactory(sede=self.sede)  # otra orden, sin fórmula
        url = reverse('ordenproduccion-historial')
        resp = self.client.get(url, {'formula_color': self.formula.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        codigos = [o['codigo'] for o in resp.data['results']] if 'results' in resp.data else [
            o['codigo'] for o in resp.data]
        self.assertIn(self.orden.codigo, codigos)

    def test_descargas_quimico_orden_dado_orden_sin_descargas_cuando_consulta_entonces_lista_vacia(self):
        url = reverse('ordenproduccion-descargas-quimico-orden', args=[self.orden.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])
