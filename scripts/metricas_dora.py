#!/usr/bin/env python3
"""
Métricas DORA de TexCore a partir de GitLab: los despliegues del environment `production`
(los registra el job `deploy:produccion` de .gitlab-ci.yml) y los jobs `rollback:produccion`.

    GITLAB_TOKEN=... python3 scripts/metricas_dora.py grupo/texcore --dias 28

Dentro del pipeline usa CI_API_V4_URL y el token de proyecto GITLAB_TOKEN (permiso read_api).
Con el certificado propio de GitLab, GITLAB_CA_FILE apunta a su CA.

- Frecuencia de despliegue: despliegues exitosos por semana.
- Lead time de cambios: mediana de horas entre el commit y su despliegue.
- Tasa de fallos de cambio: (despliegues fallidos + rollbacks) / despliegues.
- Tiempo de recuperación (MTTR): mediana de horas entre un fallo y el siguiente despliegue
  exitoso o rollback.

El pipeline programado `gobierno` lo ejecuta y publica el resultado en el log del job.
Solo usa la biblioteca estándar.
"""

import argparse
import json
import os
import ssl
import statistics
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Despliegue:
    creado: datetime
    exitoso: bool
    fecha_commit: datetime


@dataclass(frozen=True)
class Metricas:
    despliegues_por_semana: float
    lead_time_horas: float | None
    tasa_fallos: float | None
    mttr_horas: float | None


def _horas(delta: timedelta) -> float:
    return delta.total_seconds() / 3600


def calcular_metricas(despliegues: list[Despliegue], rollbacks: list[datetime], periodo_dias: int) -> Metricas:
    """Las cuatro métricas del periodo. Sin datos suficientes devuelve None, no un cero inventado."""
    despliegues = sorted(despliegues, key=lambda d: d.creado)
    exitosos = [d for d in despliegues if d.exitoso]
    fallidos = [d for d in despliegues if not d.exitoso]

    lead_time = statistics.median(_horas(d.creado - d.fecha_commit) for d in exitosos) if exitosos else None
    tasa_fallos = (len(fallidos) + len(rollbacks)) / len(despliegues) if despliegues else None

    recuperaciones = []
    for fallo in fallidos:
        siguientes = [d.creado for d in exitosos if d.creado > fallo.creado]
        siguientes += [r for r in rollbacks if r > fallo.creado]
        if siguientes:
            recuperaciones.append(_horas(min(siguientes) - fallo.creado))

    return Metricas(
        despliegues_por_semana=round(len(exitosos) / (periodo_dias / 7), 2),
        lead_time_horas=lead_time,
        tasa_fallos=tasa_fallos,
        mttr_horas=statistics.median(recuperaciones) if recuperaciones else None,
    )


# ---------------------------------------------------------------------------
# Descarga desde la API de GitLab
# ---------------------------------------------------------------------------

ESTADOS_FINALES = {"success": True, "failed": False}


def _fecha(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def necesita_commit(despliegue: dict) -> bool:
    """True si la respuesta no trae la fecha del commit y hay que pedirla aparte."""
    return not ((despliegue.get("deployable") or {}).get("commit") or {}).get("committed_date")


def despliegue_de_gitlab(despliegue: dict, fecha_commit: datetime | None) -> Despliegue | None:
    """Traduce un despliegue de la API (`/deployments`); None si sigue en curso o se canceló."""
    if despliegue["status"] not in ESTADOS_FINALES:
        return None
    propia = ((despliegue.get("deployable") or {}).get("commit") or {}).get("committed_date")
    return Despliegue(
        creado=_fecha(despliegue["created_at"]),
        exitoso=ESTADOS_FINALES[despliegue["status"]],
        fecha_commit=_fecha(propia) if propia else fecha_commit,
    )


def rollbacks_de_gitlab(jobs: list[dict], desde: datetime) -> list[datetime]:
    """Fechas de los jobs `rollback:produccion` exitosos dentro del periodo."""
    fechas = (_fecha(j["created_at"]) for j in jobs if j["name"] == "rollback:produccion" and j["status"] == "success")
    return [f for f in fechas if f >= desde]


def _get(api: str, ruta: str, token: str):
    # `api` sale de CI_API_V4_URL o de --api (https del GitLab propio); el esquema se valida en main().
    peticion = urllib.request.Request(api + ruta, headers={"PRIVATE-TOKEN": token})  # noqa: S310
    contexto = ssl.create_default_context(cafile=os.environ.get("GITLAB_CA_FILE"))
    with urllib.request.urlopen(peticion, timeout=30, context=contexto) as respuesta:  # noqa: S310
        return json.load(respuesta)


def descargar(api: str, proyecto: str, token: str, desde: datetime) -> tuple[list[Despliegue], list[datetime]]:
    pid = urllib.parse.quote(proyecto, safe="")
    despliegues = []
    for d in _get(api, f"/projects/{pid}/deployments?environment=production&per_page=100&order_by=created_at", token):
        if _fecha(d["created_at"]) < desde:
            continue
        fecha_commit = None
        if necesita_commit(d) and d["status"] in ESTADOS_FINALES:
            fecha_commit = _fecha(_get(api, f"/projects/{pid}/repository/commits/{d['sha']}", token)["committed_date"])
        traducido = despliegue_de_gitlab(d, fecha_commit)
        if traducido is not None:
            despliegues.append(traducido)
    jobs = _get(api, f"/projects/{pid}/jobs?scope[]=success&per_page=100", token)
    return despliegues, rollbacks_de_gitlab(jobs, desde)


def informe(m: Metricas, periodo_dias: int) -> str:
    def valor(x, formato):
        return "sin datos" if x is None else formato.format(x)

    return "\n".join(
        [
            f"## Métricas DORA — últimos {periodo_dias} días",
            "",
            "| Métrica | Valor |",
            "|---|---|",
            f"| Frecuencia de despliegue | {m.despliegues_por_semana} por semana |",
            f"| Lead time de cambios (mediana) | {valor(m.lead_time_horas, '{:.1f} h')} |",
            f"| Tasa de fallos de cambio | {valor(m.tasa_fallos, '{:.0%}')} |",
            f"| Tiempo de recuperación (mediana) | {valor(m.mttr_horas, '{:.1f} h')} |",
        ]
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("proyecto", help="ruta del proyecto (grupo/texcore) o su id numérico")
    parser.add_argument("--dias", type=int, default=28)
    parser.add_argument("--api", default=os.environ.get("CI_API_V4_URL"), help="URL de la API v4 (https://host/api/v4)")
    args = parser.parse_args(argv)
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        print("Falta GITLAB_TOKEN", file=sys.stderr)
        return 2
    if not args.api or not args.api.startswith("https://"):
        print("Falta --api (o CI_API_V4_URL) con esquema https", file=sys.stderr)
        return 2
    desde = datetime.now(UTC) - timedelta(days=args.dias)
    despliegues, rollbacks = descargar(args.api.rstrip("/"), args.proyecto, token, desde)
    print(informe(calcular_metricas(despliegues, rollbacks, args.dias), args.dias))
    return 0


if __name__ == "__main__":
    sys.exit(main())
