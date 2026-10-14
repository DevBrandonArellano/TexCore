#!/usr/bin/env python3
"""
Pruebas de humo de TexCore contra un stack levantado, a través de nginx.

Las ejecuta el staging efímero del release (`.github/workflows/release.yml`) antes de
pedir la aprobación de producción, y sirven igual contra cualquier instalación:

    python3 scripts/smoke_test.py https://localhost:8443 --http http://localhost:8080
    python3 scripts/smoke_test.py https://192.168.1.10 --prefijo e1_     # usuarios de la simulación

Verifica:
  1. el puerto 80 redirige con 301 a HTTPS (si se pasa --http);
  2. la salud del backend y de scanning_service;
  3. por cada uno de los 11 roles: inicio de sesión y una consulta propia del rol.

Solo usa la biblioteca estándar: corre en el runner sin instalar nada.
"""

import argparse
import http.cookiejar
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Rol → consulta que debe responder 200 con su sesión.
CONSULTA_POR_ROL = {
    "admin_sistemas": "/api/sedes/",
    "admin_sede": "/api/areas/",
    "ejecutivo": "/api/inventory/sugerencias-compra/ultima-ejecucion/",
    "jefe_planta": "/api/planes-produccion/",
    "jefe_area": "/api/maquinas/",
    "tintorero": "/api/formula-colors/",
    "operario": "/api/ordenes-produccion/",
    "empaquetado": "/api/lotes-produccion/",
    "bodeguero": "/api/inventory/alertas-stock/",
    "despacho": "/api/pedidos-venta/",
    "vendedor": "/api/clientes/",
}

# nginx limita /api/token/ a 5 por minuto por IP (ráfaga de 3): ante un 429 se espera.
ESPERA_TRAS_429 = 15
REINTENTOS_429 = 8


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _contexto_tls(verificar: bool) -> ssl.SSLContext:
    if verificar:
        return ssl.create_default_context()
    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE  # certificado autofirmado del staging o de la red interna
    return contexto


def _url_valida(url):
    """Solo http:// y https://: un `file://` leería un archivo del runner."""
    return urllib.parse.urlparse(url).scheme.lower() in ("http", "https")


def _abrir(opener, url, datos=None):
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    # El esquema se valida en main() antes de llegar aquí: solo http y https.
    peticion = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": "application/json"})  # noqa: S310
    try:
        with opener.open(peticion, timeout=60) as respuesta:
            return respuesta.status, respuesta.read(), respuesta.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def comprobar_redireccion(url_http: str) -> None:
    opener = urllib.request.build_opener(_SinRedireccion)
    estado, _, cabeceras = _abrir(opener, url_http + "/")
    destino = cabeceras.get("Location", "")
    if estado != 301 or not destino.startswith("https://"):
        raise AssertionError(f"HTTP debía responder 301 hacia https://; respondió {estado} {destino!r}")


def comprobar_salud(base: str, contexto) -> None:
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=contexto))
    for ruta in ("/api/health/", "/api/scanning/health"):
        estado, cuerpo, _ = _abrir(opener, base + ruta)
        if estado != 200:
            raise AssertionError(f"{ruta} respondió {estado}: {cuerpo[:200]!r}")


def comprobar_rol(base: str, contexto, rol: str, ruta: str, prefijo: str, contrasena: str) -> None:
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=contexto),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )
    usuario = f"{prefijo}{rol}"
    for _ in range(REINTENTOS_429):
        estado, cuerpo, _ = _abrir(opener, base + "/api/token/", {"username": usuario, "password": contrasena})
        if estado != 429:
            break
        time.sleep(ESPERA_TRAS_429)
    if estado != 200:
        raise AssertionError(f"login de {usuario} respondió {estado}: {cuerpo[:200]!r}")
    estado, cuerpo, _ = _abrir(opener, base + ruta)
    if estado != 200:
        raise AssertionError(f"{usuario} GET {ruta} respondió {estado}: {cuerpo[:200]!r}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base", help="URL HTTPS de nginx, p. ej. https://localhost:8443")
    parser.add_argument("--http", help="URL HTTP de nginx para comprobar la redirección 301")
    parser.add_argument("--prefijo", default="user_", help="prefijo de los usuarios por rol (seed_data: user_)")
    parser.add_argument("--contrasena", default="password123", help="contraseña de los usuarios por rol")
    parser.add_argument("--verificar-tls", action="store_true", help="exigir un certificado válido")
    args = parser.parse_args(argv)

    for nombre, url in (("base", args.base), ("--http", args.http)):
        if url and not _url_valida(url):
            print(f"{nombre}: solo se aceptan URL http:// o https:// ({url!r})", file=sys.stderr)
            return 2

    base = args.base.rstrip("/")
    contexto = _contexto_tls(args.verificar_tls)
    pruebas = []
    if args.http:
        pruebas.append(("redirección HTTP → HTTPS", lambda: comprobar_redireccion(args.http.rstrip("/"))))
    pruebas.append(("salud de backend y scanning", lambda: comprobar_salud(base, contexto)))
    for rol, ruta in CONSULTA_POR_ROL.items():
        pruebas.append(
            (
                f"rol {rol}: login y GET {ruta}",
                lambda r=rol, p=ruta: comprobar_rol(base, contexto, r, p, args.prefijo, args.contrasena),
            )
        )

    fallos = 0
    for nombre, prueba in pruebas:
        try:
            prueba()
            print(f"OK    {nombre}")
        except AssertionError as error:
            fallos += 1
            print(f"FALLA {nombre}: {error}")
    print(f"\n{len(pruebas) - fallos}/{len(pruebas)} pruebas de humo en verde")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
