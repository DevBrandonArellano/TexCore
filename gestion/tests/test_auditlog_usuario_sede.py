"""
AuditLog.usuario_sede_id: sede del usuario que hizo el cambio, guardada al registrarlo.

Hallazgo de la prueba de carga del 2026-10-06: el COUNT de la paginación de
/api/inventory/audit-logs/ consumía el 75 % de la CPU de SQL Server (895 × 603 ms). El
filtro `usuario__sede_id OR object_sede_id` obligaba a unir con el usuario y no podía usar
índices sobre ~1 M de filas. Con la sede del usuario en la propia fila, ambas condiciones
son columnas indexadas de gestion_auditlog.

Técnica ISTQB: partición de equivalencia (usuario con sede, sin sede, sin usuario) y
caja blanca del relleno de filas existentes (migración 0005).
"""
import importlib

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from gestion.models import AuditLog
from gestion.tests.factories import CustomUserFactory, ProductoFactory, SedeFactory


def _log(**campos):
    return AuditLog.objects.create(
        content_type=ContentType.objects.get_for_model(AuditLog),
        object_id=1,
        accion='UPDATE',
        **campos,
    )


class AuditLogUsuarioSedeTestCase(TestCase):
    def test_auditlog_dado_usuario_con_sede_cuando_se_registra_entonces_guarda_su_sede(self):
        usuario = CustomUserFactory()
        self.assertEqual(_log(usuario=usuario).usuario_sede_id, usuario.sede_id)

    def test_auditlog_dado_cambio_sin_usuario_cuando_se_registra_entonces_sede_nula(self):
        self.assertIsNone(_log(usuario=None).usuario_sede_id)

    def test_auditlog_dado_usuario_sin_sede_cuando_se_registra_entonces_sede_nula(self):
        self.assertIsNone(_log(usuario=CustomUserFactory(sede=None)).usuario_sede_id)

    def test_auditlog_dado_usuario_que_cambia_de_sede_cuando_se_consulta_entonces_conserva_la_del_cambio(self):
        usuario = CustomUserFactory()
        sede_original = usuario.sede_id
        log = _log(usuario=usuario)
        usuario.sede = SedeFactory()
        usuario.save()
        log.refresh_from_db()
        self.assertEqual(log.usuario_sede_id, sede_original)

    def test_auditlog_dado_modelo_auditable_cuando_se_guarda_entonces_el_log_lleva_la_sede_del_usuario(self):
        from gestion import middleware
        usuario = CustomUserFactory()
        middleware._local.user = usuario
        try:
            producto = ProductoFactory()
        finally:
            middleware._local.__dict__.pop('user', None)
        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(producto), object_id=producto.pk).latest('id')
        self.assertEqual(log.usuario_id, usuario.pk)
        self.assertEqual(log.usuario_sede_id, usuario.sede_id)


class RellenoUsuarioSedeTestCase(TestCase):
    """Caja blanca del RunPython de la migración 0005 (localmente se corre --nomigrations)."""

    def setUp(self):
        self.migracion = importlib.import_module('gestion.migrations.0005_rellenar_auditlog_usuario_sede')

    def test_relleno_dado_logs_previos_sin_sede_cuando_corre_entonces_copia_la_del_usuario(self):
        usuario = CustomUserFactory()
        sin_usuario = _log(usuario=None)
        previos = [_log(usuario=usuario) for _ in range(5)]
        AuditLog._base_manager.filter(pk__in=[p.pk for p in previos]).update(usuario_sede_id=None)

        self.migracion.rellenar_usuario_sede(apps, None, tamano_lote=2)

        self.assertEqual(
            set(AuditLog.objects.filter(pk__in=[p.pk for p in previos]).values_list('usuario_sede_id', flat=True)),
            {usuario.sede_id},
        )
        sin_usuario.refresh_from_db()
        self.assertIsNone(sin_usuario.usuario_sede_id)

    def test_relleno_dado_log_ya_con_sede_cuando_corre_entonces_no_la_cambia(self):
        otra_sede = SedeFactory()
        log = _log(usuario=CustomUserFactory())
        AuditLog._base_manager.filter(pk=log.pk).update(usuario_sede_id=otra_sede.pk)

        self.migracion.rellenar_usuario_sede(apps, None)

        log.refresh_from_db()
        self.assertEqual(log.usuario_sede_id, otra_sede.pk)
