"""
Pruebas de las vistas de sistema — gestion/views/system_views.py.

FrontendLogView: relay de logs del navegador hacia el logger backend (RFC 5424).
Es AllowAny (sin autenticación) y mapea severity → nivel de logging Python.

Técnicas ISTQB aplicadas:
- Particiones de equivalencia (EP) sobre 'severity': los rangos que mapean a
  CRITICAL / ERROR / WARNING / INFO.
- Análisis de valores límite (BVA): severity = 2, 3, 4, 5 (fronteras del mapeo).
- Caja blanca: rama de payload no-dict (400) y payload válido (204).
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class FrontendLogViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("frontend-logs")

    def test_log_dado_entrada_valida_cuando_post_entonces_204(self):
        resp = self.client.post(
            self.url, {"severity": 6, "message": "evento de prueba", "msgid": "ui.click"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_payload_no_dict_cuando_post_entonces_400(self):
        # Caja blanca: rama `not isinstance(entry, dict)` -> 400
        resp = self.client.post(self.url, ["no", "es", "dict"], format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_log_dado_severity_critica_cuando_post_entonces_204(self):
        # BVA: severity = 2 (frontera CRITICAL: <= 2)
        resp = self.client.post(self.url, {"severity": 2, "message": "crit"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_severity_error_cuando_post_entonces_204(self):
        # BVA: severity = 3 (ERROR)
        resp = self.client.post(self.url, {"severity": 3, "message": "err"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_severity_warning_cuando_post_entonces_204(self):
        # BVA: severity = 4 (WARNING)
        resp = self.client.post(self.url, {"severity": 4, "message": "warn"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_severity_info_cuando_post_entonces_204(self):
        # BVA: severity = 5 (frontera INFO: >= 5)
        resp = self.client.post(self.url, {"severity": 5, "message": "info"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_msgid_con_puntos_cuando_post_entonces_normaliza_y_204(self):
        # El msgid con puntos se normaliza (replace '.' -> '-')
        resp = self.client.post(self.url, {"severity": 6, "message": "x", "msgid": "modulo.sub.accion"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_sin_campos_cuando_post_entonces_usa_defaults_204(self):
        # Sin severity/message: usa defaults (severity=6 -> INFO)
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_sd_no_dict_cuando_post_entonces_400_y_loguea_el_error(self):
        # Medio: 'sd' no-dict revienta en sd['source'] = 'browser' (TypeError),
        # capturado por el except Exception genérico. Antes ese except no
        # logueaba nada pese a que el comentario decía "registrar en el
        # backend si es posible" — la falla de ingesta de logs del frontend
        # era invisible en el propio backend.
        with self.assertLogs("gestion.views", level="WARNING") as cm:
            resp = self.client.post(self.url, {"sd": "no-es-un-dict"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any("frontend" in msg.lower() for msg in cm.output))


class FrontendLogEndurecimientoTestCase(TestCase):
    """
    RNF-02 / OWASP API4: el relay es público (el front registra errores incluso en el login),
    así que acota lo que acepta. Sin esto, cada `msgid` distinto creaba un logger nuevo que
    Python nunca libera, un salto de línea en el mensaje falsificaba una línea de log y no
    había límite de tasa.

    Técnicas ISTQB: EP (msgid válido / con caracteres no permitidos), BVA (mensaje en el
    límite de longitud y uno por encima; la petición en el límite de tasa y la siguiente).
    """

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = APIClient()
        self.url = reverse("frontend-logs")

    def _registro(self, payload, logger="frontend"):
        with self.assertLogs(logger, level="INFO") as capturado:
            resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        return capturado.records[0]

    def test_log_dado_msgid_con_caracteres_no_permitidos_cuando_post_entonces_usa_el_logger_generico(self):
        registro = self._registro({"severity": 6, "message": "x", "msgid": "../../evil name\n"})
        self.assertEqual(registro.name, "frontend.frontend")

    def test_log_dado_msgid_mas_largo_que_el_limite_cuando_post_entonces_usa_el_logger_generico(self):
        registro = self._registro({"severity": 6, "message": "x", "msgid": "a" * 41})
        self.assertEqual(registro.name, "frontend.frontend")

    def test_log_dado_msgid_valido_en_el_limite_cuando_post_entonces_conserva_el_nombre(self):
        registro = self._registro({"severity": 6, "message": "x", "msgid": "a" * 40})
        self.assertEqual(registro.name, "frontend." + "a" * 40)

    def test_log_dado_saltos_de_linea_en_el_mensaje_cuando_post_entonces_no_falsifica_lineas(self):
        registro = self._registro({"severity": 6, "message": "ok\n<134>1 falso\r\notra"})
        self.assertNotIn("\n", registro.getMessage())
        self.assertNotIn("\r", registro.getMessage())

    def test_log_dado_mensaje_mas_largo_que_el_limite_cuando_post_entonces_lo_recorta(self):
        registro = self._registro({"severity": 6, "message": "x" * 5000})
        self.assertEqual(len(registro.getMessage()), 2000)

    def test_log_dado_severity_no_numerica_cuando_post_entonces_registra_como_info(self):
        import logging

        registro = self._registro({"severity": "alto", "message": "x"})
        self.assertEqual(registro.levelno, logging.INFO)

    def test_log_dado_sd_con_demasiadas_claves_y_valores_largos_cuando_post_entonces_los_acota(self):
        sd = {f"k{i}": "v" * 500 for i in range(50)}
        registro = self._registro({"severity": 6, "message": "x", "sd": sd})
        # 20 claves del cliente + `source` e `ip`, que pone el backend.
        self.assertEqual(len(registro.sd), 22)
        self.assertTrue(all(len(str(v)) <= 200 for v in registro.sd.values()))

    def test_log_dado_sd_que_intenta_cambiar_la_ip_cuando_post_entonces_prevalece_la_del_backend(self):
        registro = self._registro({"severity": 6, "message": "x", "sd": {"ip": "1.2.3.4", "source": "server"}})
        self.assertEqual(registro.sd["source"], "browser")
        self.assertNotEqual(registro.sd["ip"], "1.2.3.4")

    def test_log_dado_rafaga_por_encima_del_limite_cuando_post_entonces_429(self):
        from unittest.mock import patch

        from gestion.views.system_views import FrontendLogThrottle

        with patch.object(FrontendLogThrottle, "rate", "2/min"):
            codigos = [self.client.post(self.url, {"message": "x"}, format="json").status_code for _ in range(3)]
        self.assertEqual(codigos, [204, 204, 429])


class FrontendLogIpClienteTestCase(TestCase):
    """
    TEX-03 CA-3 (hallazgo M-8): la IP del log debe ser la del cliente real. Detrás de Nginx
    REMOTE_ADDR es la del proxy; se usa la misma regla que el AuditMiddleware
    (`_extract_client_ip`): X-Forwarded-For solo si llega desde un proxy de confianza.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("frontend-logs")

    def _ip_registrada(self, **meta):
        with self.assertLogs("frontend.ui-ip", level="INFO") as capturado:
            self.client.post(self.url, {"severity": 6, "message": "x", "msgid": "ui.ip"}, format="json", **meta)
        return capturado.records[0].sd["ip"]

    def test_log_dado_peticion_desde_proxy_de_confianza_cuando_post_entonces_registra_ip_del_cliente(self):
        ip = self._ip_registrada(REMOTE_ADDR="172.18.0.5", HTTP_X_FORWARDED_FOR="190.15.1.20, 172.18.0.5")
        self.assertEqual(ip, "190.15.1.20")

    def test_log_dado_forwarded_for_desde_ip_publica_cuando_post_entonces_ignora_el_encabezado(self):
        # Anti-spoofing: un cliente externo no puede elegir la IP que queda en el log.
        ip = self._ip_registrada(REMOTE_ADDR="200.1.1.1", HTTP_X_FORWARDED_FOR="10.9.9.9")
        self.assertEqual(ip, "200.1.1.1")
