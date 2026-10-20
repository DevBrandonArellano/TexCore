"""
Pruebas del cifrado en reposo de los datos personales — RS-19 (LOPDP 2021).

Afirmación bajo prueba: `Cliente.ruc_cedula` y `CustomUser.date_of_birth` no quedan
en claro en la base, el ORM los entrega descifrados, y la búsqueda por identificación
y la unicidad (RUC + sede) siguen funcionando a través del índice ciego.

Las comprobaciones de «no está en claro» leen la columna con SQL directo a propósito:
el ORM descifra al leer, así que preguntarle a él nunca demostraría nada.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): valor presente / nulo; RUC repetido en la misma sede
  / en otra sede; clave activa / clave retirada de la rotación.
- Valores límite (BVA): cadena vacía y valor con espacios alrededor.
- Caja blanca: las dos ramas de `descifrar()` (token válido / inválido), las ramas de
  `BlindIndexField.pre_save()` (valor presente / vacío) y las de
  `cifrar_datos_personales` (fila en claro, índice desfasado, token ilegible).
"""

import datetime
from unittest.mock import patch

from django.core.exceptions import FieldError, ValidationError
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.crypto import ErrorDeCifrado, cifrar, descifrar, generar_clave, indice_ciego, normalizar_identificacion
from gestion.models import Cliente, CustomUser
from gestion.signals import _get_user_audit_data
from gestion.tests.factories import ClienteFactory, CustomUserFactory, SedeFactory

RUC_PRUEBA = "1790012345001"


def _columna_cruda(modelo, campo, pk):
    """Lee la columna tal cual está en la base, sin pasar por el descifrado del ORM."""
    tabla = modelo._meta.db_table
    columna = modelo._meta.get_field(campo).column
    pk_col = modelo._meta.pk.column
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {columna} FROM {tabla} WHERE {pk_col} = %s",  # noqa: S608 — identificadores de _meta
            [pk],
        )
        return cursor.fetchone()[0]


class CifradoClienteTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()

    def test_cliente_dado_un_ruc_cuando_se_guarda_entonces_la_columna_no_lo_contiene_en_claro(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        guardado = _columna_cruda(Cliente, "ruc_cedula", cliente.pk)

        self.assertNotIn(RUC_PRUEBA, guardado)
        self.assertTrue(guardado.startswith("gAAAAA"), "no parece un token Fernet")

    def test_cliente_dado_un_ruc_cifrado_cuando_se_relee_entonces_el_orm_devuelve_el_valor_original(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        recargado = Cliente.objects.get(pk=cliente.pk)

        self.assertEqual(recargado.ruc_cedula, RUC_PRUEBA)

    def test_cliente_dado_el_mismo_ruc_en_dos_filas_cuando_se_comparan_entonces_los_textos_cifrados_difieren(self):
        """Fernet usa IV aleatorio: dos cifrados del mismo valor no son iguales.

        Es la razón por la que la unicidad no puede ir sobre la columna cifrada.
        """
        otra_sede = SedeFactory()
        uno = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)
        dos = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=otra_sede)

        self.assertNotEqual(
            _columna_cruda(Cliente, "ruc_cedula", uno.pk),
            _columna_cruda(Cliente, "ruc_cedula", dos.pk),
        )

    def test_cliente_dado_un_ruc_existente_cuando_se_busca_por_identificacion_entonces_lo_encuentra(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        encontrado = Cliente.objects.por_identificacion(RUC_PRUEBA).first()

        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado.pk, cliente.pk)

    def test_cliente_dado_un_ruc_inexistente_cuando_se_busca_por_identificacion_entonces_no_devuelve_nada(self):
        ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        self.assertEqual(Cliente.objects.por_identificacion("0000000000").count(), 0)

    def test_cliente_dado_el_campo_cifrado_cuando_se_filtra_por_igualdad_entonces_lanza_fielderror(self):
        """Un `filter` sobre la columna cifrada devolvería vacío en silencio: mejor que falle."""
        ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        with self.assertRaises(FieldError) as ctx:
            Cliente.objects.filter(ruc_cedula=RUC_PRUEBA).count()

        self.assertIn("por_identificacion", str(ctx.exception))

    def test_cliente_dado_el_campo_cifrado_cuando_se_filtra_por_startswith_entonces_lanza_fielderror(self):
        with self.assertRaises(FieldError):
            Cliente.objects.filter(ruc_cedula__startswith="179").count()

    def test_cliente_dado_un_ruc_repetido_en_la_misma_sede_cuando_se_guarda_entonces_lanza_validationerror(self):
        ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        with self.assertRaises(ValidationError) as ctx:
            Cliente(
                ruc_cedula=RUC_PRUEBA,
                nombre_razon_social="Duplicado SA",
                direccion_envio="Calle 1",
                nivel_precio="normal",
                sede=self.sede,
            ).save()

        self.assertIn("identificación", " ".join(ctx.exception.messages))

    def test_cliente_dado_un_ruc_repetido_en_otra_sede_cuando_se_guarda_entonces_lo_acepta(self):
        ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)
        otra_sede = SedeFactory()

        Cliente(
            ruc_cedula=RUC_PRUEBA,
            nombre_razon_social="Misma identificación otra sede SA",
            direccion_envio="Calle 1",
            nivel_precio="normal",
            sede=otra_sede,
        ).save()

        self.assertEqual(Cliente.objects.por_identificacion(RUC_PRUEBA).count(), 2)

    def test_cliente_dado_un_ruc_con_espacios_cuando_se_guarda_entonces_lo_normaliza(self):
        cliente = ClienteFactory(ruc_cedula=f"  {RUC_PRUEBA}  ", sede=self.sede)

        cliente.refresh_from_db()

        self.assertEqual(cliente.ruc_cedula, RUC_PRUEBA)
        self.assertEqual(Cliente.objects.por_identificacion(RUC_PRUEBA).count(), 1)

    def test_cliente_dado_una_carga_masiva_cuando_usa_bulk_create_entonces_calcula_el_indice_ciego(self):
        """`bulk_create` no pasa por `save()` ni por `clean()`, solo por `pre_save()`."""
        Cliente.objects.bulk_create(
            [
                Cliente(
                    ruc_cedula=f"070000000{i}",
                    nombre_razon_social=f"Masivo {i} SA",
                    direccion_envio="Calle 2",
                    nivel_precio="normal",
                    sede=self.sede,
                )
                for i in range(3)
            ]
        )

        for i in range(3):
            self.assertEqual(Cliente.objects.por_identificacion(f"070000000{i}").count(), 1)

    def test_cliente_dado_un_ruc_cuando_se_guarda_entonces_el_indice_ciego_es_el_hmac_esperado(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        cliente.refresh_from_db()

        self.assertEqual(cliente.ruc_cedula_hash, indice_ciego(RUC_PRUEBA))
        self.assertEqual(len(cliente.ruc_cedula_hash), 64)


class CifradoFechaNacimientoTestCase(TestCase):
    def test_usuario_dado_una_fecha_de_nacimiento_cuando_se_guarda_entonces_la_columna_no_la_contiene_en_claro(self):
        usuario = CustomUserFactory(date_of_birth=datetime.date(1990, 5, 17))

        guardado = _columna_cruda(CustomUser, "date_of_birth", usuario.pk)

        self.assertNotIn("1990-05-17", str(guardado))
        self.assertTrue(str(guardado).startswith("gAAAAA"))

    def test_usuario_dado_una_fecha_cifrada_cuando_se_relee_entonces_el_orm_devuelve_un_date(self):
        usuario = CustomUserFactory(date_of_birth=datetime.date(1990, 5, 17))

        recargado = CustomUser.objects.get(pk=usuario.pk)

        self.assertEqual(recargado.date_of_birth, datetime.date(1990, 5, 17))

    def test_usuario_dado_una_fecha_nula_cuando_se_guarda_entonces_la_columna_queda_nula(self):
        usuario = CustomUserFactory(date_of_birth=None)

        self.assertIsNone(_columna_cruda(CustomUser, "date_of_birth", usuario.pk))
        self.assertIsNone(CustomUser.objects.get(pk=usuario.pk).date_of_birth)

    def test_usuario_dado_una_fecha_en_texto_iso_cuando_se_guarda_entonces_la_normaliza_a_date(self):
        usuario = CustomUserFactory(date_of_birth="1985-12-01")

        self.assertEqual(CustomUser.objects.get(pk=usuario.pk).date_of_birth, datetime.date(1985, 12, 1))


class AuditoriaSinDatosPersonalesTestCase(TestCase):
    def test_auditoria_dado_un_usuario_con_fecha_cuando_se_extraen_sus_datos_entonces_no_incluye_la_fecha(self):
        """`AuditLog` no está cifrado: la fecha se audita por su HMAC, no en claro."""
        usuario = CustomUserFactory(date_of_birth=datetime.date(1990, 5, 17))

        datos = _get_user_audit_data(usuario)

        self.assertNotIn("1990-05-17", str(datos))
        self.assertTrue(datos["date_of_birth"].startswith("hmac:"))

    def test_auditoria_dado_dos_fechas_distintas_cuando_se_extraen_entonces_sus_marcas_difieren(self):
        """La marca redactada debe seguir delatando el cambio, que es lo que audita."""
        uno = CustomUserFactory(date_of_birth=datetime.date(1990, 5, 17))
        dos = CustomUserFactory(date_of_birth=datetime.date(1991, 6, 18))

        self.assertNotEqual(
            _get_user_audit_data(uno)["date_of_birth"],
            _get_user_audit_data(dos)["date_of_birth"],
        )

    def test_auditoria_dado_un_usuario_sin_fecha_cuando_se_extraen_sus_datos_entonces_queda_nula(self):
        usuario = CustomUserFactory(date_of_birth=None)

        self.assertIsNone(_get_user_audit_data(usuario)["date_of_birth"])


class PrimitivasDeCifradoTestCase(TestCase):
    def test_cifrar_dado_un_texto_cuando_se_descifra_entonces_devuelve_el_original(self):
        self.assertEqual(descifrar(cifrar(RUC_PRUEBA)), RUC_PRUEBA)

    def test_descifrar_dado_un_texto_que_no_es_token_cuando_se_descifra_entonces_lanza_errordecifrado(self):
        """No se devuelve el valor crudo: eso esconderían las filas sin migrar."""
        with self.assertRaises(ErrorDeCifrado):
            descifrar("1790012345001")

    def test_indice_ciego_dado_el_mismo_valor_cuando_se_calcula_dos_veces_entonces_coincide(self):
        self.assertEqual(indice_ciego(RUC_PRUEBA), indice_ciego(RUC_PRUEBA))

    def test_indice_ciego_dado_el_valor_con_espacios_cuando_se_calcula_entonces_coincide_con_el_normalizado(self):
        self.assertEqual(indice_ciego(f"  {RUC_PRUEBA} "), indice_ciego(RUC_PRUEBA))

    def test_indice_ciego_dado_valores_distintos_cuando_se_calculan_entonces_difieren(self):
        self.assertNotEqual(indice_ciego(RUC_PRUEBA), indice_ciego("0912345678"))

    @override_settings(BLIND_INDEX_KEY="otra-clave-distinta-para-la-prueba")
    def test_indice_ciego_dado_otra_clave_cuando_se_calcula_entonces_cambia(self):
        """Prueba a la vez que `override_settings` invalida la caché de `crypto`."""
        con_otra_clave = indice_ciego(RUC_PRUEBA)

        self.assertEqual(len(con_otra_clave), 64)
        self.assertNotEqual(con_otra_clave, "")

    def test_normalizar_identificacion_dado_texto_con_espacios_cuando_se_normaliza_entonces_lo_recorta(self):
        self.assertEqual(normalizar_identificacion(f"  {RUC_PRUEBA}\t"), RUC_PRUEBA)

    def test_normalizar_identificacion_dado_un_numero_cuando_se_normaliza_entonces_devuelve_texto(self):
        self.assertEqual(normalizar_identificacion(912345678), "912345678")

    def test_descifrar_dado_un_token_ilegible_cuando_falla_entonces_registra_el_error_sin_el_valor(self):
        with self.assertLogs("gestion.crypto", level="ERROR") as registro, self.assertRaises(ErrorDeCifrado):
            descifrar(RUC_PRUEBA)

        self.assertNotIn(RUC_PRUEBA, "\n".join(registro.output))

    def test_descifrar_dado_registrar_falso_cuando_falla_entonces_no_deja_error_en_el_registro(self):
        with self.assertNoLogs("gestion.crypto", level="ERROR"), self.assertRaises(ErrorDeCifrado):
            descifrar(RUC_PRUEBA, registrar=False)


class LogsDelCampoCifradoTestCase(TestCase):
    """RS-19: un dato ilegible deja traza con el modelo y el campo, nunca con el valor."""

    def test_cliente_dado_una_fila_ilegible_cuando_se_lee_entonces_registra_modelo_y_campo_sin_el_valor(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=SedeFactory())
        with connection.cursor() as cursor:
            cursor.execute("UPDATE gestion_cliente SET ruc_cedula = %s WHERE id = %s", ["0912345678", cliente.pk])

        with self.assertLogs("gestion.model_fields", level="ERROR") as registro, self.assertRaises(ErrorDeCifrado):
            Cliente.objects.get(pk=cliente.pk)

        salida = "\n".join(registro.output)
        self.assertIn("Cliente.ruc_cedula", salida)
        self.assertNotIn("0912345678", salida)


class RotacionDeClavesTestCase(TestCase):
    """RS-19: `FIELD_ENCRYPTION_KEYS` es una lista para poder rotar sin parar el sistema."""

    def test_rotacion_dado_un_valor_cifrado_con_la_clave_vieja_cuando_se_añade_una_nueva_entonces_sigue_legible(self):
        clave_vieja = generar_clave()
        clave_nueva = generar_clave()
        with override_settings(FIELD_ENCRYPTION_KEYS=[clave_vieja]):
            token = cifrar(RUC_PRUEBA)

        # La nueva va primera (cifra), la vieja se conserva para poder descifrar.
        with override_settings(FIELD_ENCRYPTION_KEYS=[clave_nueva, clave_vieja]):
            self.assertEqual(descifrar(token), RUC_PRUEBA)

    def test_rotacion_dado_un_valor_cifrado_con_una_clave_retirada_cuando_se_lee_entonces_lanza_errordecifrado(self):
        clave_vieja = generar_clave()
        clave_nueva = generar_clave()
        with override_settings(FIELD_ENCRYPTION_KEYS=[clave_vieja]):
            token = cifrar(RUC_PRUEBA)

        with override_settings(FIELD_ENCRYPTION_KEYS=[clave_nueva]), self.assertRaises(ErrorDeCifrado):
            descifrar(token)


class ComandoCifrarDatosPersonalesTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()

    def _escribir_en_claro(self, cliente, valor):
        """Simula una fila escrita por SQL directo o por una restauración parcial."""
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE gestion_cliente SET ruc_cedula = %s, ruc_cedula_hash = %s WHERE id = %s",
                [valor, "", cliente.pk],
            )

    def test_comando_dado_todo_cifrado_cuando_solo_verifica_entonces_termina_sin_error(self):
        ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)

        call_command("cifrar_datos_personales")  # no lanza

    def test_comando_dado_una_fila_en_claro_cuando_solo_verifica_entonces_lanza_commanderror(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)
        self._escribir_en_claro(cliente, "0912345678")

        with self.assertRaises(CommandError):
            call_command("cifrar_datos_personales")

    def test_comando_dado_una_fila_en_claro_cuando_repara_entonces_la_cifra_y_la_indexa(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)
        self._escribir_en_claro(cliente, "0912345678")

        call_command("cifrar_datos_personales", "--reparar")

        guardado = _columna_cruda(Cliente, "ruc_cedula", cliente.pk)
        self.assertTrue(guardado.startswith("gAAAAA"))
        self.assertEqual(Cliente.objects.get(pk=cliente.pk).ruc_cedula, "0912345678")
        self.assertEqual(Cliente.objects.por_identificacion("0912345678").count(), 1)

    def test_comando_dado_un_indice_desfasado_cuando_recalcula_entonces_lo_corrige(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE gestion_cliente SET ruc_cedula_hash = %s WHERE id = %s",
                ["0" * 64, cliente.pk],
            )

        call_command("cifrar_datos_personales", "--recalcular-indices")

        self.assertEqual(Cliente.objects.por_identificacion(RUC_PRUEBA).count(), 1)

    @patch("gestion.management.commands.cifrar_datos_personales.LOTE", 2)
    def test_comando_dado_mas_filas_que_el_tamano_del_lote_cuando_repara_entonces_las_corrige_todas(self):
        rucs = ["0912345671", "0912345672", "0912345673", "0912345674", "0912345675"]
        for ruc in rucs:
            self._escribir_en_claro(ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=SedeFactory()), ruc)

        call_command("cifrar_datos_personales", "--reparar")

        for ruc in rucs:
            self.assertEqual(Cliente.objects.por_identificacion(ruc).count(), 1)
        call_command("cifrar_datos_personales")  # verificación posterior limpia

    def test_comando_dado_una_fila_en_claro_cuando_repara_entonces_registra_la_clave_primaria_sin_el_valor(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)
        self._escribir_en_claro(cliente, "0912345678")

        with self.assertLogs("gestion.management.commands.cifrar_datos_personales", level="INFO") as registro:
            call_command("cifrar_datos_personales", "--reparar")

        salida = "\n".join(registro.output)
        self.assertIn(f"pk={cliente.pk}", salida)
        self.assertIn("Cliente.ruc_cedula", salida)
        self.assertNotIn("0912345678", salida)

    def test_comando_dado_un_token_de_clave_retirada_cuando_verifica_entonces_registra_error_con_pk(self):
        cliente = ClienteFactory(ruc_cedula=RUC_PRUEBA, sede=self.sede)
        with override_settings(FIELD_ENCRYPTION_KEYS=[generar_clave()]):
            token_ajeno = cifrar("0912345678")
        with connection.cursor() as cursor:
            cursor.execute("UPDATE gestion_cliente SET ruc_cedula = %s WHERE id = %s", [token_ajeno, cliente.pk])

        with (
            self.assertLogs("gestion.management.commands.cifrar_datos_personales", level="ERROR") as registro,
            self.assertRaises(CommandError),
        ):
            call_command("cifrar_datos_personales")

        salida = "\n".join(registro.output)
        self.assertIn(f"pk={cliente.pk}", salida)
        self.assertNotIn(token_ajeno, salida)


class ApiClientesConRucCifradoTestCase(TestCase):
    """El cifrado no debe cambiar el contrato de la API (RC-09: el esquema no se mueve)."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.admin = CustomUserFactory(groups=["admin_sistemas"], sede=self.sede)
        self.client.force_authenticate(user=self.admin)

    def _cuerpo(self, ruc, nombre="Cliente API QA"):
        return {
            "nombre_razon_social": nombre,
            "ruc_cedula": ruc,
            "direccion_envio": "Calle QA",
            "limite_credito": "500.00",
            "nivel_precio": "normal",
            "sede": self.sede.id,
        }

    def test_api_clientes_dado_un_ruc_cuando_se_crea_y_se_lee_entonces_lo_devuelve_en_claro(self):
        creacion = self.client.post(reverse("cliente-list"), self._cuerpo(RUC_PRUEBA), format="json")
        self.assertEqual(creacion.status_code, status.HTTP_201_CREATED)

        detalle = self.client.get(reverse("cliente-detail", args=[creacion.data["id"]]))

        self.assertEqual(detalle.status_code, status.HTTP_200_OK)
        self.assertEqual(detalle.data["ruc_cedula"], RUC_PRUEBA)

    def test_api_clientes_dado_un_ruc_duplicado_en_la_sede_cuando_se_crea_entonces_responde_400(self):
        self.client.post(reverse("cliente-list"), self._cuerpo(RUC_PRUEBA), format="json")

        repetido = self.client.post(reverse("cliente-list"), self._cuerpo(RUC_PRUEBA, "Otro nombre SA"), format="json")

        self.assertEqual(repetido.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_clientes_dado_un_ruc_mas_largo_que_el_maximo_cuando_se_crea_entonces_responde_400(self):
        """BVA: `max_length=20` sigue validando el valor en claro, no el cifrado."""
        respuesta = self.client.post(reverse("cliente-list"), self._cuerpo("9" * 21), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
