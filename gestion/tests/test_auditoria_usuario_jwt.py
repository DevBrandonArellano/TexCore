"""
La auditoría registra al usuario que hace el cambio cuando entra con el JWT de la cookie.

Defecto encontrado el 18-nov-2026: AuditMiddleware guarda `request.user` antes de que DRF
autentique el JWT, así que todo cambio hecho por la API quedaba como «Sistema» en la
auditoría de Admin Sistemas.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): petición autenticada con JWT / sin JWT válido.
- Caja negra: petición real de punta a punta (cookie → middleware → DRF → AuditLog).
"""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from gestion.middleware import get_current_user
from gestion.models import AuditLog, MaterialSustrato
from gestion.tests.factories import CustomUserFactory, MaterialSustratoFactory, SedeFactory


class AuditoriaUsuarioJwtTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.tintorero = CustomUserFactory(sede=self.sede, groups=["tintorero"])
        self.material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        self.client = APIClient()

    def _con_cookie_jwt(self, usuario):
        self.client.cookies["access_token"] = str(RefreshToken.for_user(usuario).access_token)

    def _desactivar(self):
        return self.client.patch(
            reverse("materialsustrato-detail", args=[self.material.id]),
            {"activo": False, "_justificacion_auditoria": "Ya no se compra"},
            format="json",
        )

    def test_auditoria_dado_usuario_con_jwt_en_cookie_cuando_edita_entonces_registra_ese_usuario(self):
        self._con_cookie_jwt(self.tintorero)
        resp = self._desactivar()
        self.assertEqual(resp.status_code, 200, resp.data)
        log = AuditLog.objects.get(
            content_type=ContentType.objects.get_for_model(MaterialSustrato), object_id=self.material.id, accion="UPDATE"
        )
        self.assertEqual(log.usuario, self.tintorero)

    def test_auditoria_dado_peticion_terminada_cuando_sigue_el_hilo_entonces_no_queda_usuario_colgado(self):
        self._con_cookie_jwt(self.tintorero)
        self._desactivar()
        self.assertIsNone(get_current_user())

    def test_auditoria_dado_token_invalido_cuando_edita_entonces_401_y_no_registra(self):
        self.client.cookies["access_token"] = "token-invalido"
        resp = self._desactivar()
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(AuditLog.objects.filter(accion="UPDATE", object_id=self.material.id).exists())
