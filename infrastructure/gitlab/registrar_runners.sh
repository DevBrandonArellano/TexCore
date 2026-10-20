#!/bin/bash
# Registra los dos runners de este equipo. Los tokens salen de GitLab:
#   Admin > CI/CD > Runners > Nuevo runner de instancia (o del proyecto).
# Uso, desde la raíz del repositorio:
#   TOKEN_CI=glrt-... TOKEN_STAGING=glrt-... bash infrastructure/gitlab/registrar_runners.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
COMPOSE=(docker compose -f infrastructure/gitlab/docker-compose.gitlab.yml --env-file infrastructure/gitlab/.env)
URL="https://$(grep -E '^GITLAB_HOST=' infrastructure/gitlab/.env | cut -d= -f2):$(grep -E '^GITLAB_HTTPS_PORT=' infrastructure/gitlab/.env | cut -d= -f2)"
: "${TOKEN_CI:?Falta TOKEN_CI}" "${TOKEN_STAGING:?Falta TOKEN_STAGING}"

# texcore-ci: lint, pruebas, auditoría y front. Los jobs no reciben el socket de Docker.
"${COMPOSE[@]}" exec -T runner-ci gitlab-runner register --non-interactive \
    --url "$URL" --tls-ca-file /etc/gitlab-runner/certs/gitlab.crt --token "$TOKEN_CI" \
    --executor docker --docker-image python:3.12-bookworm --docker-pull-policy if-not-present \
    --docker-network-mode bridge --description texcore-ci

# texcore-staging: construcción, escaneo y staging efímero. Solo ramas protegidas; los
# jobs reciben el socket del host y la red del host (el smoke test llama a localhost).
"${COMPOSE[@]}" exec -T runner-staging gitlab-runner register --non-interactive \
    --url "$URL" --tls-ca-file /etc/gitlab-runner/certs/gitlab.crt --token "$TOKEN_STAGING" \
    --executor docker --docker-image texcore/ci-tools:1 --docker-pull-policy if-not-present \
    --docker-network-mode host --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
    --description texcore-staging

cat <<'AVISO'
Runners registrados. Falta ajustarlos en GitLab (Admin > CI/CD > Runners), porque con tokens
de runner nuevos esas opciones se fijan al crearlos:
  texcore-ci       sin etiqueta, "Ejecutar jobs sin etiqueta" activado, sin protección.
  texcore-staging  etiqueta «staging», "Ejecutar jobs sin etiqueta" DESACTIVADO y
                   "Protegido" activado (solo ramas protegidas: master y staging).
  texcore-produccion (VM de Hyper-V, ejecutor shell): etiqueta «produccion» y "Protegido";
                   se registra cuando exista la VM (GUIA_GITLAB.md §6).
AVISO
