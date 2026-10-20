"""Auditoría de permisos de las rutas `api/` del backend (RNF-02, OWASP API1/API2).

Recorre todas las rutas de Django y, por cada una, informa la vista, sus clases de
permiso, si es pública (`AllowAny` o sin autenticación) y si filtra por sede. Imprime
un CSV y termina con código 1 si alguna ruta pública no está en la lista blanca
`RUTAS_PUBLICAS`, que es la evidencia de «100 % de las funcionalidades requieren
autenticación».

Uso (desde la raíz del repo):
    DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python scripts/auditar_permisos_backend.py
"""

import csv
import os
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TexCore.settings_test_local")

import django  # noqa: E402 — tras django.setup()
from django.apps import apps  # noqa: E402

# Si Django ya está configurado (el script se importa desde la suite de pruebas),
# no se vuelve a llamar a setup(): reaplica LOGGING con disable_existing_loggers
# y silencia los loggers ya creados.
if not apps.ready:
    django.setup()

from django.urls import URLPattern, URLResolver, get_resolver  # noqa: E402 — tras django.setup()
from rest_framework.permissions import AllowAny  # noqa: E402

# Rutas que son públicas por diseño. Cualquier otra ruta pública rompe el gate.
RUTAS_PUBLICAS = {
    "api/token/": "login: emite la cookie JWT; limitado por nginx (5/min)",
    "api/token/refresh/": "renovación del JWT con la cookie de refresco; limitado por nginx",
    "api/health/": "healthcheck de Docker",
    "api/internal/v1/auth/token/": "credenciales de servicio (secreto del satélite)",
    "api/internal/v1/auth/refresh/": "renovación del token de servicio",
    "api/logs/": "relay de logs del front, también antes del login; acotado y limitado por IP",
}

GRUPO = re.compile(r"\(\?P<[^>]+>(?:[^()]|\([^()]*\))*\)|<[^>]+>")
FILTROS_DE_SEDE = (
    "filtrar_por_sede",
    "filtrar_catalogo_por_sede",
    "filtrar_lotes_por_sede",
    "bodegas_visibles",
    "resolve_sede_scope",
)


def _recorrer(patrones, prefijo=""):
    for p in patrones:
        if isinstance(p, URLResolver):
            yield from _recorrer(p.url_patterns, prefijo + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield prefijo + str(p.pattern), p.callback


def normalizar(ruta):
    """`^clientes/(?P<pk>[^/.]+)/$` → `clientes/<p>/`, igual en rutas `path()` y `re_path()`."""
    return GRUPO.sub("<p>", ruta.replace("^", "").replace("$", "").replace("\\.", "."))


def url_de_prueba(ruta, valor="1"):
    """Ruta lista para pedir en una prueba: cada parámetro se reemplaza por `valor`."""
    return "/" + normalizar(ruta).replace("<p>", valor)


def rutas():
    """Todas las rutas `api/` sin los sufijos de formato (`.json`) de DRF."""
    for ruta, vista in _recorrer(get_resolver().url_patterns):
        if "format" in ruta or not ruta.startswith("api/"):
            continue
        yield normalizar(ruta), vista


def _codigo_de_la_vista(cls):
    import inspect

    try:
        return inspect.getsource(cls)
    except (OSError, TypeError):
        return ""


def nombre_permiso(permiso):
    """Nombre legible de una clase de permiso, incluidas las compuestas con `|`, `&` y `~`."""
    if hasattr(permiso, "__name__"):
        return permiso.__name__
    operador = {"OR": "|", "AND": "&"}.get(getattr(permiso, "operator_class", type(None)).__name__)
    if operador and hasattr(permiso, "op2_class"):
        return f"({nombre_permiso(permiso.op1_class)}{operador}{nombre_permiso(permiso.op2_class)})"
    if hasattr(permiso, "op1_class"):
        return f"~{nombre_permiso(permiso.op1_class)}"
    return type(permiso).__name__


def clasificar(ruta, vista):
    """Datos de seguridad de una ruta: vista, permisos, publica y filtro de sede."""
    cls = getattr(vista, "cls", None)
    if cls is None:
        # Vista de Django sin DRF (p. ej. el healthcheck): no autentica.
        return {
            "ruta": ruta,
            "vista": getattr(vista, "__name__", str(vista)),
            "permisos": "",
            "por_accion": False,
            "publica": True,
            "filtra_sede": False,
        }
    permisos = [nombre_permiso(p) for p in getattr(cls, "permission_classes", [])]
    codigo = _codigo_de_la_vista(cls)
    return {
        "ruta": ruta,
        "vista": cls.__name__,
        "permisos": "+".join(permisos),
        "por_accion": _define_get_permissions(cls),
        "publica": AllowAny in getattr(cls, "permission_classes", []),
        "filtra_sede": any(f in codigo for f in FILTROS_DE_SEDE),
    }


def _define_get_permissions(cls):
    """True si la vista (o una clase propia de su MRO) elige el permiso por acción."""
    return any(
        "get_permissions" in k.__dict__
        for k in cls.__mro__
        if k.__module__.startswith(("gestion", "inventory", "internal_api"))
    )


def auditar():
    return sorted((clasificar(r, v) for r, v in rutas()), key=lambda f: f["ruta"])


def publicas_no_autorizadas(filas):
    return [f for f in filas if f["publica"] and f["ruta"] not in RUTAS_PUBLICAS]


def main():
    filas = auditar()
    escritor = csv.DictWriter(
        sys.stdout, fieldnames=["ruta", "vista", "permisos", "por_accion", "publica", "filtra_sede"]
    )
    escritor.writeheader()
    escritor.writerows(filas)
    sobran = publicas_no_autorizadas(filas)
    for f in sobran:
        print(f"PÚBLICA SIN AUTORIZAR: {f['ruta']} ({f['vista']})", file=sys.stderr)
    print(f"\n{len(filas)} rutas, {len(sobran)} públicas fuera de la lista blanca", file=sys.stderr)
    return 1 if sobran else 0


if __name__ == "__main__":
    sys.exit(main())
