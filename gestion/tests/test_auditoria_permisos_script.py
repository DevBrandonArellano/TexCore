"""
Pruebas de la auditoría de permisos del backend (`scripts/auditar_permisos_backend.py`).

Es la evidencia automática de RNF-02 («100 % de las funcionalidades requieren
autenticación»): el gate falla si aparece una ruta pública fuera de la lista blanca.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): ruta pública autorizada / pública no autorizada / protegida.
- Caja blanca: nombre de permisos compuestos (`|`, `&`, `~`) y vistas de Django sin DRF.
"""

import importlib.util
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

_ruta = Path(settings.BASE_DIR) / "scripts" / "auditar_permisos_backend.py"
_spec = importlib.util.spec_from_file_location("auditar_permisos_backend", _ruta)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_ruta}"
auditoria = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditoria)


class AuditoriaPermisosTest(SimpleTestCase):
    def test_auditar_dado_el_proyecto_cuando_se_recorre_entonces_no_hay_rutas_publicas_sin_autorizar(self):
        sobran = auditoria.publicas_no_autorizadas(auditoria.auditar())
        self.assertEqual([f["ruta"] for f in sobran], [])

    def test_auditar_dado_el_proyecto_cuando_se_recorre_entonces_cada_ruta_de_la_lista_blanca_existe(self):
        # Una entrada que ya no corresponde a una ruta dejaría la lista blanca más ancha de lo debido.
        rutas = {f["ruta"] for f in auditoria.auditar()}
        self.assertEqual(sorted(set(auditoria.RUTAS_PUBLICAS) - rutas), [])

    def test_auditar_dado_el_proyecto_cuando_se_recorre_entonces_toda_ruta_no_publica_declara_permisos(self):
        sin_permisos = [
            f["ruta"] for f in auditoria.auditar() if not f["publica"] and not (f["permisos"] or f["por_accion"])
        ]
        self.assertEqual(sin_permisos, [])

    def test_publicas_dado_ruta_publica_fuera_de_la_lista_cuando_se_filtra_entonces_se_reporta(self):
        filas = [
            {"ruta": "api/token/", "publica": True},
            {"ruta": "api/intrusa/", "publica": True},
            {"ruta": "api/clientes/", "publica": False},
        ]
        self.assertEqual([f["ruta"] for f in auditoria.publicas_no_autorizadas(filas)], ["api/intrusa/"])

    def test_nombre_dado_permisos_compuestos_cuando_se_nombra_entonces_muestra_la_expresion(self):
        self.assertEqual(auditoria.nombre_permiso(IsAuthenticated), "IsAuthenticated")
        self.assertEqual(auditoria.nombre_permiso(IsAuthenticated | IsAdminUser), "(IsAuthenticated|IsAdminUser)")
        self.assertEqual(auditoria.nombre_permiso(IsAuthenticated & AllowAny), "(IsAuthenticated&AllowAny)")
        self.assertEqual(auditoria.nombre_permiso(~IsAdminUser), "~IsAdminUser")

    def test_normalizar_dado_ruta_de_router_cuando_se_normaliza_entonces_queda_con_marcador(self):
        self.assertEqual(auditoria.normalizar("api/^clientes/(?P<pk>[^/.]+)/$"), "api/clientes/<p>/")
        self.assertEqual(auditoria.url_de_prueba("api/clientes/<p>/", "7"), "/api/clientes/7/")
