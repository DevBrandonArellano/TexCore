"""
Pruebas de gestion/views/production_views.py.

Cubre MaquinaViewSet, OrdenProduccionViewSet, LoteProduccionViewSet,
ComponenteMezclaOPViewSet, RegistrarLoteProduccionView y la máquina de
estados de OrdenProduccionSubprocesoViewSet.

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: RBAC por rol y área, ramas de validación.
- Prueba de transición de estados (STT): subprocesos pendiente→en_progreso→
  completado/pausado/rechazado; ajuste de stock al corregir/rechazar lotes.
- Análisis de valores límite (BVA): stock insuficiente en corrección de lote.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import (
    OrdenProduccion, LoteProduccion, ProcessStep, AreaProcessStep,
    OrdenProduccionSubproceso,
)
from inventory.models import StockBodega
from gestion.tests.factories import (
    SedeFactory, AreaFactory, ProductoFactory, CustomUserFactory, MaquinaFactory,
    OrdenProduccionFactory, LoteProduccionFactory, FormulaColorFactory,
    FaseRecetaFactory, DetalleFormulaFactory, StockBodegaFactory,
)


class MaquinaViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.otra_area = AreaFactory(sede=self.sede)
        self.maquina = MaquinaFactory(area=self.area, capacidad_maxima=Decimal('500.00'))
        self.maquina_otra = MaquinaFactory(area=self.otra_area)

    def test_maquina_dado_jefe_area_cuando_lista_entonces_solo_su_area(self):
        # Caja blanca: jefe_area ve solo máquinas de su área
        jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe)
        resp = self.client.get(reverse('maquina-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['id'], self.maquina.id)

    def test_maquina_dado_jefe_area_sin_area_cuando_lista_entonces_vacio(self):
        jefe = CustomUserFactory(sede=self.sede, area=None, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe)
        resp = self.client.get(reverse('maquina-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_maquina_dado_existente_cuando_eficiencia_entonces_200(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('maquina-eficiencia', args=[self.maquina.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('eficiencia_porcentaje', resp.data)
        self.assertEqual(resp.data['capacidad_maxima'], Decimal('500.00'))


class OrdenProduccionViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.otra_area = AreaFactory(sede=self.sede)
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])

    def test_op_dado_jefe_area_cuando_lista_entonces_filtra_por_area(self):
        op_mia = OrdenProduccionFactory(sede=self.sede, area=self.area)
        OrdenProduccionFactory(sede=self.sede, area=self.otra_area)
        jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe)
        resp = self.client.get(reverse('ordenproduccion-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        ids = [o['id'] for o in results]
        self.assertEqual(ids, [op_mia.id])

    def test_op_dado_operario_cuando_lista_entonces_solo_asignadas(self):
        operario = CustomUserFactory(sede=self.sede, groups=['operario'])
        op_asignada = OrdenProduccionFactory(sede=self.sede, area=self.area, operario_asignado=operario)
        OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('ordenproduccion-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        ids = [o['id'] for o in results]
        self.assertEqual(ids, [op_asignada.id])

    def test_completar_detalles_dado_usuario_de_otra_area_cuando_patch_entonces_403(self):
        # Caja blanca (L186-190): un usuario con área asignada distinta a la de la OP
        # es rechazado. Se usa jefe_planta (no filtra queryset por área, sí ve la OP)
        # con área distinta para alcanzar la guarda — un jefe_area nunca vería OPs ajenas.
        op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        usuario_otra = CustomUserFactory(sede=self.sede, area=self.otra_area, groups=['jefe_planta'])
        self.client.force_authenticate(user=usuario_otra)
        resp = self.client.patch(
            reverse('ordenproduccion-completar-detalles', args=[op.id]),
            {'maquina_asignada': MaquinaFactory(area=self.otra_area).id}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_completar_detalles_dado_jefe_correcto_cuando_asigna_maquina_entonces_200(self):
        # FK asignada por id (corrección bug Fase 14)
        op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        maquina = MaquinaFactory(area=self.area)
        jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe)
        resp = self.client.patch(
            reverse('ordenproduccion-completar-detalles', args=[op.id]),
            {'maquina_asignada': maquina.id}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")
        op.refresh_from_db()
        self.assertEqual(op.maquina_asignada_id, maquina.id)

    def test_op_dado_inventario_descontado_sin_justificacion_cuando_patch_entonces_400(self):
        # perform_update: justificación obligatoria si ya hay descarga
        op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        OrdenProduccion.objects.filter(id=op.id).update(inventario_descontado=True)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            reverse('ordenproduccion-detail', args=[op.id]),
            {'observaciones': 'cambio'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('justificacion', resp.data.get('error', {}).get('fields', resp.data))

    def test_op_dado_sin_justificacion_cuando_destroy_entonces_400(self):
        op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(reverse('ordenproduccion-detail', args=[op.id]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_op_dado_justificacion_cuando_destroy_entonces_204(self):
        op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(
            reverse('ordenproduccion-detail', args=[op.id]),
            {'justificacion': 'OP creada por error'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(OrdenProduccion.objects.filter(id=op.id).exists())

    def test_requisitos_materiales_dado_op_con_formula_cuando_get_entonces_base_y_quimicos(self):
        # Cubre la corrección del bug producto_entrada (antes orden.producto -> 500)
        formula = FormulaColorFactory(sede=self.sede)
        fase = FaseRecetaFactory(formula=formula)
        quimico = ProductoFactory(tipo='quimico', sede=self.sede)
        DetalleFormulaFactory(fase=fase, producto=quimico, concentracion_gr_l=Decimal('10.00'), tipo_calculo='gr_l')
        op = OrdenProduccionFactory(sede=self.sede, area=self.area, formula_color=formula)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('ordenproduccion-requisitos-materiales', args=[op.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 1 base (producto_entrada) + 1 químico
        self.assertEqual(len(resp.data['requisitos']), 2)
        self.assertTrue(resp.data['requisitos'][0]['es_base'])

    def test_stock_quimicos_dado_tintorero_cuando_get_entonces_200(self):
        tintorero = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.client.force_authenticate(user=tintorero)
        resp = self.client.get(reverse('ordenproduccion-stock-quimicos'), {'sede_id': self.sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_stock_quimicos_dado_operario_cuando_get_entonces_403(self):
        operario = CustomUserFactory(sede=self.sede, groups=['operario'])
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('ordenproduccion-stock-quimicos'), {'sede_id': self.sede.id})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_stock_quimicos_dado_sin_sede_cuando_get_entonces_400(self):
        tintorero = CustomUserFactory(sede=None, groups=['tintorero'])
        self.client.force_authenticate(user=tintorero)
        resp = self.client.get(reverse('ordenproduccion-stock-quimicos'))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cambiar_estado_dado_estado_valido_cuando_patch_entonces_200(self):
        op = OrdenProduccionFactory(sede=self.sede, area=self.area, estado='pendiente')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            reverse('ordenproduccion-cambiar-estado', args=[op.id]),
            {'estado': 'en_proceso'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['estado'], 'en_proceso')


class LoteProduccionViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.lote = LoteProduccionFactory(orden_produccion=self.op, peso_neto_producido=Decimal('95.000'))

    def test_lote_dado_filtro_orden_cuando_lista_entonces_filtra(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('loteproduccion-list'), {'orden_produccion': self.op.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_genealogia_dado_lote_cuando_get_entonces_trazabilidad(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('loteproduccion-genealogia', args=[self.lote.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['lote_codigo'], self.lote.codigo_lote)
        self.assertIn('quimicos_consumidos', resp.data)

    def test_generate_zpl_dado_servicio_caido_cuando_get_entonces_fallback_local(self):
        # PrintingService no disponible en test -> ZPL fallback local
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('loteproduccion-generate-zpl', args=[self.lote.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('zpl', resp.data)

    def test_obtener_costo_dado_lote_cuando_get_entonces_200(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('loteproduccion-obtener-costo', args=[self.lote.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_perform_update_dado_aumento_peso_cuando_patch_entonces_ajusta_stock(self):
        # STT/caja blanca: corrección de lote ajusta stock salida (+) y entrada (-)
        StockBodegaFactory(bodega=self.op.bodega_salida, producto=self.op.producto_salida,
                           lote=self.lote, cantidad=Decimal('95.00'))
        StockBodegaFactory(bodega=self.op.bodega_entrada, producto=self.op.producto_entrada,
                           lote=None, cantidad=Decimal('1000.00'))
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            reverse('loteproduccion-detail', args=[self.lote.id]),
            {'peso_neto_producido': '100.000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")
        salida = StockBodega.objects.get(bodega=self.op.bodega_salida, producto=self.op.producto_salida, lote=self.lote)
        entrada = StockBodega.objects.get(bodega=self.op.bodega_entrada, producto=self.op.producto_entrada, lote=None)
        self.assertEqual(salida.cantidad, Decimal('100.00'))
        self.assertEqual(entrada.cantidad, Decimal('995.00'))

    def test_perform_update_dado_materia_prima_insuficiente_cuando_patch_entonces_400(self):
        # BVA: aumento de peso sin stock de MP suficiente
        StockBodegaFactory(bodega=self.op.bodega_salida, producto=self.op.producto_salida,
                           lote=self.lote, cantidad=Decimal('95.00'))
        StockBodegaFactory(bodega=self.op.bodega_entrada, producto=self.op.producto_entrada,
                           lote=None, cantidad=Decimal('1.00'))
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            reverse('loteproduccion-detail', args=[self.lote.id]),
            {'peso_neto_producido': '200.000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechazar_dado_sin_justificacion_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(reverse('loteproduccion-rechazar', args=[self.lote.id]), {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechazar_dado_justificacion_cuando_post_entonces_revierte_y_elimina(self):
        # STT: rechazo revierte salida a 0, devuelve MP y elimina el lote
        StockBodegaFactory(bodega=self.op.bodega_salida, producto=self.op.producto_salida,
                           lote=self.lote, cantidad=Decimal('95.00'))
        entrada = StockBodegaFactory(bodega=self.op.bodega_entrada, producto=self.op.producto_entrada,
                                     lote=None, cantidad=Decimal('100.00'))
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse('loteproduccion-rechazar', args=[self.lote.id]),
            {'justificacion': 'Lote defectuoso'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")
        self.assertFalse(LoteProduccion.objects.filter(id=self.lote.id).exists())
        entrada.refresh_from_db()
        self.assertEqual(entrada.cantidad, Decimal('195.00'))


class RegistrarLoteProduccionViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.otra_area = AreaFactory(sede=self.sede)
        self.op = OrdenProduccionFactory(sede=self.sede, area=self.area)

    def test_registrar_lote_dado_jefe_de_otra_area_cuando_post_entonces_403(self):
        jefe_otra = CustomUserFactory(sede=self.sede, area=self.otra_area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe_otra)
        resp = self.client.post(
            reverse('registrar-lote', args=[self.op.id]),
            {'peso_neto_producido': '50.000'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_registrar_lote_dado_payload_invalido_cuando_post_entonces_400(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(
            reverse('registrar-lote', args=[self.op.id]),
            {'peso_neto_producido': '-5.000'}, format='json'  # negativo -> inválido
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class SubprocesoStateMachineTestCase(TestCase):
    """STT: máquina de estados de OrdenProduccionSubproceso."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        # superuser para satisfacer DjangoModelPermissions
        self.admin = CustomUserFactory(sede=self.sede, is_superuser=True, is_staff=True)
        self.client.force_authenticate(user=self.admin)
        self.op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        proceso = ProcessStep.objects.create(name='Tintura')
        self.area_proceso = AreaProcessStep.objects.create(area=self.area, proceso=proceso, orden=1)

    def _subproceso(self, estado='pendiente'):
        return OrdenProduccionSubproceso.objects.create(
            orden_produccion=self.op, area_proceso=self.area_proceso, estado=estado
        )

    def test_iniciar_dado_pendiente_cuando_patch_entonces_en_progreso(self):
        sp = self._subproceso('pendiente')
        resp = self.client.patch(reverse('orden-produccion-subproceso-iniciar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['estado'], 'en_progreso')

    def test_iniciar_dado_no_pendiente_cuando_patch_entonces_400(self):
        # Transición inválida: solo se inicia desde pendiente
        sp = self._subproceso('en_progreso')
        resp = self.client.patch(reverse('orden-produccion-subproceso-iniciar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_completar_dado_en_progreso_cuando_patch_entonces_completado(self):
        sp = self._subproceso('en_progreso')
        resp = self.client.patch(reverse('orden-produccion-subproceso-completar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['estado'], 'completado')

    def test_completar_dado_pendiente_cuando_patch_entonces_400(self):
        sp = self._subproceso('pendiente')
        resp = self.client.patch(reverse('orden-produccion-subproceso-completar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pausar_dado_en_progreso_cuando_patch_entonces_pausado(self):
        sp = self._subproceso('en_progreso')
        resp = self.client.patch(reverse('orden-produccion-subproceso-pausar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['estado'], 'pausado')

    def test_rechazar_dado_completado_cuando_patch_entonces_400(self):
        # No se puede rechazar un subproceso completado
        sp = self._subproceso('completado')
        resp = self.client.patch(reverse('orden-produccion-subproceso-rechazar-subproceso', args=[sp.id]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechazar_dado_pendiente_cuando_patch_entonces_rechazado(self):
        sp = self._subproceso('pendiente')
        resp = self.client.patch(
            reverse('orden-produccion-subproceso-rechazar-subproceso', args=[sp.id]),
            {'motivo_rechazo': 'Material no disponible'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['estado'], 'rechazado')
