"""
GET /api/inventory/audit-logs/: alcance por sede, búsqueda y consulta indexable.

Hallazgo de la prueba de carga del 2026-10-06: el COUNT de la paginación consumía el 75 %
de la CPU de SQL Server. El filtro `usuario__sede_id OR object_sede_id` unía con el
usuario; ahora filtra por dos columnas de gestion_auditlog (usuario_sede_id y
object_sede_id), cubiertas por el índice por fecha idx_audit_fecha_sedes (gestion/0008).

También se cubre un hueco encontrado al revisar la pantalla: AuditLogViewer envía
`?search=` y el backend lo ignoraba.

Técnica ISTQB: partición de equivalencia por rol (OWASP A01) y caja blanca de la consulta.
"""
import re

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from gestion.models import AuditLog, Producto
from gestion.tests.factories import CustomUserFactory, SedeFactory

URL = '/api/inventory/audit-logs/'


class AuditLogsSedeTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()
        self.operario = CustomUserFactory(sede=self.sede, username='operario_propio')
        self.operario_otra = CustomUserFactory(sede=self.otra_sede, username='operario_ajeno')
        ct = ContentType.objects.get_for_model(Producto)

        def log(usuario, object_sede_id):
            return AuditLog.objects.create(
                usuario=usuario, content_type=ct, object_id=1,
                object_sede_id=object_sede_id, accion='UPDATE')

        self.por_usuario = log(self.operario, None)
        self.por_objeto = log(None, self.sede.pk)
        self.ajeno = log(self.operario_otra, self.otra_sede.pk)
        self.propios = {self.por_usuario.pk, self.por_objeto.pk, self.ajeno.pk}

    def _ids(self, usuario, **params):
        """Logs de la prueba visibles; crear usuarios también deja logs (señal) y se ignoran."""
        self.client.force_authenticate(user=usuario)
        resp = self.client.get(URL, params)
        self.assertEqual(resp.status_code, 200)
        return {f['id'] for f in resp.data['results']} & self.propios

    def test_audit_logs_dado_admin_sede_cuando_lista_entonces_ve_su_sede_por_usuario_o_por_objeto(self):
        admin_sede = CustomUserFactory(sede=self.sede, groups=['admin_sede'])
        self.assertEqual(self._ids(admin_sede), {self.por_usuario.pk, self.por_objeto.pk})

    def test_audit_logs_dado_admin_sede_cuando_pide_otra_sede_entonces_sigue_acotado_a_la_suya(self):
        admin_sede = CustomUserFactory(sede=self.sede, groups=['admin_sede'])
        self.assertNotIn(self.ajeno.pk, self._ids(admin_sede, sede_id=self.otra_sede.pk))

    def test_audit_logs_dado_admin_sistemas_con_sede_id_cuando_lista_entonces_filtra_esa_sede(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.assertEqual(self._ids(admin, sede_id=self.otra_sede.pk), {self.ajeno.pk})

    def test_audit_logs_dado_admin_sistemas_sin_sede_id_cuando_lista_entonces_ve_todas(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.assertEqual(self._ids(admin), {self.por_usuario.pk, self.por_objeto.pk, self.ajeno.pk})

    def test_audit_logs_dado_rol_sin_permiso_cuando_lista_entonces_vacio(self):
        self.assertEqual(self._ids(CustomUserFactory(sede=self.sede, groups=['bodeguero'])), set())

    def test_audit_logs_dado_busqueda_por_usuario_cuando_lista_entonces_filtra(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.assertEqual(self._ids(admin, search='ajeno'), {self.ajeno.pk})

    def test_audit_logs_dado_busqueda_por_tabla_cuando_lista_entonces_filtra(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.assertEqual(self._ids(admin, search='producto'), {self.por_usuario.pk, self.por_objeto.pk, self.ajeno.pk})
        self.assertEqual(self._ids(admin, search='zzz-sin-coincidencia'), set())

    def test_audit_logs_dado_busqueda_numerica_cuando_lista_entonces_filtra_por_id_del_registro(self):
        AuditLog._base_manager.filter(pk=self.ajeno.pk).update(object_id=4242)
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.assertEqual(self._ids(admin, search='4242'), {self.ajeno.pk})

    def test_audit_logs_dado_filtro_de_sede_cuando_cuenta_entonces_no_une_con_el_usuario(self):
        admin_sede = CustomUserFactory(sede=self.sede, groups=['admin_sede'])
        self.client.force_authenticate(user=admin_sede)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(URL)
        # SQL Server emite COUNT_BIG(*); SQLite, COUNT(*).
        conteos = [q['sql'] for q in ctx.captured_queries
                   if re.search(r'COUNT(_BIG)?\(', q['sql'], re.IGNORECASE) and 'gestion_auditlog' in q['sql']]
        self.assertEqual(len(conteos), 1)
        self.assertNotIn('gestion_customuser', conteos[0])
        self.assertIn('usuario_sede_id', conteos[0])


class AuditLogsFiltrosTestCase(TestCase):
    """
    TEX-52 CA-1: filtrar por usuario, fecha o tipo de operación. Hasta el 7-oct-2026 solo
    había búsqueda de texto y un recorte fijo de 30 días: los registros más antiguos no
    se podían consultar (hallazgo M-6 de la auditoría del backlog).

    Técnicas ISTQB: partición de equivalencia (con y sin rango, acción válida e inválida)
    y valores límite en los extremos del rango.
    """

    def setUp(self):
        from datetime import datetime, timedelta

        from django.utils import timezone

        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()
        ct = ContentType.objects.get_for_model(Producto)
        hoy = timezone.localdate()
        self.hoy = hoy

        def log(dias_atras, accion='UPDATE', sede=None):
            registro = AuditLog.objects.create(content_type=ct, object_id=1, accion=accion,
                                               object_sede_id=(sede or self.sede).pk)
            momento = timezone.make_aware(datetime.combine(hoy - timedelta(days=dias_atras), datetime.min.time()))
            AuditLog._base_manager.filter(pk=registro.pk).update(fecha_hora=momento.replace(hour=12))
            return registro

        self.reciente = log(1)
        self.creacion_reciente = log(2, accion='CREATE')
        self.antiguo = log(90)
        self.antiguo_borrado = log(95, accion='DELETE')
        self.ajeno_antiguo = log(90, sede=self.otra_sede)
        self.propios = {r.pk for r in (self.reciente, self.creacion_reciente, self.antiguo,
                                       self.antiguo_borrado, self.ajeno_antiguo)}
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])

    def _dia(self, dias_atras):
        from datetime import timedelta
        return (self.hoy - timedelta(days=dias_atras)).isoformat()

    def _get(self, usuario, **params):
        self.client.force_authenticate(user=usuario)
        return self.client.get(URL, params)

    def _ids(self, usuario, **params):
        resp = self._get(usuario, **params)
        self.assertEqual(resp.status_code, 200, resp.data)
        return {f['id'] for f in resp.data['results']} & self.propios

    def test_audit_logs_dado_sin_fechas_cuando_lista_entonces_ultimos_30_dias(self):
        self.assertEqual(self._ids(self.admin), {self.reciente.pk, self.creacion_reciente.pk})

    def test_audit_logs_dado_fecha_desde_antigua_cuando_lista_entonces_incluye_registros_viejos(self):
        self.assertEqual(self._ids(self.admin, fecha_desde=self._dia(100)), self.propios)

    def test_audit_logs_dado_rango_cerrado_cuando_lista_entonces_solo_ese_rango(self):
        ids = self._ids(self.admin, fecha_desde=self._dia(96), fecha_hasta=self._dia(89))
        self.assertEqual(ids, {self.antiguo.pk, self.antiguo_borrado.pk, self.ajeno_antiguo.pk})

    def test_audit_logs_dado_limites_del_rango_cuando_lista_entonces_incluye_ambos_dias(self):
        # BVA: desde y hasta el mismo día del registro → incluido (el día completo).
        self.assertEqual(self._ids(self.admin, fecha_desde=self._dia(90), fecha_hasta=self._dia(90)),
                         {self.antiguo.pk, self.ajeno_antiguo.pk})
        self.assertEqual(self._ids(self.admin, fecha_desde=self._dia(89), fecha_hasta=self._dia(89)), set())

    def test_audit_logs_dado_solo_fecha_hasta_cuando_lista_entonces_desde_el_inicio(self):
        self.assertEqual(self._ids(self.admin, fecha_hasta=self._dia(80)),
                         {self.antiguo.pk, self.antiguo_borrado.pk, self.ajeno_antiguo.pk})

    def test_audit_logs_dado_accion_cuando_lista_entonces_solo_ese_tipo(self):
        self.assertEqual(self._ids(self.admin, accion='CREATE'), {self.creacion_reciente.pk})
        self.assertEqual(self._ids(self.admin, accion='DELETE', fecha_desde=self._dia(100)),
                         {self.antiguo_borrado.pk})

    def test_audit_logs_dado_accion_invalida_cuando_lista_entonces_400(self):
        self.assertEqual(self._get(self.admin, accion='HACKEO').status_code, 400)

    def test_audit_logs_dado_fecha_invalida_cuando_lista_entonces_400(self):
        self.assertEqual(self._get(self.admin, fecha_desde='31/12/2026').status_code, 400)

    def test_audit_logs_dado_rango_invertido_cuando_lista_entonces_400(self):
        self.assertEqual(self._get(self.admin, fecha_desde=self._dia(1), fecha_hasta=self._dia(10)).status_code, 400)

    def test_audit_logs_dado_admin_sede_con_rango_antiguo_cuando_lista_entonces_sigue_acotado_a_su_sede(self):
        admin_sede = CustomUserFactory(sede=self.sede, groups=['admin_sede'])
        ids = self._ids(admin_sede, fecha_desde=self._dia(100))
        self.assertNotIn(self.ajeno_antiguo.pk, ids)
        self.assertIn(self.antiguo.pk, ids)
