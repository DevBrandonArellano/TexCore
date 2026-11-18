"""
GET /api/inventory/audit-logs/: filtro por módulo (tabla afectada) y nombres legibles.

El administrador de sistemas filtra la auditoría por módulo («Material», «Fórmula de
color»...) en vez de escribir el nombre técnico de la tabla.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): con módulo / sin módulo / módulo inexistente; rol con
  acceso a la auditoría / sin acceso.
- Caja negra: catálogo de módulos y nombre legible de cada registro.
"""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import AuditLog, FormulaColor, MaterialSustrato
from gestion.tests.factories import CustomUserFactory, SedeFactory

URL = "/api/inventory/audit-logs/"
URL_MODULOS = "/api/inventory/audit-logs/modulos/"


class AuditLogModulosTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.admin = CustomUserFactory(sede=self.sede, groups=["admin_sistemas"])
        self.client.force_authenticate(user=self.admin)

        def log(modelo):
            return AuditLog.objects.create(
                content_type=ContentType.objects.get_for_model(modelo), object_id=1, accion="UPDATE"
            )

        self.log_material = log(MaterialSustrato)
        self.log_formula = log(FormulaColor)

    def test_audit_logs_dado_modulo_cuando_filtra_entonces_solo_devuelve_esa_tabla(self):
        resp = self.client.get(URL, {"tabla": "materialsustrato"})
        self.assertEqual(resp.status_code, 200)
        ids = {r["id"] for r in resp.data["results"]}
        self.assertIn(self.log_material.id, ids)
        self.assertNotIn(self.log_formula.id, ids)

    def test_audit_logs_dado_modulo_inexistente_cuando_filtra_entonces_no_devuelve_nada(self):
        resp = self.client.get(URL, {"tabla": "no_existe"})
        self.assertEqual(resp.data["results"], [])

    def test_audit_logs_dado_registro_de_material_cuando_lista_entonces_muestra_nombre_legible(self):
        resp = self.client.get(URL, {"tabla": "materialsustrato"})
        fila = next(r for r in resp.data["results"] if r["id"] == self.log_material.id)
        self.assertEqual(fila["tabla_afectada"], "Material")

    def test_modulos_dado_admin_cuando_consulta_entonces_lista_los_modulos_auditados_con_su_nombre(self):
        resp = self.client.get(URL_MODULOS)
        self.assertEqual(resp.status_code, 200)
        modulos = {m["valor"]: m["etiqueta"] for m in resp.data}
        self.assertEqual(modulos["materialsustrato"], "Material")
        self.assertEqual(modulos["formulacolor"], "Fórmula Color")
        self.assertIn("customuser", modulos)
        etiquetas = [m["etiqueta"] for m in resp.data]
        self.assertEqual(etiquetas, sorted(etiquetas))

    def test_modulos_dado_usuario_sin_acceso_a_auditoria_cuando_consulta_entonces_403(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=["operario"]))
        resp = self.client.get(URL_MODULOS)
        self.assertEqual(resp.status_code, 403)
