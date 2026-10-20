#!/bin/bash
# Certificado propio para GitLab y su Container Registry (un solo certificado con SAN por IP).
# Uso: bash infrastructure/gitlab/generar_certificado.sh 192.168.1.55
# Deja gitlab.crt y gitlab.key en infrastructure/gitlab/certs (fuera de git). La CA que deben
# confiar los clientes es gitlab.crt: ver docs/arquitectura/GUIA_GITLAB.md §3.
set -euo pipefail
HOST="${1:?Uso: bash infrastructure/gitlab/generar_certificado.sh <ip-o-dominio>}"
DIR="$(cd "$(dirname "$0")" && pwd)/certs"
mkdir -p "$DIR"
if [[ "$HOST" =~ ^[0-9.]+$ ]]; then SAN="IP:${HOST}"; else SAN="DNS:${HOST}"; fi
openssl req -x509 -nodes -newkey rsa:4096 -days 825 -subj "/CN=${HOST}" \
    -addext "subjectAltName=${SAN}" -keyout "$DIR/gitlab.key" -out "$DIR/gitlab.crt"
chmod 644 "$DIR/gitlab.crt"
chmod 640 "$DIR/gitlab.key"
echo "Certificado generado en $DIR (válido 825 días, SAN ${SAN})."
