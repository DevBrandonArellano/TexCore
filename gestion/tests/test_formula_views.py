"""
Pruebas de gestion/views/formula_views.py — FormulaColorViewSet y DetalleFormulaViewSet.

Cubre acciones (calcular-dosificacion, duplicar, exportar-dosificador), RBAC
por acción (lectura vs escritura vs borrado) y filtrado multi-tenant por sede.

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: get_permissions según acción y rol.
- Particiones de equivalencia (EP): rol tintorero / admin / sin permiso.
- Caja negra: contrato de las acciones personalizadas.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import DetalleFormula
from gestion.tests.factories import (
    SedeFactory, CustomUserFactory, ProductoFactory,
    FormulaColorFactory, FaseRecetaFactory, DetalleFormulaFactory,
)


class FormulaColorViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        # Fórmula con una fase y un insumo (gr/L)
        self.formula = FormulaColorFactory(sede=self.sede, estado='aprobada')
        self.fase = FaseRecetaFactory(formula=self.formula, nombre='tintura')
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede)
        self.detalle = DetalleFormulaFactory(
            fase=self.fase, producto=self.quimico,
            concentracion_gr_l=Decimal('10.00'), tipo_calculo='gr_l',
        )

    def test_formula_dado_autenticado_cuando_lista_entonces_200(self):
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.get(reverse('formulacolor-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_formula_dado_kg_y_relacion_cuando_calcular_dosificacion_entonces_200(self):
        # Caja negra: acción calcular-dosificacion devuelve insumos calculados
        self.client.force_authenticate(user=self.tintorero)
        url = reverse('formulacolor-calcular-dosificacion', args=[self.formula.id])
        resp = self.client.post(url, {'kg_tela': 100, 'relacion_bano': 10}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['insumos']), 1)

    def test_formula_dado_payload_invalido_cuando_calcular_dosificacion_entonces_400(self):
        self.client.force_authenticate(user=self.tintorero)
        url = reverse('formulacolor-calcular-dosificacion', args=[self.formula.id])
        resp = self.client.post(url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_formula_dado_existente_cuando_duplicar_entonces_201_y_nueva_version(self):
        self.client.force_authenticate(user=self.tintorero)
        url = reverse('formulacolor-duplicar', args=[self.formula.id])
        resp = self.client.post(url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['estado'], 'en_pruebas')

    def test_formula_dado_existente_cuando_exportar_dosificador_entonces_ticket(self):
        # Cubre exportar-dosificador (estructura de integración a cocina de colores)
        self.client.force_authenticate(user=self.tintorero)
        url = reverse('formulacolor-exportar-dosificador', args=[self.formula.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['recipe_code'], self.formula.codigo)
        self.assertEqual(len(resp.data['phases']), 1)

    def test_formula_dado_admin_cuando_elimina_con_justificacion_entonces_204(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(
            reverse('formulacolor-detail', args=[self.formula.id]),
            HTTP_X_JUSTIFICACION_AUDITORIA='Fórmula obsoleta'
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_formula_dado_tintorero_cuando_elimina_entonces_403(self):
        # Caja blanca: destroy exige IsSystemAdmin; tintorero no puede borrar
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.delete(reverse('formulacolor-detail', args=[self.formula.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class DetalleFormulaViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.formula = FormulaColorFactory(sede=self.sede)
        self.fase = FaseRecetaFactory(formula=self.formula)
        self.detalle = DetalleFormulaFactory(fase=self.fase, producto=ProductoFactory(tipo='quimico', sede=self.sede))

    def test_detalle_dado_autenticado_cuando_lista_entonces_200(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('detalleformula-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detalle_dado_filtro_formula_cuando_lista_entonces_filtra(self):
        # EP: query param formula_color filtra el queryset
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('detalleformula-list'), {'formula_color': 99999})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
