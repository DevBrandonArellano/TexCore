#!/bin/bash
# Construye la imagen de herramientas de los jobs de release en el equipo del runner.
set -euo pipefail
cd "$(dirname "$0")/../.."
docker build -f infrastructure/gitlab/Dockerfile.ci-tools -t texcore/ci-tools:1 infrastructure/gitlab
echo "Imagen texcore/ci-tools:1 lista."
