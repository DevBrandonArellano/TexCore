"""
Pruebas de LineaProduccion (Células de Manufactura Flexibles).

Cubre el modelo LineaProduccion, LineaProduccionViewSet y
LineaProduccionSerializer (flag 'compartida' de recurso compartido).

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: RBAC por rol, área y sede.
- Partición de equivalencia: máquina propia vs. ajena; línea activa vs. inactiva.
- Caja blanca del serializer: ramas de validate() en create y PATCH parcial.
"""
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import LineaProduccion
from gestion.tests.factories import (
    SedeFactory, AreaFactory, CustomUserFactory, MaquinaFactory,
    LineaProduccionFactory,
)


class LineaProduccionModelTestCase(TestCase):
    def test_linea_dado_creada_cuando_str_entonces_nombre_y_area(self):
        linea = LineaProduccionFactory(nombre='Tintura A')
        self.assertEqual(str(linea), f"Tintura A ({linea.area.nombre})")

    def test_linea_dado_nombre_duplicado_en_misma_area_cuando_crea_entonces_error(self):
        linea = LineaProduccionFactory()
        with self.assertRaises(IntegrityError), transaction.atomic():
            LineaProduccion.objects.create(nombre=linea.nombre, area=linea.area)

    def test_linea_dado_nombre_duplicado_en_otra_area_cuando_crea_entonces_ok(self):
        linea = LineaProduccionFactory()
        otra = LineaProduccion.objects.create(
            nombre=linea.nombre, area=AreaFactory(sede=linea.area.sede))
        self.assertIsNotNone(otra.pk)


class LineaProduccionViewSetTestCase(TestCase):
    """Tabla de decisión RBAC + validaciones del serializer."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.otra_area = AreaFactory(sede=self.sede)
        self.area_otra_sede = AreaFactory(sede=self.otra_sede)
        self.maquina = MaquinaFactory(area=self.area)
        self.maquina_ajena = MaquinaFactory(area=self.otra_area)
        self.linea = LineaProduccionFactory(area=self.area, maquinas=[self.maquina])
        self.linea_ajena = LineaProduccionFactory(area=self.otra_area)
        self.linea_otra_sede = LineaProduccionFactory(area=self.area_otra_sede)
        self.jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])

    def _listar(self, user):
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('linea-produccion-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return [x['id'] for x in resp.data]

    # --- Scoping de lectura ---

    def test_lineas_dado_jefe_area_cuando_lista_entonces_solo_su_area(self):
        self.assertEqual(self._listar(self.jefe), [self.linea.id])

    def test_lineas_dado_jefe_area_cuando_detail_ajeno_entonces_404(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.get(reverse('linea-produccion-detail', args=[self.linea_ajena.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_lineas_dado_jefe_area_sin_area_cuando_lista_entonces_vacio(self):
        jefe_sin_area = CustomUserFactory(sede=self.sede, area=None, groups=['jefe_area'])
        self.assertEqual(self._listar(jefe_sin_area), [])

    def test_lineas_dado_admin_sistemas_cuando_lista_entonces_ve_todas(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.assertCountEqual(
            self._listar(admin),
            [self.linea.id, self.linea_ajena.id, self.linea_otra_sede.id])

    def test_lineas_dado_usuario_de_otra_sede_cuando_lista_entonces_no_ve_ajenas(self):
        operario = CustomUserFactory(sede=self.otra_sede, groups=['operario'])
        self.assertEqual(self._listar(operario), [self.linea_otra_sede.id])

    def test_lineas_dado_operario_cuando_post_entonces_403(self):
        operario = CustomUserFactory(sede=self.sede, groups=['operario'])
        self.client.force_authenticate(user=operario)
        resp = self.client.post(
            reverse('linea-produccion-list'),
            {'nombre': 'Linea Operario', 'area': self.area.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_lineas_dado_filtro_area_cuando_lista_entonces_filtra(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('linea-produccion-list'), {'area': self.otra_area.id})
        self.assertEqual([x['id'] for x in resp.data], [self.linea_ajena.id])

    # --- Escritura y validación ---

    def test_lineas_dado_jefe_cuando_crea_con_maquinas_propias_entonces_201(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('linea-produccion-list'),
            {'nombre': 'Linea Nueva', 'area': self.area.id, 'maquinas': [self.maquina.id]},
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        detalle = resp.data['maquinas_detail']
        self.assertEqual([d['id'] for d in detalle], [self.maquina.id])
        self.assertEqual(detalle[0]['nombre'], self.maquina.nombre)

    def test_lineas_dado_jefe_cuando_crea_con_maquina_ajena_entonces_400(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('linea-produccion-list'),
            {'nombre': 'Linea Invalida', 'area': self.area.id, 'maquinas': [self.maquina_ajena.id]},
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('maquinas', resp.data)

    def test_lineas_dado_jefe_cuando_crea_en_area_ajena_entonces_400(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('linea-produccion-list'),
            {'nombre': 'Linea Ajena Nueva', 'area': self.otra_area.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('area', resp.data)

    def test_lineas_dado_jefe_cuando_patch_agrega_maquina_ajena_entonces_400(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.patch(
            reverse('linea-produccion-detail', args=[self.linea.id]),
            {'maquinas': [self.maquina.id, self.maquina_ajena.id]}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('maquinas', resp.data)

    def test_lineas_dado_admin_cuando_patch_area_con_maquinas_viejas_entonces_400(self):
        # Rama "maquinas is None + instance": al mover la línea de área se
        # revalidan las máquinas existentes contra el área nueva.
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.patch(
            reverse('linea-produccion-detail', args=[self.linea.id]),
            {'area': self.otra_area.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('maquinas', resp.data)

    def test_lineas_dado_nombre_invalido_cuando_crea_entonces_400(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('linea-produccion-list'),
            {'nombre': 'Linea <script>', 'area': self.area.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lineas_dado_jefe_cuando_delete_propia_entonces_204(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.delete(reverse('linea-produccion-detail', args=[self.linea.id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LineaProduccion.objects.filter(pk=self.linea.pk).exists())

    def test_lineas_dado_jefe_cuando_delete_ajena_entonces_404(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.delete(reverse('linea-produccion-detail', args=[self.linea_ajena.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(LineaProduccion.objects.filter(pk=self.linea_ajena.pk).exists())

    def test_lineas_dado_admin_cuando_crea_en_cualquier_area_entonces_201(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(
            reverse('linea-produccion-list'),
            {'nombre': 'Linea Admin', 'area': self.otra_area.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class RecursoCompartidoTestCase(TestCase):
    """Célula de manufactura flexible: máquina compartida entre líneas activas."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.maquina = MaquinaFactory(area=self.area)
        self.jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=self.jefe)

    def _detalle_por_linea(self):
        resp = self.client.get(reverse('linea-produccion-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return {
            linea['id']: {d['id']: d for d in linea['maquinas_detail']}
            for linea in resp.data
        }

    def test_maquina_dado_dos_lineas_activas_cuando_se_comparte_entonces_ambas_aceptan_y_marcan_compartida(self):
        linea_a = LineaProduccionFactory(area=self.area, maquinas=[self.maquina])
        # La segunda asignación se hace vía API (comportamiento célula flexible:
        # compartir NO es error de validación)
        resp = self.client.post(
            reverse('linea-produccion-list'),
            {'nombre': 'Linea B', 'area': self.area.id, 'maquinas': [self.maquina.id]},
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        linea_b_id = resp.data['id']

        detalle = self._detalle_por_linea()
        for linea_id in (linea_a.id, linea_b_id):
            self.assertIn(self.maquina.id, detalle[linea_id])
            info = detalle[linea_id][self.maquina.id]
            self.assertTrue(info['compartida'])
            self.assertEqual(info['nombre'], self.maquina.nombre)
            self.assertEqual(info['estado'], self.maquina.estado)

    def test_maquina_dado_linea_activa_e_inactiva_cuando_lista_entonces_no_compartida(self):
        # Solo cuentan líneas ACTIVAS para el flag (filtro Q de la anotación)
        linea_activa = LineaProduccionFactory(area=self.area, maquinas=[self.maquina])
        LineaProduccionFactory(area=self.area, estado='inactiva', maquinas=[self.maquina])
        detalle = self._detalle_por_linea()
        self.assertFalse(detalle[linea_activa.id][self.maquina.id]['compartida'])

    def test_maquina_dado_una_sola_linea_cuando_lista_entonces_no_compartida(self):
        linea = LineaProduccionFactory(area=self.area, maquinas=[self.maquina])
        detalle = self._detalle_por_linea()
        self.assertFalse(detalle[linea.id][self.maquina.id]['compartida'])
