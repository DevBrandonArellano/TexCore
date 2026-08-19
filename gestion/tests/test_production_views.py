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
from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import (
    OrdenProduccion, LoteProduccion, ProcessStep, AreaProcessStep,
    OrdenProduccionSubproceso, EventoEtiqueta,
)
from gestion.views.production_views import LoteProduccionViewSet
from inventory.models import StockBodega
from gestion.tests.factories import (
    SedeFactory, AreaFactory, ProductoFactory, CustomUserFactory, MaquinaFactory,
    OrdenProduccionFactory, LoteProduccionFactory, FormulaColorFactory,
    FaseRecetaFactory, DetalleFormulaFactory, StockBodegaFactory,
    EventoEtiquetaFactory,
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

    def test_maquina_dado_producto_merma_cuando_lista_entonces_retorna_producto_merma_detail(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        merma_prod = ProductoFactory(sede=self.sede, tipo='hilo', codigo='MERMA-COT')
        self.maquina.producto_merma = merma_prod
        self.maquina.save()
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('maquina-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        maquina_data = next(m for m in resp.data if m['id'] == self.maquina.id)
        self.assertIsNotNone(maquina_data.get('producto_merma_detail'))
        self.assertEqual(maquina_data['producto_merma_detail']['codigo'], 'MERMA-COT')


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

    def test_build_zpl_payload_dado_setting_no_definido_cuando_construye_entonces_usa_default_prod(self):
        # Bajo: antes de este fix, qr_data era un f-string hardcodeado a
        # app.texcore.com sin importar el entorno. Con settings.py sin override
        # explícito, debe seguir apuntando a ese mismo dominio por compatibilidad.
        data = LoteProduccionViewSet._build_zpl_payload(self.lote)
        self.assertEqual(data['qr_data'], f'https://app.texcore.com/trazabilidad/{self.lote.codigo_lote}')

    @override_settings(TRAZABILIDAD_BASE_URL='http://staging.texcore.local/trazabilidad')
    def test_build_zpl_payload_dado_setting_override_cuando_construye_entonces_usa_ese_dominio(self):
        # Bajo: TRAZABILIDAD_BASE_URL debe ser configurable por entorno (dev/staging)
        # sin editar código, a diferencia del dominio hardcodeado anterior.
        data = LoteProduccionViewSet._build_zpl_payload(self.lote)
        self.assertEqual(
            data['qr_data'],
            f'http://staging.texcore.local/trazabilidad/{self.lote.codigo_lote}',
        )

    def test_generate_pdf_label_dado_servicio_caido_cuando_get_entonces_503(self):
        # F5: sin microservicio disponible en test, el passthrough de PDF reporta 503
        self.client.force_authenticate(user=self.admin)
        with patch('gestion.views.production_views.PrintingService.generate_label_pdf',
                   return_value=None):
            resp = self.client.get(reverse('loteproduccion-generate-pdf-label', args=[self.lote.id]))
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_generate_pdf_label_dado_servicio_caido_cuando_get_entonces_error_code_distinguible(self):
        # Bajo: a diferencia de generate_zpl (fallback local propio), el PDF no
        # tiene fallback local (WeasyPrint vive deliberadamente aislado en el
        # microservicio, ver printing_service/README.md#Arquitectura). El
        # frontend ya cubre esta caída con su propio fallback a portapapeles
        # (frontend/src/lib/printing.ts:printLabel). Aquí solo se asegura que
        # el 503 sea distinguible de otros 503 para monitoreo/alertas.
        self.client.force_authenticate(user=self.admin)
        with patch('gestion.views.production_views.PrintingService.generate_label_pdf',
                   return_value=None):
            resp = self.client.get(reverse('loteproduccion-generate-pdf-label', args=[self.lote.id]))
        self.assertEqual(resp.data['error']['code'], 'PRINTING_SERVICE_UNAVAILABLE')

    def test_generate_pdf_label_dado_servicio_disponible_cuando_get_entonces_200_pdf(self):
        # F5: microservicio disponible (mockeado) -> passthrough retorna el PDF binario
        self.client.force_authenticate(user=self.admin)
        with patch('gestion.views.production_views.PrintingService.generate_label_pdf',
                   return_value=b'%PDF-1.4 fake'):
            resp = self.client.get(reverse('loteproduccion-generate-pdf-label', args=[self.lote.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertEqual(resp.content, b'%PDF-1.4 fake')

    def test_generate_pdf_label_dado_sin_query_params_cuando_get_entonces_payload_sin_tipo_evento(self):
        # Sin ?tipo_evento=..., el PDF debe seguir comportándose como ORIGINAL
        # (regresión: el fallback PDF de reimpresión/reetiquetado antes SIEMPRE
        # regeneraba una etiqueta ORIGINAL plana, perdiendo el sello de gobernanza).
        self.client.force_authenticate(user=self.admin)
        with patch('gestion.views.production_views.PrintingService.generate_label_pdf',
                   return_value=b'%PDF-1.4 fake') as mock_pdf:
            self.client.get(reverse('loteproduccion-generate-pdf-label', args=[self.lote.id]))
        payload = mock_pdf.call_args[0][0]
        self.assertNotIn('tipo_evento', payload)
        self.assertNotIn('version', payload)

    def test_generate_pdf_label_dado_tipo_evento_reimpresion_cuando_get_entonces_propaga_contexto(self):
        self.client.force_authenticate(user=self.admin)
        with patch('gestion.views.production_views.PrintingService.generate_label_pdf',
                   return_value=b'%PDF-1.4 fake') as mock_pdf:
            resp = self.client.get(
                reverse('loteproduccion-generate-pdf-label', args=[self.lote.id]),
                {'tipo_evento': 'REIMPRESION', 'version': '2'},
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payload = mock_pdf.call_args[0][0]
        self.assertEqual(payload['tipo_evento'], 'REIMPRESION')
        self.assertEqual(payload['version'], 2)
        self.assertEqual(payload['usuario'], self.admin.username)

    def test_generate_pdf_label_dado_tipo_evento_reetiquetado_cuando_get_entonces_propaga_contexto(self):
        self.client.force_authenticate(user=self.admin)
        with patch('gestion.views.production_views.PrintingService.generate_label_pdf',
                   return_value=b'%PDF-1.4 fake') as mock_pdf:
            self.client.get(
                reverse('loteproduccion-generate-pdf-label', args=[self.lote.id]),
                {'tipo_evento': 'REETIQUETADO', 'version': '3'},
            )
        payload = mock_pdf.call_args[0][0]
        self.assertEqual(payload['tipo_evento'], 'REETIQUETADO')
        self.assertEqual(payload['version'], 3)

    def test_generate_pdf_label_dado_tipo_evento_no_reconocido_cuando_get_entonces_lo_ignora(self):
        # EP: un valor fuera de {REIMPRESION, REETIQUETADO} no debe filtrarse al payload.
        self.client.force_authenticate(user=self.admin)
        with patch('gestion.views.production_views.PrintingService.generate_label_pdf',
                   return_value=b'%PDF-1.4 fake') as mock_pdf:
            resp = self.client.get(
                reverse('loteproduccion-generate-pdf-label', args=[self.lote.id]),
                {'tipo_evento': 'ORIGINAL'},
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payload = mock_pdf.call_args[0][0]
        self.assertNotIn('tipo_evento', payload)

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

    def test_reimprimir_dado_sin_motivo_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(reverse('loteproduccion-reimprimir', args=[self.lote.id]), {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EventoEtiqueta.objects.filter(lote=self.lote).count(), 0)

    def test_reimprimir_dado_motivo_invalido_cuando_post_entonces_400(self):
        # motivo es un campo de catálogo (EventoEtiqueta.MOTIVO_CHOICES); un valor
        # fuera del catálogo antes llegaba a SQL Server y producía un 500 crudo
        # por truncamiento de columna en vez de un 400 controlado.
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse('loteproduccion-reimprimir', args=[self.lote.id]),
            {'motivo': 'Texto libre que no está en el catálogo de motivos'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EventoEtiqueta.objects.filter(lote=self.lote).count(), 0)

    def test_reimprimir_dado_motivo_cuando_post_entonces_crea_evento_y_zpl(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse('loteproduccion-reimprimir', args=[self.lote.id]),
            {'motivo': 'DANIADA', 'detalle_motivo': 'Etiqueta dañada en despacho'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")
        self.assertIn('zpl', resp.data)
        self.assertEqual(resp.data['evento']['tipo_evento'], 'REIMPRESION')
        self.assertEqual(resp.data['evento']['version'], 1)
        evento = EventoEtiqueta.objects.get(lote=self.lote, tipo_evento='REIMPRESION')
        self.assertEqual(evento.motivo, 'DANIADA')
        self.assertEqual(evento.usuario, self.admin)

    def test_reimprimir_dado_dos_veces_cuando_post_entonces_secuencia_incrementa_y_version_igual(self):
        self.client.force_authenticate(user=self.admin)
        self.client.post(
            reverse('loteproduccion-reimprimir', args=[self.lote.id]),
            {'motivo': 'DANIADA'}, format='json'
        )
        self.client.post(
            reverse('loteproduccion-reimprimir', args=[self.lote.id]),
            {'motivo': 'PERDIDA'}, format='json'
        )
        eventos = list(EventoEtiqueta.objects.filter(lote=self.lote).order_by('secuencia'))
        self.assertEqual([e.secuencia for e in eventos], [1, 2])
        self.assertEqual([e.version for e in eventos], [1, 1])

    def test_etiquetas_dado_lote_con_reimpresion_cuando_get_entonces_historial(self):
        self.client.force_authenticate(user=self.admin)
        self.client.post(
            reverse('loteproduccion-reimprimir', args=[self.lote.id]),
            {'motivo': 'ATASCO'}, format='json'
        )
        resp = self.client.get(reverse('loteproduccion-etiquetas', args=[self.lote.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['tipo_evento'], 'REIMPRESION')
        self.assertEqual(resp.data[0]['motivo'], 'ATASCO')


class LoteProduccionZplFallbackSanitizationTestCase(TestCase):
    """
    Medio: _build_zpl_fallback interpola producto_desc/empresa (texto libre,
    editable por un admin de catálogo) directo en un f-string ZPL sin ningún
    escapado. Un '^' (prefijo de comando de formato) o '~' (prefijo de
    comando de control) sin sanear rompe el stream que se envía a la
    impresora térmica Zebra. No requiere DB: _build_zpl_fallback es un
    @staticmethod puro sobre un dict.
    """

    def _make_data(self, **overrides):
        data = {
            'empresa': 'Sede Principal',
            'producto_desc': 'Hilo Nylon 40/1',
            'lote_codigo': 'L-2026-001',
            'peso_neto': 45.5,
            'peso_bruto': 48.0,
            'tara': 2.5,
            'cantidad_metros': None,
            'unidad': 'kg',
        }
        data.update(overrides)
        return data

    def test_build_zpl_fallback_dado_producto_con_caret_cuando_genera_entonces_lo_elimina(self):
        zpl = LoteProduccionViewSet._build_zpl_fallback(self._make_data(producto_desc='Hilo^Malicioso'))
        self.assertNotIn('Hilo^Malicioso', zpl)
        self.assertIn('HiloMalicioso', zpl)

    def test_build_zpl_fallback_dado_empresa_con_tilde_cuando_genera_entonces_lo_elimina(self):
        zpl = LoteProduccionViewSet._build_zpl_fallback(self._make_data(empresa='Sede~Norte'))
        self.assertNotIn('Sede~Norte', zpl)
        self.assertIn('SedeNorte', zpl)

    def test_build_zpl_fallback_dado_lote_codigo_con_caret_cuando_genera_entonces_lo_elimina(self):
        # lote_codigo también alimenta el símbolo de barras (^BCN...^FD{lote_codigo}^FS).
        zpl = LoteProduccionViewSet._build_zpl_fallback(self._make_data(lote_codigo='L^2026^001'))
        self.assertNotIn('L^2026^001', zpl)
        self.assertIn('L2026001', zpl)

    def test_build_zpl_fallback_dado_texto_normal_cuando_genera_entonces_no_cambia(self):
        zpl = LoteProduccionViewSet._build_zpl_fallback(self._make_data())
        self.assertIn('Hilo Nylon 40/1', zpl)
        self.assertIn('Sede Principal', zpl)


class LoteProduccionBusquedaTestCase(TestCase):
    """F3: filtros de búsqueda dedicados (fecha, turno, código, máquina, calidad) + paginación opt-in."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.maquina_a = MaquinaFactory(area=self.area)
        self.maquina_b = MaquinaFactory(area=self.area)

        fecha_antigua = datetime(2026, 5, 1, 8, 0)
        fecha_reciente = datetime(2026, 6, 1, 8, 0)
        self.lote_antiguo = LoteProduccionFactory(
            orden_produccion=self.op, codigo_lote='OP-BUSQ-VIEJO', turno='Dia',
            maquina=self.maquina_a, clasificacion_calidad='primera',
            hora_inicio=fecha_antigua, hora_final=fecha_antigua + timedelta(hours=8),
        )
        self.lote_reciente = LoteProduccionFactory(
            orden_produccion=self.op, codigo_lote='OP-BUSQ-NUEVO', turno='Noche',
            maquina=self.maquina_b, clasificacion_calidad='segunda',
            hora_inicio=fecha_reciente, hora_final=fecha_reciente + timedelta(hours=8),
        )
        self.client.force_authenticate(user=self.admin)

    def test_busqueda_dado_rango_fechas_cuando_lista_entonces_filtra(self):
        resp = self.client.get(reverse('loteproduccion-list'), {
            'fecha_desde': '2026-04-30', 'fecha_hasta': '2026-05-02',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        codigos = [lote['codigo_lote'] for lote in resp.data]
        self.assertIn('OP-BUSQ-VIEJO', codigos)
        self.assertNotIn('OP-BUSQ-NUEVO', codigos)

    def test_busqueda_dado_fecha_invalida_cuando_lista_entonces_400(self):
        resp = self.client.get(reverse('loteproduccion-list'), {'fecha_desde': 'no-es-fecha'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_busqueda_dado_fecha_desde_mayor_a_hasta_cuando_lista_entonces_400(self):
        resp = self.client.get(reverse('loteproduccion-list'), {
            'fecha_desde': '2026-06-10', 'fecha_hasta': '2026-06-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_busqueda_dado_turno_cuando_lista_entonces_filtra(self):
        resp = self.client.get(reverse('loteproduccion-list'), {'turno': 'Noche'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        codigos = [lote['codigo_lote'] for lote in resp.data]
        self.assertEqual(codigos, ['OP-BUSQ-NUEVO'])

    def test_busqueda_dado_codigo_lote_parcial_cuando_lista_entonces_filtra(self):
        resp = self.client.get(reverse('loteproduccion-list'), {'codigo_lote': 'nuevo'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['codigo_lote'], 'OP-BUSQ-NUEVO')

    def test_busqueda_dado_maquina_cuando_lista_entonces_filtra(self):
        resp = self.client.get(reverse('loteproduccion-list'), {'maquina': self.maquina_a.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        codigos = [lote['codigo_lote'] for lote in resp.data]
        self.assertEqual(codigos, ['OP-BUSQ-VIEJO'])

    def test_busqueda_dado_calidad_cuando_lista_entonces_filtra(self):
        resp = self.client.get(reverse('loteproduccion-list'), {'clasificacion_calidad': 'segunda'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        codigos = [lote['codigo_lote'] for lote in resp.data]
        self.assertEqual(codigos, ['OP-BUSQ-NUEVO'])

    def test_busqueda_dado_sin_page_cuando_lista_entonces_respuesta_es_lista_simple(self):
        # Compatibilidad: consumidores existentes (Historial Reciente) esperan un array plano.
        resp = self.client.get(reverse('loteproduccion-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_busqueda_dado_page_cuando_lista_entonces_respuesta_paginada(self):
        resp = self.client.get(reverse('loteproduccion-list'), {'page': 1, 'page_size': 1})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)
        self.assertIn('count', resp.data)
        self.assertEqual(resp.data['count'], 2)
        self.assertEqual(len(resp.data['results']), 1)


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

    def test_registrar_lote_dado_sin_hora_final_cuando_post_entonces_400(self):
        # LoteProduccion.hora_final es NOT NULL en el modelo; antes el serializer
        # lo trataba como opcional y el INSERT fallaba con IntegrityError, que el
        # view reportaba (incorrectamente) como "código de lote duplicado".
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(
            reverse('registrar-lote', args=[self.op.id]),
            {'peso_neto_producido': '50.00', 'hora_inicio': '2026-08-18T10:00:00Z'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hora_final', resp.data)

    def test_registrar_lote_dado_sin_hora_inicio_cuando_post_entonces_400(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(
            reverse('registrar-lote', args=[self.op.id]),
            {'peso_neto_producido': '50.00', 'hora_final': '2026-08-18T11:00:00Z'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hora_inicio', resp.data)

    def test_registrar_lote_dado_ambas_horas_cuando_post_entonces_201(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        StockBodegaFactory(bodega=self.op.bodega_entrada, producto=self.op.producto_entrada,
                           lote=None, cantidad=Decimal('1000.00'))
        resp = self.client.post(
            reverse('registrar-lote', args=[self.op.id]),
            {'peso_neto_producido': '50.00', 'hora_inicio': '2026-08-18T10:00:00Z',
             'hora_final': '2026-08-18T11:00:00Z'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, f"Error: {resp.data}")

    def test_registrar_lote_dado_unidades_personalizadas_cuando_post_entonces_mantiene_unidades(self):
        operario = CustomUserFactory(sede=self.sede, groups=['operario'])
        lote = LoteProduccionFactory(
            orden_produccion=self.op, operario=operario, unidades_empaque=12, presentacion='cono')
        lote.full_clean()
        self.assertEqual(lote.unidades_empaque, 12)

    def test_registrar_lote_dado_peso_merma_excede_orden_cuando_post_entonces_400(self):
        self.op.peso_neto_requerido = Decimal('100.00')
        self.op.save()
        operario = CustomUserFactory(sede=self.sede, groups=['operario'])
        lote = LoteProduccion(
            orden_produccion=self.op, operario=operario, peso_neto_producido=Decimal('50.00'),
            peso_merma=Decimal('150.00'), unidades_empaque=1)
        with self.assertRaises(Exception):
            lote.clean()


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


class SubprocesoQuerysetScopingTestCase(TestCase):
    """Tabla de decisión RBAC: scoping de OrdenProduccionSubprocesoViewSet.get_queryset."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.otra_area = AreaFactory(sede=self.sede)
        proceso = ProcessStep.objects.create(name='Tintura-Scoping')
        op_mia = OrdenProduccionFactory(sede=self.sede, area=self.area)
        op_ajena = OrdenProduccionFactory(sede=self.sede, area=self.otra_area)
        self.sp_mio = OrdenProduccionSubproceso.objects.create(
            orden_produccion=op_mia,
            area_proceso=AreaProcessStep.objects.create(area=self.area, proceso=proceso, orden=1),
        )
        self.sp_ajeno = OrdenProduccionSubproceso.objects.create(
            orden_produccion=op_ajena,
            area_proceso=AreaProcessStep.objects.create(area=self.otra_area, proceso=proceso, orden=1),
        )

    def _listar(self, user):
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('orden-produccion-subproceso-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        return [s['id'] for s in results]

    def test_subprocesos_dado_admin_sistemas_no_superuser_cuando_lista_entonces_ve_todos(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        ids = self._listar(admin)
        self.assertCountEqual(ids, [self.sp_mio.id, self.sp_ajeno.id])

    def test_subprocesos_dado_jefe_planta_cuando_lista_entonces_ve_todos(self):
        jefe_planta = CustomUserFactory(sede=self.sede, groups=['jefe_planta'])
        ids = self._listar(jefe_planta)
        self.assertCountEqual(ids, [self.sp_mio.id, self.sp_ajeno.id])

    def test_subprocesos_dado_jefe_area_cuando_lista_entonces_solo_su_area(self):
        jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        ids = self._listar(jefe)
        self.assertEqual(ids, [self.sp_mio.id])

    def test_subprocesos_dado_jefe_area_sin_area_cuando_lista_entonces_vacio(self):
        jefe = CustomUserFactory(sede=self.sede, area=None, groups=['jefe_area'])
        self.assertEqual(self._listar(jefe), [])


class LoteProduccionReetiquetarTestCase(TestCase):
    """F4: reetiquetado con cambio de datos — RBAC supervisor, versionado, ajuste de stock."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.operario = CustomUserFactory(sede=self.sede, area=self.area, groups=['operario'])
        self.op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.lote = LoteProduccionFactory(orden_produccion=self.op, peso_neto_producido=Decimal('95.000'))
        EventoEtiquetaFactory(lote=self.lote, tipo_evento='ORIGINAL', secuencia=1, version=1)

    def test_reetiquetar_dado_operario_cuando_post_entonces_403(self):
        self.client.force_authenticate(user=self.operario)
        resp = self.client.post(
            reverse('loteproduccion-reetiquetar', args=[self.lote.id]),
            {'motivo': 'RECLASIFICACION', 'cambios': {'clasificacion_calidad': 'segunda'}}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_reetiquetar_dado_sin_motivo_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('loteproduccion-reetiquetar', args=[self.lote.id]),
            {'cambios': {'clasificacion_calidad': 'segunda'}}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reetiquetar_dado_motivo_invalido_cuando_post_entonces_400(self):
        # motivo es un campo de catálogo (EventoEtiqueta.MOTIVO_CHOICES); un valor
        # fuera del catálogo antes llegaba a SQL Server y producía un 500 crudo.
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('loteproduccion-reetiquetar', args=[self.lote.id]),
            {'motivo': 'Texto libre que no está en el catálogo de motivos',
             'cambios': {'clasificacion_calidad': 'segunda'}}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.lote.refresh_from_db()
        self.assertNotEqual(self.lote.clasificacion_calidad, 'segunda')

    def test_reetiquetar_dado_sin_cambios_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('loteproduccion-reetiquetar', args=[self.lote.id]),
            {'motivo': 'RECLASIFICACION'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reetiquetar_dado_campo_no_permitido_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('loteproduccion-reetiquetar', args=[self.lote.id]),
            {'motivo': 'OTRO', 'cambios': {'codigo_lote': 'HACKEADO'}}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.lote.refresh_from_db()
        self.assertNotEqual(self.lote.codigo_lote, 'HACKEADO')

    def test_reetiquetar_dado_calidad_cuando_post_entonces_versiona_y_anula_previa(self):
        self.client.force_authenticate(user=self.jefe)
        codigo_original = self.lote.codigo_lote
        resp = self.client.post(
            reverse('loteproduccion-reetiquetar', args=[self.lote.id]),
            {'motivo': 'RECLASIFICACION', 'detalle_motivo': 'Reclasificado tras inspección',
             'cambios': {'clasificacion_calidad': 'segunda'}}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")
        self.assertEqual(resp.data['evento']['tipo_evento'], 'REETIQUETADO')
        self.assertEqual(resp.data['evento']['version'], 2)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.clasificacion_calidad, 'segunda')
        self.assertEqual(self.lote.codigo_lote, codigo_original)

        eventos = list(EventoEtiqueta.objects.filter(lote=self.lote).order_by('secuencia'))
        self.assertEqual(len(eventos), 2)
        self.assertTrue(eventos[0].anulada)
        self.assertFalse(eventos[1].anulada)
        self.assertEqual(eventos[1].anula_a_id, eventos[0].id)

    def test_reetiquetar_dado_cambio_peso_cuando_post_entonces_ajusta_stock(self):
        StockBodegaFactory(bodega=self.op.bodega_salida, producto=self.op.producto_salida,
                           lote=self.lote, cantidad=Decimal('95.00'))
        StockBodegaFactory(bodega=self.op.bodega_entrada, producto=self.op.producto_entrada,
                           lote=None, cantidad=Decimal('1000.00'))
        self.client.force_authenticate(user=self.jefe)
        resp = self.client.post(
            reverse('loteproduccion-reetiquetar', args=[self.lote.id]),
            {'motivo': 'CORRECCION_PESO', 'cambios': {'peso_neto_producido': '100.000'}}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")
        salida = StockBodega.objects.get(bodega=self.op.bodega_salida, producto=self.op.producto_salida, lote=self.lote)
        entrada = StockBodega.objects.get(bodega=self.op.bodega_entrada, producto=self.op.producto_entrada, lote=None)
        self.assertEqual(salida.cantidad, Decimal('100.00'))
        self.assertEqual(entrada.cantidad, Decimal('995.00'))
