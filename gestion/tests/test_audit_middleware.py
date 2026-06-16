"""
Pruebas del middleware de auditoría — gestion/middleware.py.

Foco de seguridad: extracción segura de la IP del cliente con prevención de
IP spoofing vía X-Forwarded-For (solo se confía en proxies de redes privadas).

Técnicas ISTQB aplicadas:
- Caja blanca (cobertura de decisiones): cada rama de _extract_client_ip y
  _is_trusted_proxy, incluyendo rutas de excepción (ValueError).
- Particiones de equivalencia (EP): IP de proxy confiable / no confiable / inválida.
- Análisis de valores límite (BVA): bordes exactos de los rangos CIDR de confianza.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from gestion.middleware import (
    AuditMiddleware,
    _extract_client_ip,
    _is_trusted_proxy,
    get_current_user,
    get_current_ip,
    set_cascade_justification,
    get_cascade_justification,
    clear_cascade_justification,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# _is_trusted_proxy — EP + BVA sobre los rangos CIDR de confianza
# ---------------------------------------------------------------------------
class IsTrustedProxyTestCase(TestCase):
    """Caja blanca: rama True (IP en red confiable), False y except (ValueError)."""

    def test_proxy_dado_ip_docker_bridge_cuando_verifica_entonces_confiable(self):
        # EP: clase confiable — red bridge de Docker (172.16/12)
        self.assertTrue(_is_trusted_proxy('172.18.0.1'))

    def test_proxy_dado_ip_loopback_cuando_verifica_entonces_confiable(self):
        # EP: loopback 127.0.0.1/32
        self.assertTrue(_is_trusted_proxy('127.0.0.1'))

    def test_proxy_dado_ip_privada_clase_c_cuando_verifica_entonces_confiable(self):
        self.assertTrue(_is_trusted_proxy('192.168.1.10'))

    def test_proxy_dado_ip_publica_cuando_verifica_entonces_no_confiable(self):
        # EP: clase no confiable — IP pública (cliente externo)
        self.assertFalse(_is_trusted_proxy('8.8.8.8'))

    def test_proxy_dado_string_no_ip_cuando_verifica_entonces_falso(self):
        # Caja blanca: rama except ValueError
        self.assertFalse(_is_trusted_proxy('no-es-una-ip'))

    def test_proxy_dado_string_vacio_cuando_verifica_entonces_falso(self):
        self.assertFalse(_is_trusted_proxy(''))

    def test_proxy_dado_borde_inferior_172_16_cuando_verifica_entonces_confiable(self):
        # BVA: límite inferior exacto del rango 172.16.0.0/12
        self.assertTrue(_is_trusted_proxy('172.16.0.0'))

    def test_proxy_dado_borde_superior_172_31_cuando_verifica_entonces_confiable(self):
        # BVA: límite superior del rango 172.16.0.0/12
        self.assertTrue(_is_trusted_proxy('172.31.255.255'))

    def test_proxy_dado_justo_bajo_rango_172_15_cuando_verifica_entonces_no_confiable(self):
        # BVA: justo por debajo del rango (172.15.x.x no pertenece a /12)
        self.assertFalse(_is_trusted_proxy('172.15.255.255'))

    def test_proxy_dado_justo_sobre_rango_172_32_cuando_verifica_entonces_no_confiable(self):
        # BVA: justo por encima del rango
        self.assertFalse(_is_trusted_proxy('172.32.0.0'))

    def test_proxy_dado_loopback_127_0_0_2_cuando_verifica_entonces_no_confiable(self):
        # BVA: la confianza loopback es /32, solo 127.0.0.1 exacto
        self.assertFalse(_is_trusted_proxy('127.0.0.2'))


# ---------------------------------------------------------------------------
# _extract_client_ip — tabla de decisión XFF × confianza × validez
# ---------------------------------------------------------------------------
class ExtractClientIpTestCase(TestCase):
    """
    Caja blanca: cada combinación de (X-Forwarded-For presente, proxy confiable,
    IP del cliente válida) que determina si se usa la IP reenviada o REMOTE_ADDR.
    """

    def setUp(self):
        self.rf = RequestFactory()

    def _request(self, remote_addr, xff=None):
        extra = {'REMOTE_ADDR': remote_addr}
        if xff is not None:
            extra['HTTP_X_FORWARDED_FOR'] = xff
        return self.rf.get('/', **extra)

    def test_ip_dado_xff_y_proxy_confiable_cuando_extrae_entonces_usa_ip_cliente(self):
        # Caso feliz: proxy confiable reenvía la IP real del cliente
        req = self._request('172.18.0.5', xff='203.0.113.7')
        self.assertEqual(_extract_client_ip(req), '203.0.113.7')

    def test_ip_dado_xff_con_cadena_cuando_extrae_entonces_usa_primera(self):
        # XFF con múltiples saltos: se toma el primero (cliente original)
        req = self._request('172.18.0.5', xff='203.0.113.7, 70.41.3.18, 150.172.238.178')
        self.assertEqual(_extract_client_ip(req), '203.0.113.7')

    def test_ip_dado_proxy_no_confiable_cuando_extrae_entonces_ignora_xff(self):
        # SEGURIDAD: cliente externo intenta spoofear XFF -> se ignora
        req = self._request('8.8.8.8', xff='1.2.3.4')
        self.assertEqual(_extract_client_ip(req), '8.8.8.8')

    def test_ip_dado_sin_xff_cuando_extrae_entonces_usa_remote_addr(self):
        req = self._request('172.18.0.5')
        self.assertEqual(_extract_client_ip(req), '172.18.0.5')

    def test_ip_dado_xff_invalida_desde_proxy_confiable_cuando_extrae_entonces_remote_addr(self):
        # Caja blanca: rama except ValueError dentro del bloque de proxy confiable
        req = self._request('172.18.0.5', xff='no-ip')
        self.assertEqual(_extract_client_ip(req), '172.18.0.5')

    def test_ip_dado_xff_vacio_cuando_extrae_entonces_remote_addr(self):
        req = self._request('172.18.0.5', xff='   ')
        self.assertEqual(_extract_client_ip(req), '172.18.0.5')


# ---------------------------------------------------------------------------
# AuditMiddleware.__call__ — flujo normal y de excepción
# ---------------------------------------------------------------------------
class AuditMiddlewareCallTestCase(TestCase):
    """Caja blanca: rama feliz (response) y rama de excepción (re-raise)."""

    def setUp(self):
        self.rf = RequestFactory()

    def test_middleware_dado_request_normal_cuando_llama_entonces_propaga_response(self):
        sentinel = object()

        def get_response(request):
            # Durante la petición, la IP debe estar disponible en thread-local
            assert get_current_ip() == '172.18.0.9'

            class Resp:
                status_code = 200
            return Resp()

        mw = AuditMiddleware(get_response)
        req = self.rf.get('/api/x/', REMOTE_ADDR='172.18.0.9')
        resp = mw(req)
        self.assertEqual(resp.status_code, 200)
        # Tras la petición, el thread-local se limpia
        self.assertIsNone(get_current_ip())

    def test_middleware_dado_excepcion_cuando_llama_entonces_re_lanza_y_limpia(self):
        def get_response(request):
            raise ValueError("fallo interno")

        mw = AuditMiddleware(get_response)
        req = self.rf.get('/api/x/', REMOTE_ADDR='172.18.0.9')
        with self.assertRaises(ValueError):
            mw(req)
        # El finally debe ejecutarse igualmente y limpiar el thread-local
        self.assertIsNone(get_current_ip())


# ---------------------------------------------------------------------------
# get_current_user — verificación de existencia en BD
# ---------------------------------------------------------------------------
class GetCurrentUserTestCase(TestCase):
    """Caja blanca: usuario existe / no existe en BD / sin usuario en contexto."""

    def tearDown(self):
        clear_cascade_justification()
        # Limpia thread-local entre tests
        from gestion import middleware
        middleware._local.__dict__.pop('user', None)

    def test_usuario_dado_sin_contexto_cuando_consulta_entonces_none(self):
        from gestion import middleware
        middleware._local.__dict__.pop('user', None)
        self.assertIsNone(get_current_user())

    def test_usuario_dado_existe_en_bd_cuando_consulta_entonces_lo_retorna(self):
        from gestion import middleware
        user = User.objects.create_user(username='audit_u1', password='x')
        middleware._local.user = user
        self.assertEqual(get_current_user(), user)

    def test_usuario_dado_borrado_de_bd_cuando_consulta_entonces_none(self):
        from gestion import middleware
        user = User.objects.create_user(username='audit_u2', password='x')
        middleware._local.user = user
        pk = user.pk
        User.objects.filter(pk=pk).delete()
        self.assertIsNone(get_current_user())


# ---------------------------------------------------------------------------
# Justificación de cascada — set / get / clear
# ---------------------------------------------------------------------------
class CascadeJustificationTestCase(TestCase):
    """EP: valor presente vs ausente tras clear."""

    def test_cascada_dado_valor_seteado_cuando_obtiene_entonces_lo_retorna(self):
        set_cascade_justification("Borrado autorizado por jefe")
        self.assertEqual(get_cascade_justification(), "Borrado autorizado por jefe")

    def test_cascada_dado_clear_cuando_obtiene_entonces_none(self):
        set_cascade_justification("temporal")
        clear_cascade_justification()
        self.assertIsNone(get_cascade_justification())

    def test_cascada_dado_nunca_seteado_cuando_obtiene_entonces_none(self):
        clear_cascade_justification()
        self.assertIsNone(get_cascade_justification())
