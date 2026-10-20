"""
Cifrado de datos personales en reposo (RS-19 — LOPDP 2021, ISO/IEC 27001).

Dos primitivas, con propósitos distintos y claves distintas:

- `cifrar`/`descifrar`: cifrado simétrico reversible con Fernet (AES-128-CBC con
  HMAC-SHA256 de autenticación). Protege el dato en la base; la aplicación lo
  descifra para mostrarlo. La clave vive en `FIELD_ENCRYPTION_KEYS`.

- `indice_ciego`: resumen unidireccional HMAC-SHA256 del valor normalizado. No es
  reversible y existe solo para poder buscar por igualdad exacta y mantener la
  unicidad en la base sin descifrar fila por fila. La clave vive en
  `BLIND_INDEX_KEY`.

Por qué dos claves: `FIELD_ENCRYPTION_KEYS` es una lista rotable (la primera cifra,
todas descifran, ver `MultiFernet`), mientras que `BLIND_INDEX_KEY` debe ser estable
— si cambia, todos los índices ciegos guardados dejan de coincidir y hay que
recalcularlos con `manage.py cifrar_datos_personales --recalcular-indices`.

Ninguna de las dos se deriva de `SECRET_KEY`: `SECRET_KEY` también firma los JWT y
se rota cada año (`SECURITY.md`), y derivar de ella volvería ilegibles los datos
cifrados en cada rotación.
"""

import hashlib
import hmac
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.dispatch import receiver

logger = logging.getLogger(__name__)

__all__ = [
    "ErrorDeCifrado",
    "cifrar",
    "descifrar",
    "generar_clave",
    "indice_ciego",
    "normalizar_identificacion",
]

# Caché de los objetos criptográficos: construirlos en cada lectura de fila
# costaría un PBKDF/parseo de clave por campo y por registro.
_cache: dict[str, object] = {}


class ErrorDeCifrado(Exception):
    """El valor guardado no se pudo descifrar con ninguna de las claves activas."""


def _claves_configuradas() -> list[str]:
    claves = getattr(settings, "FIELD_ENCRYPTION_KEYS", None)
    if not claves:
        raise ImproperlyConfigured(
            "Falta FIELD_ENCRYPTION_KEYS: sin ella no se pueden leer ni escribir los "
            "datos personales cifrados. Genera una clave con "
            '`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.'
        )
    if isinstance(claves, str):
        claves = [claves]
    return [clave.strip() for clave in claves if clave and clave.strip()]


def _fernet() -> MultiFernet:
    """MultiFernet con todas las claves activas: la primera cifra, todas descifran."""
    if "fernet" not in _cache:
        claves = _claves_configuradas()
        try:
            _cache["fernet"] = MultiFernet([Fernet(clave) for clave in claves])
        except (TypeError, ValueError) as exc:
            logger.exception("FIELD_ENCRYPTION_KEYS contiene una clave Fernet inválida (%d configuradas).", len(claves))
            raise ImproperlyConfigured(
                "FIELD_ENCRYPTION_KEYS contiene una clave que no es una clave Fernet "
                "válida (32 bytes en base64 urlsafe)."
            ) from exc
    return _cache["fernet"]  # type: ignore[return-value]


def _clave_indice() -> bytes:
    if "indice" not in _cache:
        clave = getattr(settings, "BLIND_INDEX_KEY", None)
        if not clave:
            raise ImproperlyConfigured(
                "Falta BLIND_INDEX_KEY: sin ella no se puede calcular el índice ciego "
                "que permite buscar por identificación ni garantizar su unicidad."
            )
        _cache["indice"] = clave.encode("utf-8") if isinstance(clave, str) else clave
    return _cache["indice"]  # type: ignore[return-value]


def generar_clave() -> str:
    """Clave Fernet nueva, lista para pegar en FIELD_ENCRYPTION_KEYS."""
    return Fernet.generate_key().decode("ascii")


def cifrar(texto: str) -> str:
    """Cifra el texto con la primera clave de FIELD_ENCRYPTION_KEYS."""
    return _fernet().encrypt(texto.encode("utf-8")).decode("ascii")


def descifrar(token: str, *, registrar: bool = True) -> str:
    """
    Descifra un token Fernet probando todas las claves activas.

    `registrar=False` es para quien espera el fallo como parte de su trabajo (el comando
    `cifrar_datos_personales` busca justamente las filas que no descifran) y lo informa
    por su cuenta; si no, cada fila en claro dejaría un error falso en el registro.

    Lanza `ErrorDeCifrado` si ninguna sirve, en vez de devolver el valor crudo: un
    valor que no descifra significa que falta una clave en la rotación o que la fila
    nunca se migró, y leerla «en claro» escondería ese fallo.
    """
    if isinstance(token, str):
        token = token.encode("utf-8")  # type: ignore[assignment]
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        if registrar:
            # Nunca se registra el token ni el valor: solo el hecho, para poder alertar.
            logger.exception("Un dato personal no se pudo descifrar con las claves activas.")
        raise ErrorDeCifrado(
            "No se pudo descifrar un dato personal con las claves activas. Revisa "
            "FIELD_ENCRYPTION_KEYS (¿falta la clave anterior tras una rotación?) o "
            "ejecuta `manage.py cifrar_datos_personales` si quedan filas sin migrar."
        ) from exc


def normalizar_identificacion(valor) -> str:
    """Forma canónica de una identificación: texto sin espacios alrededor."""
    return str(valor).strip()


def indice_ciego(valor: str) -> str:
    """
    HMAC-SHA256 en hexadecimal (64 caracteres) del valor normalizado.

    Determinista a propósito: es lo que permite `filter(ruc_cedula_hash=...)` sobre un
    índice de la base. Con clave (HMAC y no SHA-256 a secas) para que quien obtenga
    una copia de la base no pueda confirmar una identificación por fuerza bruta sobre
    el espacio de cédulas, que es pequeño.
    """
    normalizado = normalizar_identificacion(valor)
    return hmac.new(_clave_indice(), normalizado.encode("utf-8"), hashlib.sha256).hexdigest()


@receiver(setting_changed)
def _limpiar_cache(sender, setting, **kwargs):
    """Invalida la caché cuando un test usa override_settings sobre las claves."""
    if setting in ("FIELD_ENCRYPTION_KEYS", "BLIND_INDEX_KEY"):
        _cache.clear()
