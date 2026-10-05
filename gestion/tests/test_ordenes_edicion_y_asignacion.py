"""
Edición y asignación de órdenes de producción (OWASP A01) y vistas previas de
dosificación y procesos por máquina para el Jefe de Planta.

- La edición genérica de una orden (peso, fórmula, bodega de químicos: dispara
  descargas de químicos del stock) es del Jefe de Planta y los administradores.
- El Jefe de Área asigna máquina y operario de su área con `completar_detalles`
  y puede iniciar la orden en la misma operación. Las referencias son de la
  sede de la orden (y la máquina, de su área); un id ajeno responde como inexistente.

Técnicas ISTQB: partición de equivalencia por rol y por sede/área, transición
de estados (pendiente → en_proceso; finalizada no retrocede) y atomicidad.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import MaquinaProceso
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    CustomUserFactory,
    DetalleFormulaFactory,
    FaseRecetaFactory,
    FormulaColorFactory,
    MaquinaFactory,
    OrdenProduccionFactory,
    ProcesoTintoreriaFactory,
    ProductoFactory,
    SedeFactory,
)


def _campos_con_error(resp):
    return resp.data.get('error', {}).get('fields', resp.data)


class _OrdenesMixin:

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.sede_b = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.otra_area = AreaFactory(sede=self.sede)
        self.area_b = AreaFactory(sede=self.sede_b)
        self.maquina = MaquinaFactory(area=self.area)
        self.maquina_otra_area = MaquinaFactory(area=self.otra_area)
        self.maquina_b = MaquinaFactory(area=self.area_b)
        self.operario = CustomUserFactory(sede=self.sede, area=self.area, groups=['operario'])
        self.operario_b = CustomUserFactory(sede=self.sede_b, groups=['operario'])
        self.bodega = BodegaFactory(sede=self.sede)
        self.bodega_b = BodegaFactory(sede=self.sede_b)
        self.orden = OrdenProduccionFactory(
            sede=self.sede, area=self.area, peso_neto_requerido=Decimal('100.00'),
            producto_entrada=ProductoFactory(sede=self.sede), producto_salida=ProductoFactory(sede=self.sede),
            bodega_entrada=self.bodega, bodega_salida=self.bodega,
        )
        self.url_orden = f'/api/ordenes-produccion/{self.orden.id}/'
        self.url_detalles = f'{self.url_orden}completar_detalles/'

    def _como(self, grupo, area=None, sede=None):
        user = CustomUserFactory(sede=sede or self.sede, area=area, groups=[grupo])
        self.client.force_authenticate(user=user)
        return user


class EdicionOrdenTestCase(_OrdenesMixin, TestCase):

    def test_orden_dado_rol_sin_gestion_cuando_patch_entonces_403_y_no_cambia(self):
        for grupo in ('vendedor', 'despacho', 'operario', 'empaquetado', 'jefe_area'):
            with self.subTest(grupo=grupo):
                self._como(grupo, area=self.area)
                resp = self.client.patch(self.url_orden, {'peso_neto_requerido': '1.00'}, format='json')
                self.assertEqual(resp.status_code, 403)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.peso_neto_requerido, Decimal('100.00'))

    def test_orden_dado_jefe_planta_cuando_patch_entonces_200(self):
        self._como('jefe_planta')
        resp = self.client.patch(self.url_orden, {'peso_neto_requerido': '120.00'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.peso_neto_requerido, Decimal('120.00'))


class CompletarDetallesTestCase(_OrdenesMixin, TestCase):

    def test_completar_dado_jefe_area_y_recursos_de_su_area_cuando_inicia_entonces_asigna_y_queda_en_proceso(self):
        self._como('jefe_area', area=self.area)
        resp = self.client.patch(self.url_detalles, {
            'maquina_asignada': self.maquina.id, 'operario_asignado': self.operario.id, 'iniciar': True,
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.orden.refresh_from_db()
        self.assertEqual((self.orden.maquina_asignada_id, self.orden.operario_asignado_id, self.orden.estado),
                         (self.maquina.id, self.operario.id, 'en_proceso'))

    def test_completar_dado_maquina_de_otra_area_cuando_patch_entonces_400(self):
        self._como('jefe_area', area=self.area)
        resp = self.client.patch(self.url_detalles, {'maquina_asignada': self.maquina_otra_area.id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('maquina_asignada', _campos_con_error(resp))

    def test_completar_dado_referencias_de_otra_sede_cuando_patch_entonces_400_sin_cambios(self):
        self._como('jefe_area', area=self.area)
        casos = {
            'maquina_asignada': self.maquina_b.id,
            'operario_asignado': self.operario_b.id,
            'bodega_quimicos': self.bodega_b.id,
            'bodega_entrada': self.bodega_b.id,
            'producto_salida': ProductoFactory(sede=self.sede_b).id,
            'formula_color': FormulaColorFactory(sede=self.sede_b).id,
        }
        for campo, valor in casos.items():
            with self.subTest(campo=campo):
                resp = self.client.patch(self.url_detalles, {campo: valor}, format='json')
                self.assertEqual(resp.status_code, 400)
                self.assertIn(campo, _campos_con_error(resp))
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.maquina_asignada_id)
        self.assertEqual(self.orden.bodega_entrada_id, self.bodega.id)

    def test_completar_dado_jefe_area_sin_area_cuando_patch_entonces_403(self):
        self._como('jefe_area', area=None)
        resp = self.client.patch(self.url_detalles, {'maquina_asignada': self.maquina.id}, format='json')
        self.assertIn(resp.status_code, (403, 404))
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.maquina_asignada_id)

    def test_completar_dado_id_no_numerico_cuando_patch_entonces_400_sin_detalle_interno(self):
        self._como('jefe_area', area=self.area)
        resp = self.client.patch(self.url_detalles, {'maquina_asignada': 'abc'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn('Traceback', str(resp.data))

    def test_completar_dado_orden_finalizada_cuando_inicia_entonces_400_y_no_asigna(self):
        self.orden.estado = 'finalizada'
        self.orden.save(update_fields=['estado'])
        self._como('jefe_planta')
        resp = self.client.patch(self.url_detalles, {
            'maquina_asignada': self.maquina.id, 'operario_asignado': self.operario.id, 'iniciar': True,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.orden.refresh_from_db()
        self.assertEqual((self.orden.estado, self.orden.maquina_asignada_id), ('finalizada', None))

    def test_completar_dado_fallo_en_descarga_cuando_patch_entonces_500_generico_y_no_asigna(self):
        formula = FormulaColorFactory(sede=self.sede)
        self._como('jefe_planta')
        with patch('gestion.views.production_orden_views.DescargaQuimicosService.descargar_para_op',
                   side_effect=RuntimeError('detalle interno')):
            resp = self.client.patch(self.url_detalles, {
                'formula_color': formula.id, 'bodega_quimicos': self.bodega.id,
                'maquina_asignada': self.maquina.id,
            }, format='json')
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn('detalle interno', str(resp.data))
        self.orden.refresh_from_db()
        self.assertIsNone(self.orden.maquina_asignada_id)


class EliminacionOrdenTestCase(_OrdenesMixin, TestCase):
    """DELETE de una OP: la justificación es obligatoria (ISO 9001), queda en el
    AuditLog (ISO 27001 A.12.4) y un fallo interno no expone su detalle (OWASP A05).
    Técnica: partición de equivalencia sobre la justificación (ausente, solo
    espacios, válida)."""

    def _audit_delete(self):
        from django.contrib.contenttypes.models import ContentType

        from gestion.models import AuditLog, OrdenProduccion
        return AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(OrdenProduccion),
            object_id=self.orden.id, accion='DELETE',
        ).first()

    def test_eliminar_dado_sin_justificacion_cuando_delete_entonces_400_y_la_orden_sigue(self):
        self._como('jefe_planta')
        resp = self.client.delete(self.url_orden, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(type(self.orden).objects.filter(pk=self.orden.pk).exists())

    def test_eliminar_dado_justificacion_solo_espacios_cuando_delete_entonces_400_y_la_orden_sigue(self):
        self._como('jefe_planta')
        resp = self.client.delete(self.url_orden, {'justificacion': '    '}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(type(self.orden).objects.filter(pk=self.orden.pk).exists())

    def test_eliminar_dado_justificacion_valida_cuando_delete_entonces_204_y_audita_la_causa(self):
        self._como('jefe_planta')
        resp = self.client.delete(self.url_orden, {'justificacion': '  Orden duplicada por error  '}, format='json')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(type(self.orden).objects.filter(pk=self.orden.pk).exists())
        log = self._audit_delete()
        self.assertIsNotNone(log)
        self.assertEqual(log.justificacion, 'Orden duplicada por error')

    def test_eliminar_dado_fallo_al_revertir_quimicos_cuando_delete_entonces_500_generico_y_la_orden_sigue(self):
        self.orden.inventario_descontado = True
        self.orden.save(update_fields=['inventario_descontado'])
        self._como('jefe_planta')
        with patch('gestion.views.production_orden_views.DescargaQuimicosService.revertir_descarga_op',
                   side_effect=RuntimeError('detalle interno')):
            resp = self.client.delete(self.url_orden, {'justificacion': 'Orden duplicada'}, format='json')
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn('detalle interno', str(resp.data))
        self.assertTrue(type(self.orden).objects.filter(pk=self.orden.pk).exists())

    def test_eliminar_dado_error_de_negocio_al_revertir_cuando_delete_entonces_400_y_la_orden_sigue(self):
        # Una ValidationError del servicio es error del cliente: se propaga como 400, no como 500 genérico.
        from django.core.exceptions import ValidationError as DjangoValidationError
        self.orden.inventario_descontado = True
        self.orden.save(update_fields=['inventario_descontado'])
        self._como('jefe_planta')
        with patch('gestion.views.production_orden_views.DescargaQuimicosService.revertir_descarga_op',
                   side_effect=DjangoValidationError('La descarga ya fue revertida.')):
            resp = self.client.delete(self.url_orden, {'justificacion': 'Orden duplicada'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('La descarga ya fue revertida.', str(resp.data))
        self.assertTrue(type(self.orden).objects.filter(pk=self.orden.pk).exists())

    def test_editar_dado_orden_sin_descarga_cuando_asigna_formula_y_bodega_entonces_descarga_quimicos(self):
        formula = FormulaColorFactory(sede=self.sede)
        self._como('jefe_planta')
        with patch('gestion.views.production_orden_views.DescargaQuimicosService.descargar_para_op') as descargar:
            resp = self.client.patch(self.url_orden, {
                'formula_color': formula.id, 'bodega_quimicos': self.bodega.id,
            }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        descargar.assert_called_once()
        self.assertEqual(descargar.call_args.args[0].pk, self.orden.pk)


class VistasPreviasJefePlantaTestCase(_OrdenesMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.formula = FormulaColorFactory(sede=self.sede)
        fase = FaseRecetaFactory(formula=self.formula)
        DetalleFormulaFactory(fase=fase, producto=ProductoFactory(sede=self.sede, tipo='quimico'),
                              concentracion_gr_l=Decimal('10.00'), tipo_calculo='gr_l')
        self.orden.formula_color = self.formula
        self.orden.save(update_fields=['formula_color'])

    def test_dosificacion_dado_jefe_planta_cuando_calcula_entonces_200_con_insumos(self):
        self._como('jefe_planta')
        resp = self.client.post(f'{self.url_orden}calcular-dosificacion/', {'litros_bano': '800'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data['insumos']), 1)

    def test_dosificacion_dado_vendedor_cuando_calcula_entonces_403(self):
        self._como('vendedor')
        resp = self.client.post(f'{self.url_orden}calcular-dosificacion/', {'litros_bano': '800'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_procesos_de_maquina_dado_jefe_planta_cuando_consulta_entonces_lista_los_asignados(self):
        proceso = ProcesoTintoreriaFactory(sede=self.sede)
        MaquinaProceso.objects.create(maquina=self.maquina, proceso=proceso)
        self._como('jefe_planta')
        resp = self.client.get(f'/api/maquinas/{self.maquina.id}/procesos/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([p['id'] for p in resp.data], [proceso.id])
