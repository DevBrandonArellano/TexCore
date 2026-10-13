"""
Pruebas complementarias de inventory/views.py — AuditLogViewSet.
(Las vistas del MRP se prueban en test_mrp_views.py.)

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): sin permiso / admin_sede / admin_sistemas
  / superuser, con y sin filtro sede_id.
- Caja blanca: rama `qs.none()` cuando el usuario no tiene rol de auditoría
  o admin_sede sin sede asignada.
"""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import AuditLog
from gestion.tests.factories import CustomUserFactory, SedeFactory


class AuditLogViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()
        # Usuarios creados ANTES de los AuditLog propios: CustomUserFactory dispara
        # señales de auditoría (creación de usuario) que insertan sus propios
        # AuditLog — por eso las aserciones de abajo verifican membresía de ids
        # concretos en vez de conteos totales (contaminados por esas señales).
        self.usuario_sede = CustomUserFactory(sede=self.sede)
        # Actor DISTINTO para el log de "otra sede": get_queryset filtra por
        # (usuario__sede_id == mi_sede) OR (object_sede_id == mi_sede). Si
        # ambos logs comparten el mismo usuario (de self.sede), el de otra
        # sede calzaría igual por la rama usuario__sede_id.
        self.usuario_otra_sede = CustomUserFactory(sede=self.otra_sede)
        self.content_type = ContentType.objects.get_for_model(AuditLog)
        self.log_sede = AuditLog.objects.create(
            usuario=self.usuario_sede, content_type=self.content_type, object_id=1,
            object_sede_id=self.sede.id, accion='UPDATE',
        )
        self.log_otra_sede = AuditLog.objects.create(
            usuario=self.usuario_otra_sede, content_type=self.content_type, object_id=2,
            object_sede_id=self.otra_sede.id, accion='UPDATE',
        )

    @staticmethod
    def _ids(resp):
        return [item['id'] for item in resp.data['results']]

    def test_list_dado_usuario_sin_rol_de_auditoria_cuando_get_entonces_vacio(self):
        operario = CustomUserFactory(groups=['operario'])
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('audit-log-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 0)

    def test_list_dado_admin_sede_sin_sede_asignada_cuando_get_entonces_vacio(self):
        admin_sede = CustomUserFactory(groups=['admin_sede'], sede=None)
        self.client.force_authenticate(user=admin_sede)
        resp = self.client.get(reverse('audit-log-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 0)

    def test_list_dado_admin_sede_cuando_get_entonces_solo_su_sede(self):
        admin_sede = CustomUserFactory(groups=['admin_sede'], sede=self.sede)
        self.client.force_authenticate(user=admin_sede)
        resp = self.client.get(reverse('audit-log-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.log_sede.id, ids)
        self.assertNotIn(self.log_otra_sede.id, ids)

    def test_list_dado_admin_sistemas_con_filtro_sede_id_cuando_get_entonces_filtra(self):
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('audit-log-list'), {'sede_id': self.otra_sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.log_otra_sede.id, ids)
        self.assertNotIn(self.log_sede.id, ids)

    def test_list_dado_admin_sistemas_sin_filtro_cuando_get_entonces_ve_todo(self):
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('audit-log-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.log_sede.id, ids)
        self.assertIn(self.log_otra_sede.id, ids)

    def test_list_dado_logs_viejos_cuando_get_entonces_excluye_mas_de_30_dias(self):
        # Caja blanca: rama `qs.filter(fecha_hora__gte=umbral)`
        viejo = AuditLog.objects.create(
            usuario=self.usuario_sede, content_type=self.content_type, object_id=3,
            object_sede_id=self.sede.id, accion='DELETE',
        )
        # _base_manager: el AuditLog es inmutable por el ORM normal (TEX-09); la prueba fecha el registro.
        AuditLog._base_manager.filter(pk=viejo.pk).update(fecha_hora=timezone.now() - timedelta(days=45))

        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('audit-log-list'))
        ids = [item['id'] for item in resp.data['results']]
        self.assertNotIn(viejo.id, ids)
