"""
Aislamiento por sede de los reportes de la internal_api (OWASP A01, defensa en profundidad).

Un token de servicio con el claim de sede de un usuario que no es admin no puede pedir los
datos de otra sede: cada vista responde 403 antes de consultar. La ruta interna del pulso
diario se retiró el 9-nov-2026: no tenía consumidor y el pulso lo sirve el backend humano
(`/api/produccion/pulso-diario/`), que sí conoce al usuario y su sede.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): sede del claim igual / distinta a la pedida; ruta vigente / retirada.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from internal_api.authentication import JWTServiceAuthentication

BASE = "/api/internal/v1/"
RUTAS_CON_SEDE = (
    "reports/productos/",
    "reports/usuarios/",
    "gerencial/ventas/",
    "gerencial/top-clientes/",
    "gerencial/deudores/",
    "produccion/ordenes/",
    "produccion/lotes/",
    "produccion/tendencia/",
)


def _cliente(sede_id=None, is_admin=False):
    token = JWTServiceAuthentication.generate_token(
        service_name="reporting_excel", scopes=["reports:read"], sede_id=sede_id, is_admin=is_admin
    )
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return cliente


class ReportesInternosAlcanceSedeTest(TestCase):
    def test_reportes_dado_claim_de_una_sede_cuando_pide_otra_entonces_403(self):
        cliente = _cliente(sede_id=1)
        for ruta in RUTAS_CON_SEDE:
            with self.subTest(ruta=ruta):
                resp = cliente.get(f"{BASE}{ruta}", {"sede_id": 2})
                self.assertEqual(resp.status_code, 403)
                self.assertIn("otra sede", resp.data["detail"])

    def test_reportes_dado_claim_de_una_sede_cuando_pide_la_suya_entonces_200(self):
        cliente = _cliente(sede_id=1)
        for ruta in RUTAS_CON_SEDE:
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(f"{BASE}{ruta}", {"sede_id": 1}).status_code, 200)


class RutaInternaPulsoDiarioRetiradaTest(TestCase):
    def test_pulso_diario_interno_dado_token_admin_cuando_get_entonces_404(self):
        self.assertEqual(_cliente(is_admin=True).get(f"{BASE}planta/pulso-diario/").status_code, 404)
