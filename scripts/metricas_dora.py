#!/usr/bin/env python3
"""
Métricas DORA de TexCore a partir de GitHub: los despliegues del environment `production`
(los registra el job `deploy` de release.yml) y las ejecuciones de rollback.yml.

    GITHUB_TOKEN=... python3 scripts/metricas_dora.py org/TexCore --dias 28

- Frecuencia de despliegue: despliegues exitosos por semana.
- Lead time de cambios: mediana de horas entre el commit y su despliegue.
- Tasa de fallos de cambio: (despliegues fallidos + rollbacks) / despliegues.
- Tiempo de recuperación (MTTR): mediana de horas entre un fallo y el siguiente despliegue
  exitoso o rollback.

El workflow semanal gobierno.yml lo ejecuta y publica el resultado en el resumen del run.
Solo usa la biblioteca estándar.
"""
import argparse
import json
import os
import statistics
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"


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
# Descarga desde la API de GitHub
# ---------------------------------------------------------------------------

def _fecha(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def _get(ruta: str, token: str):
    peticion = urllib.request.Request(API + ruta, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        return json.load(respuesta)


def descargar(repo: str, token: str, desde: datetime) -> tuple[list[Despliegue], list[datetime]]:
    despliegues = []
    for d in _get(f"/repos/{repo}/deployments?environment=production&per_page=100", token):
        creado = _fecha(d["created_at"])
        if creado < desde:
            continue
        estados = _get(f"/repos/{repo}/deployments/{d['id']}/statuses?per_page=1", token)
        if not estados or estados[0]["state"] not in ("success", "failure", "error"):
            continue  # en curso o esperando aprobación
        commit = _get(f"/repos/{repo}/commits/{d['sha']}", token)
        despliegues.append(Despliegue(creado=creado, exitoso=estados[0]["state"] == "success",
                                      fecha_commit=_fecha(commit["commit"]["committer"]["date"])))
    ejecuciones = _get(f"/repos/{repo}/actions/workflows/rollback.yml/runs?status=success&per_page=100", token)
    rollbacks = [_fecha(r["created_at"]) for r in ejecuciones["workflow_runs"] if _fecha(r["created_at"]) >= desde]
    return despliegues, rollbacks


def informe(m: Metricas, periodo_dias: int) -> str:
    def valor(x, formato):
        return "sin datos" if x is None else formato.format(x)
    return "\n".join([
        f"## Métricas DORA — últimos {periodo_dias} días",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Frecuencia de despliegue | {m.despliegues_por_semana} por semana |",
        f"| Lead time de cambios (mediana) | {valor(m.lead_time_horas, '{:.1f} h')} |",
        f"| Tasa de fallos de cambio | {valor(m.tasa_fallos, '{:.0%}')} |",
        f"| Tiempo de recuperación (mediana) | {valor(m.mttr_horas, '{:.1f} h')} |",
    ])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("--dias", type=int, default=28)
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Falta GITHUB_TOKEN", file=sys.stderr)
        return 2
    desde = datetime.now(timezone.utc) - timedelta(days=args.dias)
    despliegues, rollbacks = descargar(args.repo, token, desde)
    print(informe(calcular_metricas(despliegues, rollbacks, args.dias), args.dias))
    return 0


if __name__ == "__main__":
    sys.exit(main())
