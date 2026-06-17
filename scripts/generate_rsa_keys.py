#!/usr/bin/env python3
"""
Genera un par de claves RSA 2048 para autenticación JWT de servicio (RS256).

Uso:
    python scripts/generate_rsa_keys.py

Salida:
    - Clave privada en una línea (para INTERNAL_JWT_PRIVATE_KEY en .env)
    - Clave pública en una línea (para INTERNAL_JWT_PUBLIC_KEY en .env)

La clave privada debe mantenerse SOLO en el backend (Django).
La clave pública se distribuye a scanning_service y reporting_excel.
"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def generate_key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    private_oneline = private_pem.replace("\n", "\\n")
    public_oneline = public_pem.replace("\n", "\\n")

    return private_oneline, public_oneline


if __name__ == "__main__":
    private, public = generate_key_pair()

    print("# Agrega estas líneas a tu archivo .env de producción")
    print("# NUNCA commitees este archivo\n")
    print(f'INTERNAL_JWT_PRIVATE_KEY="{private}"\n')
    print(f'INTERNAL_JWT_PUBLIC_KEY="{public}"')
