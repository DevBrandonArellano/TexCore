"""
Pruebas del catálogo de materiales (tipo de sustrato) por sede.

El tintorero crea los materiales con los que trabaja (algodón, poliéster, lino...).
FormulaColor.tipo_sustrato guarda la clave estable del material; el catálogo
MaterialSustrato le da nombre y controla cuáles se pueden usar en cada sede.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol × acción (tintorero / admin / bodeguero / operario);
  material de la misma sede / de otra sede; material existente / inexistente.
- Análisis de valores límite (BVA): longitud del nombre (0, 1, 2, 60 y 61 caracteres).
- Transición de estados (STT): activo → inactivo → activo, y su efecto en las fórmulas.
- Caja blanca: siembra de los materiales base al crear una sede.
- Auditoría: justificación obligatoria al editar; la siembra queda registrada.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.contenttypes.models import ContentType

from gestion.models import AuditLog, FormulaColor, MaterialSustrato
from gestion.services.versionado_formula import VersionadoFormulaService
from gestion.tests.factories import (
    CustomUserFactory,
    FormulaColorFactory,
    MaterialSustratoFactory,
    SedeFactory,
)

CLAVES_BASE = {"algodon", "poliester", "nylon", "mixto", "otro"}


class MaterialSustratoModelTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()

    def test_sede_dado_sede_nueva_cuando_se_crea_entonces_siembra_los_materiales_base(self):
        claves = set(MaterialSustrato.objects.filter(sede=self.sede).values_list("clave", flat=True))
        self.assertEqual(claves, CLAVES_BASE)

    def test_material_dado_nombre_con_tildes_y_espacios_cuando_guarda_entonces_genera_clave_estable(self):
        material = MaterialSustratoFactory(nombre="Lino Orgánico", sede=self.sede)
        self.assertEqual(material.clave, "lino_organico")

    def test_material_dado_nombre_equivalente_en_misma_sede_cuando_guarda_entonces_error(self):
        # EP inválida: misma clave (derivada del nombre) en la misma sede
        MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        with self.assertRaises(ValidationError):
            MaterialSustratoFactory(nombre="LINO", sede=self.sede)

    def test_material_dado_mismo_nombre_en_otra_sede_cuando_guarda_entonces_se_permite(self):
        MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        MaterialSustratoFactory(nombre="Lino", sede=SedeFactory())
        self.assertEqual(MaterialSustrato.objects.filter(clave="lino").count(), 2)

    def test_material_dado_nombre_sin_letras_ni_numeros_cuando_guarda_entonces_error(self):
        with self.assertRaises(ValidationError):
            MaterialSustratoFactory(nombre="!!", sede=self.sede)

    def test_material_dado_nombre_de_1_caracter_cuando_guarda_entonces_error(self):
        # BVA: por debajo del mínimo (2)
        with self.assertRaises(ValidationError):
            MaterialSustratoFactory(nombre="L", sede=self.sede)

    def test_material_dado_nombre_de_2_caracteres_cuando_guarda_entonces_se_permite(self):
        # BVA: en el mínimo
        self.assertEqual(MaterialSustratoFactory(nombre="Li", sede=self.sede).clave, "li")

    def test_material_dado_nombre_de_60_caracteres_cuando_guarda_entonces_se_permite(self):
        # BVA: en el máximo; la clave se recorta a 20 caracteres
        material = MaterialSustratoFactory(nombre="a" * 60, sede=self.sede)
        self.assertEqual(len(material.clave), 20)

    def test_material_dado_nombre_de_61_caracteres_cuando_guarda_entonces_error(self):
        # BVA: por encima del máximo
        with self.assertRaises(ValidationError):
            MaterialSustratoFactory(nombre="a" * 61, sede=self.sede)

    def test_material_dado_cambio_de_nombre_cuando_guarda_entonces_conserva_la_clave(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        material.nombre = "Lino Europeo"
        material._justificacion_auditoria = "Nombre comercial del proveedor"
        material.save()
        material.refresh_from_db()
        self.assertEqual(material.clave, "lino")

    def test_material_dado_formulas_que_lo_usan_cuando_elimina_entonces_error(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        FormulaColorFactory(sede=self.sede, tipo_sustrato="lino")
        with self.assertRaises(ValidationError):
            material.delete()
        self.assertTrue(MaterialSustrato.objects.filter(pk=material.pk).exists())

    def test_material_dado_sin_formulas_cuando_elimina_entonces_se_borra(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        FormulaColorFactory(sede=SedeFactory(), tipo_sustrato="lino")  # otra sede: no cuenta
        material._justificacion_auditoria = "Creado por error"
        material.delete()
        self.assertFalse(MaterialSustrato.objects.filter(pk=material.pk).exists())


class MaterialSustratoApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.tintorero = CustomUserFactory(sede=self.sede, groups=["tintorero"])
        self.admin = CustomUserFactory(sede=self.sede, groups=["admin_sistemas"])
        self.url = reverse("materialsustrato-list")

    def _detalle(self, material):
        return reverse("materialsustrato-detail", args=[material.id])

    def test_material_dado_tintorero_cuando_crea_entonces_201_con_sede_y_clave(self):
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.post(self.url, {"nombre": "Lino"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual((resp.data["clave"], resp.data["sede"]), ("lino", self.sede.id))

    def test_material_dado_admin_cuando_crea_entonces_201(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self.url, {"nombre": "Lino"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_material_dado_operario_o_bodeguero_cuando_crea_entonces_403(self):
        for grupo in ("operario", "bodeguero"):
            with self.subTest(grupo=grupo):
                self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=[grupo]))
                resp = self.client.post(self.url, {"nombre": f"Lino {grupo}"}, format="json")
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_material_dado_nombre_existente_en_la_sede_cuando_crea_entonces_400(self):
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.post(self.url, {"nombre": "Algodón"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_material_dado_nombre_vacio_cuando_crea_entonces_400(self):
        # BVA: 0 caracteres
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.post(self.url, {"nombre": ""}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_material_dado_autenticado_cuando_lista_entonces_solo_ve_su_sede(self):
        MaterialSustratoFactory(nombre="Lino Ajeno", sede=SedeFactory())
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=["operario"]))
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        claves = {m["clave"] for m in resp.data}
        self.assertEqual(claves, CLAVES_BASE)

    def test_material_dado_filtro_activo_cuando_lista_entonces_excluye_inactivos(self):
        MaterialSustratoFactory(nombre="Lino", sede=self.sede, activo=False)
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.get(self.url, {"activo": "true"})
        self.assertNotIn("lino", {m["clave"] for m in resp.data})

    def test_material_dado_tintorero_cuando_renombra_entonces_200_y_clave_no_cambia(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.patch(
            self._detalle(material),
            {"nombre": "Lino Europeo", "clave": "otra", "_justificacion_auditoria": "Nombre del proveedor"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        material.refresh_from_db()
        self.assertEqual((material.nombre, material.clave), ("Lino Europeo", "lino"))

    def test_material_dado_tintorero_cuando_elimina_entonces_403(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        self.client.force_authenticate(user=self.tintorero)
        resp = self.client.delete(self._detalle(material))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_material_dado_admin_y_material_sin_uso_cuando_elimina_entonces_204(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(self._detalle(material))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_material_dado_admin_y_material_en_uso_cuando_elimina_entonces_400(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        FormulaColorFactory(sede=self.sede, tipo_sustrato="lino")
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(self._detalle(material))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MaterialSustratoAuditoriaTestCase(TestCase):
    """El administrador ve en Auditoría quién creó o cambió cada material y por qué."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.tintorero = CustomUserFactory(sede=self.sede, groups=["tintorero"])
        self.client.force_authenticate(user=self.tintorero)
        self.ct = ContentType.objects.get_for_model(MaterialSustrato)

    def _logs(self, material, accion):
        return AuditLog.objects.filter(content_type=self.ct, object_id=material.id, accion=accion)

    def test_material_dado_edicion_sin_justificacion_cuando_guarda_entonces_error(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        material.activo = False
        with self.assertRaises(ValidationError):
            material.save()

    def test_material_dado_creacion_cuando_guarda_entonces_no_exige_justificacion(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        self.assertTrue(self._logs(material, "CREATE").exists())

    def test_material_dado_api_sin_justificacion_cuando_desactiva_entonces_400(self):
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        resp = self.client.patch(reverse("materialsustrato-detail", args=[material.id]), {"activo": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        material.refresh_from_db()
        self.assertTrue(material.activo)

    def test_material_dado_api_con_justificacion_cuando_desactiva_entonces_registra_sede_cambio_y_motivo(self):
        # El usuario del registro (petición con JWT real) lo cubre test_auditoria_usuario_jwt.py.
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        resp = self.client.patch(
            reverse("materialsustrato-detail", args=[material.id]),
            {"activo": False, "_justificacion_auditoria": "El proveedor dejó de venderlo"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        log = self._logs(material, "UPDATE").get()
        self.assertEqual(log.object_sede_id, self.sede.id)
        self.assertEqual((log.valor_anterior, log.valor_nuevo), ({"activo": True}, {"activo": False}))
        self.assertEqual(log.justificacion, "El proveedor dejó de venderlo")

    def test_sede_dado_sede_nueva_cuando_siembra_materiales_entonces_cada_uno_queda_auditado_con_la_sede(self):
        sede = SedeFactory(nombre="Sede Norte")
        logs = AuditLog.objects.filter(content_type=self.ct, accion="CREATE", object_sede_id=sede.id)
        self.assertEqual(logs.count(), len(CLAVES_BASE))
        self.assertTrue(all("Sede Norte" in log.justificacion for log in logs))


class FormulaConMaterialTestCase(TestCase):
    """La fórmula solo acepta materiales activos del catálogo de su sede."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.tintorero = CustomUserFactory(sede=self.sede, groups=["tintorero"])
        self.client.force_authenticate(user=self.tintorero)
        self.url = reverse("formulacolor-list")

    def _crear(self, tipo_sustrato, codigo="FC-MAT-1"):
        datos = {"codigo": codigo, "nombre_color": "Azul", "tipo_sustrato": tipo_sustrato, "fases": []}
        return self.client.post(self.url, datos, format="json")

    def test_formula_dado_material_creado_por_tintorero_cuando_crea_entonces_201(self):
        MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        resp = self._crear("lino")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["tipo_sustrato_display"], "Lino")

    def test_formula_dado_material_inexistente_cuando_crea_entonces_400(self):
        resp = self._crear("seda")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tipo_sustrato", resp.data["error"]["fields"])

    def test_formula_dado_material_de_otra_sede_cuando_crea_entonces_400(self):
        MaterialSustratoFactory(nombre="Lino", sede=SedeFactory())
        resp = self._crear("lino")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_formula_dado_material_inactivo_cuando_crea_entonces_400(self):
        # STT: activo → inactivo, ya no se ofrece para fórmulas nuevas
        MaterialSustratoFactory(nombre="Lino", sede=self.sede, activo=False)
        resp = self._crear("lino")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_formula_dado_material_reactivado_cuando_crea_entonces_201(self):
        # STT: inactivo → activo, vuelve a estar disponible
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede, activo=False)
        material.activo = True
        material._justificacion_auditoria = "Vuelve a usarse en planta"
        material.save()
        self.assertEqual(self._crear("lino").status_code, status.HTTP_201_CREATED)

    def test_formula_dado_material_desactivado_despues_cuando_edita_sin_cambiarlo_entonces_200(self):
        # STT: la fórmula que ya usaba el material sigue editándose y mostrándose
        material = MaterialSustratoFactory(nombre="Lino", sede=self.sede)
        formula = FormulaColorFactory(sede=self.sede, tipo_sustrato="lino", estado="en_pruebas")
        material.activo = False
        material._justificacion_auditoria = "Ya no se compra"
        material.save()
        resp = self.client.patch(
            reverse("formulacolor-detail", args=[formula.id]),
            {"tipo_sustrato": "lino", "observaciones": "Ajuste", "_justificacion_auditoria": "Ajuste de prueba"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["tipo_sustrato_display"], "Lino")

    def test_formula_dado_listado_cuando_lista_entonces_muestra_nombre_del_material(self):
        FormulaColorFactory(sede=self.sede, tipo_sustrato="poliester")
        resp = self.client.get(self.url)
        data = resp.data.get("results", resp.data)
        self.assertEqual(data[0]["tipo_sustrato_display"], "Poliéster")

    def test_derivar_dado_material_inexistente_cuando_deriva_entonces_error(self):
        origen = FormulaColorFactory(sede=self.sede, estado="en_pruebas", tipo_sustrato="algodon")
        version = VersionadoFormulaService.crear_version(origen, "Ensayo base", self.tintorero)
        with self.assertRaises(ValidationError):
            VersionadoFormulaService.derivar(
                origen, version, {"codigo": "DER-1", "nombre_color": "Azul", "tipo_sustrato": "seda"}, self.tintorero
            )
        self.assertFalse(FormulaColor.objects.filter(codigo="DER-1").exists())
