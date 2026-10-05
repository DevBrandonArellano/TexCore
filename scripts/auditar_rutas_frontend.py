"""Auditoría de rutas del backend sin consumidor en el frontend.

Lista las rutas `api/` de Django y busca, para cada una, una llamada en
`frontend/src` (sin archivos de prueba). Imprime las rutas sin consumidor y
termina con código 1 si hay alguna.

Uso (desde la raíz del repo):
    DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python scripts/auditar_rutas_frontend.py

Una ruta cuenta como consumida si alguna URL del frontend coincide con ella.
Un parámetro de la ruta coincide con `${...}` o con un valor literal. Un
segmento fijo coincide con su texto o, salvo el primero (el recurso), con
`${...}` cuando ese texto aparece como literal en el mismo archivo, p. ej.
`/maquinas/${m.id}/${accion}/` con `accion: 'oee' | 'eficiencia'`.
"""
import os
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TexCore.settings_test_local')

import django  # noqa: E402 — tras django.setup()

django.setup()

from django.urls import URLPattern, URLResolver, get_resolver  # noqa: E402 — tras django.setup()

# Rutas con consumidor fuera del frontend.
EXCLUIDAS = (
    re.compile(r'^api/internal/'),         # microservicios (JWT de servicio)
    re.compile(r'^api/health/$'),          # healthcheck de Docker
    re.compile(r'^api/(schema|docs)/$'),   # OpenAPI, herramienta de desarrollo
    re.compile(r'^api/(inventory/)?$'),    # raíz navegable del router
)

GRUPO = re.compile(r'\(\?P<[^>]+>(?:[^()]|\([^()]*\))*\)|<[^>]+>')
PARAMETRO = r"(?:\$\{[^}]+\}|[A-Za-z0-9_\-]+)"
INTERPOLACION = r"\$\{[^}]+\}"
FIN = r"/?(?:[?'\"`]|\$\{)"


def rutas_api():
    def recorrer(patrones, prefijo=''):
        for p in patrones:
            if isinstance(p, URLResolver):
                yield from recorrer(p.url_patterns, prefijo + str(p.pattern))
            elif isinstance(p, URLPattern):
                yield prefijo + str(p.pattern), p.callback
    for ruta, vista in recorrer(get_resolver().url_patterns):
        if 'format' in ruta or not ruta.startswith('api/'):
            continue
        if any(e.search(ruta) for e in EXCLUIDAS):
            continue
        yield ruta, vista


def segmentos(ruta):
    limpia = GRUPO.sub('<p>', ruta[len('api/'):].replace('^', '').replace('$', ''))
    return [s for s in limpia.split('/') if s]


def regex_para(segs, texto):
    partes = []
    for i, s in enumerate(segs):
        if s == '<p>':
            partes.append(PARAMETRO)
        elif i > 0 and re.search(rf"['\"`]{re.escape(s)}['\"`]", texto):
            partes.append(rf"(?:{re.escape(s)}|{INTERPOLACION})")
        else:
            partes.append(re.escape(s))
    return re.compile('/' + '/'.join(partes) + FIN)


def fuentes_frontend():
    for p in (RAIZ / 'frontend' / 'src').rglob('*'):
        if p.suffix not in ('.ts', '.tsx'):
            continue
        if '.test.' in p.name or '__tests__' in p.parts or 'mocks' in p.parts:
            continue
        yield p.read_text(errors='ignore')


def main():
    textos = list(fuentes_frontend())
    sin_consumidor = []
    for ruta, vista in rutas_api():
        segs = segmentos(ruta)
        if not any(regex_para(segs, t).search(t) for t in textos):
            acciones = getattr(vista, 'actions', None)
            sin_consumidor.append((ruta, acciones))
    for ruta, acciones in sin_consumidor:
        print(f'{ruta}\t{acciones or ""}')
    print(f'\n{len(sin_consumidor)} rutas sin consumidor en el frontend', file=sys.stderr)
    return 1 if sin_consumidor else 0


if __name__ == '__main__':
    sys.exit(main())
