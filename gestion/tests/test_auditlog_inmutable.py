"""
TEX-09 CA-2: el registro de auditoría es inmutable en el propio modelo.

Hasta el 7-oct-2026 la inmutabilidad dependía solo de no exponer un endpoint de escritura
(hallazgo M-5 de la auditoría del backlog): cualquier código podía editar o borrar un
AuditLog con el ORM. Ahora `save()` sobre un registro existente, `delete()` y las
operaciones masivas `update()`/`delete()` del manager lanzan RegistroAuditoriaInmutable.

Las acciones referenciales de la base siguen funcionando: borrar un usuario deja sus
registros con usuario NULL (SET_NULL), sin borrar la auditoría.

Técnicas ISTQB: partición de equivalencia sobre las vías de escritura del ORM y prueba
de transición (alta → intento de cambio).
"""
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from gestion.models import AuditLog, Producto, RegistroAuditoriaInmutable
from gestion.tests.factories import CustomUserFactory


class AuditLogInmutableTestCase(TestCase):
    def setUp(self):
        self.usuario = CustomUserFactory()
        self.log = AuditLog.objects.create(
            usuario=self.usuario, content_type=ContentType.objects.get_for_model(Producto), object_id=1,
            accion='UPDATE', justificacion='Ajuste original')

    def test_auditlog_dado_registro_nuevo_cuando_se_crea_entonces_se_guarda(self):
        self.assertTrue(AuditLog.objects.filter(pk=self.log.pk).exists())

    def test_auditlog_dado_registro_existente_cuando_se_edita_y_guarda_entonces_lanza(self):
        self.log.justificacion = 'Texto alterado'
        with self.assertRaises(RegistroAuditoriaInmutable):
            self.log.save()
        self.log.refresh_from_db()
        self.assertEqual(self.log.justificacion, 'Ajuste original')

    def test_auditlog_dado_registro_cuando_se_borra_entonces_lanza_y_se_conserva(self):
        with self.assertRaises(RegistroAuditoriaInmutable):
            self.log.delete()
        self.assertTrue(AuditLog.objects.filter(pk=self.log.pk).exists())

    def test_auditlog_dado_queryset_cuando_update_masivo_entonces_lanza(self):
        with self.assertRaises(RegistroAuditoriaInmutable):
            AuditLog.objects.filter(pk=self.log.pk).update(justificacion='Masivo')
        self.log.refresh_from_db()
        self.assertEqual(self.log.justificacion, 'Ajuste original')

    def test_auditlog_dado_queryset_cuando_delete_masivo_entonces_lanza(self):
        with self.assertRaises(RegistroAuditoriaInmutable):
            AuditLog.objects.all().delete()
        self.assertTrue(AuditLog.objects.filter(pk=self.log.pk).exists())

    def test_auditlog_dado_usuario_borrado_cuando_se_consulta_entonces_conserva_el_registro_sin_usuario(self):
        self.usuario.delete()
        self.log.refresh_from_db()
        self.assertIsNone(self.log.usuario_id)
