"""HEALTHCHECK del contenedor backend (Dockerfile.prod).

Pide GET /api/health/ a gunicorn dentro del contenedor. El encabezado Host
sale del primer valor de ALLOWED_HOSTS: en producción ALLOWED_HOSTS es el
dominio real, y una petición con Host 127.0.0.1 respondería 400
(DisallowedHost) aunque Django esté sano.

Sale con 0 si responde 200; con 1 en cualquier otro caso.
"""
import os
import sys
import urllib.request

PUERTO = os.environ.get("HEALTHCHECK_PORT", "8000")


def host_de_allowed_hosts() -> str:
    primero = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")[0].strip()
    # '*' y los comodines de subdominio ('.dominio.com') no son un Host válido.
    if not primero or primero == "*":
        return "localhost"
    return primero.lstrip(".")


def main() -> int:
    peticion = urllib.request.Request(
        f"http://127.0.0.1:{PUERTO}/api/health/",
        headers={"Host": host_de_allowed_hosts()},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=4) as respuesta:  # noqa: S310 — URL fija a loopback
            return 0 if respuesta.status == 200 else 1
    except Exception as exc:  # noqa: BLE001 — cualquier fallo es «no sano»
        sys.stderr.write(f"healthcheck: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
