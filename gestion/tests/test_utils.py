"""
Pruebas de gestion/utils.py — PrintingService (proxy HTTP a printing_service).
PaymentReconciler ya se ejercita indirectamente en test_anticipos_pagos_parciales_p1.py
y test_pago_seguridad_p0.py; este archivo cubre las ramas propias de PrintingService.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): respuesta 200 / error HTTP / excepción de red.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from gestion.utils import PrintingService


class PrintingServiceNotaVentaPdfTestCase(TestCase):
    @patch('gestion.utils.requests.post')
    def test_generate_pdf_dado_respuesta_200_cuando_llama_entonces_retorna_contenido(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, content=b'%PDF-contenido')
        resultado = PrintingService.generate_nota_venta_pdf({'id': 1})
        self.assertEqual(resultado, b'%PDF-contenido')

    @patch('gestion.utils.requests.post')
    def test_generate_pdf_dado_respuesta_error_cuando_llama_entonces_none(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, text='error interno')
        resultado = PrintingService.generate_nota_venta_pdf({'id': 1})
        self.assertIsNone(resultado)

    @patch('gestion.utils.requests.post', side_effect=ConnectionError('servicio caído'))
    def test_generate_pdf_dado_excepcion_de_red_cuando_llama_entonces_none(self, mock_post):
        resultado = PrintingService.generate_nota_venta_pdf({'id': 1})
        self.assertIsNone(resultado)


class PrintingServiceZplTestCase(TestCase):
    @patch('gestion.utils.requests.post')
    def test_generate_zpl_dado_respuesta_200_cuando_llama_entonces_retorna_texto(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text='^XA...^XZ')
        resultado = PrintingService.generate_zpl_label({'lote_codigo': 'L1'})
        self.assertEqual(resultado, '^XA...^XZ')

    @patch('gestion.utils.requests.post')
    def test_generate_zpl_dado_respuesta_error_cuando_llama_entonces_none(self, mock_post):
        mock_post.return_value = MagicMock(status_code=404, text='not found')
        resultado = PrintingService.generate_zpl_label({'lote_codigo': 'L1'})
        self.assertIsNone(resultado)

    @patch('gestion.utils.requests.post', side_effect=TimeoutError('timeout'))
    def test_generate_zpl_dado_timeout_cuando_llama_entonces_none(self, mock_post):
        resultado = PrintingService.generate_zpl_label({'lote_codigo': 'L1'})
        self.assertIsNone(resultado)


class PrintingServiceUrlResolutionTestCase(TestCase):
    """
    Antes PRINTING_SERVICE_URL era una constante de módulo leída de
    os.environ directamente en gestion/utils.py — un tercer default distinto
    (por casualidad correcto) frente a los dos de
    internal_api/views/pdf_produccion_views.py. Ahora las 3 llamadas usan
    settings.PRINTING_SERVICE_URL, un único punto de verdad.
    """

    @patch('gestion.utils.requests.post')
    def test_generate_zpl_dado_setting_no_definido_cuando_llama_entonces_usa_hostname_printing(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, text='^XA^XZ')
        PrintingService.generate_zpl_label({'lote_codigo': 'L1'})
        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, 'http://printing:8001/zpl/etiqueta')

    @override_settings(PRINTING_SERVICE_URL='http://staging-printing:9001')
    @patch('gestion.utils.requests.post')
    def test_generate_pdf_dado_setting_override_cuando_llama_entonces_usa_ese_dominio(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, content=b'%PDF')
        PrintingService.generate_nota_venta_pdf({'id': 1})
        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, 'http://staging-printing:9001/pdf/nota-venta')
