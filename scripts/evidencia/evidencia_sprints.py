"""Evidencia por sprint: ejecuta las pruebas que cita el backlog y deja el resultado.

Lee `docs/gestion-proyecto/PRODUCT_BACKLOG.md` (historia → sprint → línea
«Verificación»), ejecuta una sola vez cada archivo de prueba citado y escribe:

- `docs/gestion-proyecto/evidencia/EVIDENCIA_POR_SPRINT.md`: tabla por sprint e
  historia con pruebas ejecutadas, aprobadas y fallidas, fecha y commit;
- `docs/gestion-proyecto/evidencia/junit/*.xml`: reportes JUnit crudos (anexo).

Las historias sin prueba automatizada quedan marcadas como «evidencia manual»;
su lista de comprobación vive en `CHECKLIST_EVIDENCIA_MANUAL.md`.

Uso (en el equipo sin Docker, backend con SQLite en memoria):

    python scripts/evidencia/evidencia_sprints.py \\
        --python-backend "%TEMP%/be/Scripts/python.exe" \\
        --python-servicio scanning_service="%TEMP%/sv_scanning_service/Scripts/python.exe" \\
        --python-servicio printing_service="%TEMP%/sv_printing_service/Scripts/python.exe" \\
        --python-servicio reporting_excel="%TEMP%/sv_reporting_excel/Scripts/python.exe"

En el equipo con Docker (Linux), backend sobre SQL Server 2022: el envoltorio corre pytest en la
imagen `texcore-django-test` contra un SQL Server desechable. Los servicios necesitan su
`requirements.txt` más `pytest-cov` (por ejemplo, entornos creados con `uv venv -p 3.12`):

    python scripts/evidencia/evidencia_sprints.py --settings TexCore.settings_test \\
        --python-backend scripts/evidencia/python_backend_sqlserver.sh \\
        --python-servicio scanning_service=<venv>/bin/python ...
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKLOG = RAIZ / "docs" / "gestion-proyecto" / "PRODUCT_BACKLOG.md"
SALIDA = RAIZ / "docs" / "gestion-proyecto" / "evidencia"
APPS_DJANGO = ("gestion", "inventory", "internal_api")
SERVICIOS = ("scanning_service", "printing_service", "reporting_excel")

RE_HISTORIA = re.compile(r"^### (TEX-\d+) · (.+)$")
RE_SPRINT = re.compile(r"^\| EP-\d+ \| Sprint (\d+) \|")
RE_RUTA = re.compile(r"`([^`]+)`")


@dataclass
class Historia:
    clave: str
    titulo: str
    sprint: int = -1
    verificacion: str = ""
    archivos: list[str] = field(default_factory=list)


@dataclass
class Resultado:
    total: int = 0
    fallidas: int = 0
    omitidas: int = 0

    def sumar(self, otro: Resultado) -> None:
        self.total += otro.total
        self.fallidas += otro.fallidas
        self.omitidas += otro.omitidas

    @property
    def aprobadas(self) -> int:
        return self.total - self.fallidas - self.omitidas


def leer_backlog() -> list[Historia]:
    historias: list[Historia] = []
    actual: Historia | None = None
    en_verificacion = False
    for linea in BACKLOG.read_text(encoding="utf-8").splitlines():
        if m := RE_HISTORIA.match(linea):
            actual = Historia(m.group(1), m.group(2).strip())
            historias.append(actual)
            en_verificacion = False
            continue
        if actual is None:
            continue
        if m := RE_SPRINT.match(linea):
            actual.sprint = int(m.group(1))
        if linea.startswith("> **Verificación:**"):
            actual.verificacion = linea.removeprefix("> **Verificación:**").strip()
            en_verificacion = True
        elif en_verificacion and linea.startswith("> "):
            actual.verificacion += " " + linea[2:].strip()
        else:
            en_verificacion = False
    for h in historias:
        h.archivos = resolver_rutas(h.verificacion)
    return historias


def resolver_rutas(texto: str) -> list[str]:
    """Rutas de prueba citadas; un nombre suelto hereda el directorio del anterior."""
    rutas: list[str] = []
    directorio = ""
    for crudo in RE_RUTA.findall(texto):
        token = crudo.split(" ")[0]
        if not token.endswith((".py", ".tsx", ".ts", "/tests")):
            continue
        if "/" in token:
            directorio = token.rsplit("/", 1)[0] if not token.endswith("/tests") else ""
        elif directorio:
            token = f"{directorio}/{token}"
        coincidencias = sorted(p.relative_to(RAIZ).as_posix() for p in RAIZ.glob(token)) if "*" in token else [token]
        rutas.extend(c for c in coincidencias if (RAIZ / c).exists())
    return list(dict.fromkeys(rutas))


def tipo_de(ruta: str) -> str:
    if ruta.startswith("frontend/"):
        return "frontend"
    servicio = ruta.split("/", 1)[0]
    return servicio if servicio in SERVICIOS else "django"


def leer_junit(xml: Path, clave_de_caso) -> dict[str, Resultado]:
    por_archivo: dict[str, Resultado] = {}
    if not xml.exists():
        return por_archivo
    # El XML es el JUnit que escriben nuestras propias suites en esta misma corrida (no es
    # entrada externa): sin riesgo de XXE. Mismo motivo que el S314 de Ruff en pyproject.toml.
    for caso in ET.parse(xml).getroot().iter("testcase"):  # nosemgrep: use-defused-xml-parse
        clave = clave_de_caso(caso)
        r = por_archivo.setdefault(clave, Resultado())
        r.total += 1
        if caso.find("failure") is not None or caso.find("error") is not None:
            r.fallidas += 1
        elif caso.find("skipped") is not None:
            r.omitidas += 1
    return por_archivo


def ejecutar(comando: list[str], cwd: Path, env: dict[str, str] | None = None) -> int:
    print("$", " ".join(comando), f"(en {cwd.relative_to(RAIZ) if cwd != RAIZ else '.'})", flush=True)
    # En Windows `npx` es un .cmd: solo se resuelve a través del intérprete de comandos.
    usar_shell = sys.platform == "win32" and comando[0] == "npx"
    return subprocess.run(comando, cwd=cwd, env=env, check=False, shell=usar_shell).returncode


def correr_django(archivos: list[str], args) -> dict[str, Resultado]:
    xml = SALIDA / "junit" / "backend_django.xml"
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": args.settings}
    comando = [
        args.python_backend,
        "-m",
        "pytest",
        *archivos,
        "-q",
        "-p",
        "no:cacheprovider",
        "-o",
        "junit_family=xunit1",
        f"--junitxml={xml}",
    ]
    if args.settings.endswith("_local"):
        comando.append("--nomigrations")
    ejecutar(comando, RAIZ, env)
    return leer_junit(xml, lambda c: c.get("file", "").replace("\\", "/"))


def correr_servicio(servicio: str, python: str) -> dict[str, Resultado]:
    xml = SALIDA / "junit" / f"{servicio}.xml"
    ejecutar([python, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"], RAIZ / servicio)
    total = Resultado()
    for r in leer_junit(xml, lambda c: servicio).values():
        total.sumar(r)
    return {f"{servicio}/tests": total}


def correr_frontend(archivos: list[str]) -> dict[str, Resultado]:
    xml = SALIDA / "junit" / "frontend.xml"
    relativos = [a.removeprefix("frontend/") for a in archivos]
    ejecutar(["npx", "vitest", "run", *relativos, "--reporter=junit", f"--outputFile={xml}"], RAIZ / "frontend")
    return leer_junit(xml, lambda c: "frontend/" + c.get("classname", "").replace("\\", "/"))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=False).stdout.strip()


def escribir_informe(historias: list[Historia], resultados: dict[str, Resultado], args) -> Path:
    cambios = git("status", "--porcelain")
    nota_sqlite = (
        " (SQLite en memoria: no cubre los CHECK nativos ni el T-SQL de SQL Server)"
        if args.settings.endswith("_local")
        else " (SQL Server 2022)"
    )
    lineas = [
        "# Evidencia de pruebas por sprint — TexCore",
        "",
        "> Generado por `scripts/evidencia/evidencia_sprints.py`. No editar a mano: volver a ejecutar el script.",
        ">",
        f"> **Fecha:** {dt.datetime.now().astimezone():%Y-%m-%d %H:%M %Z}"
        f" · **Commit:** `{git('rev-parse', '--short', 'HEAD')}`"
        f"{' con cambios sin commitear' if cambios else ''} · **Rama:** `{git('branch', '--show-current')}`",
        f"> **Backend:** `{args.settings}`{nota_sqlite}",
        "> Reportes JUnit crudos en `junit/`. Las historias sin prueba automatizada se demuestran con",
        "> `CHECKLIST_EVIDENCIA_MANUAL.md`.",
        "",
    ]
    total_global = Resultado()
    resumen: list[str] = [
        "## Resumen",
        "",
        "| Sprint | Historias | Con prueba automatizada | Pruebas | Aprobadas | Fallidas | Omitidas | Estado |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    detalle: list[str] = []
    for sprint in sorted({h.sprint for h in historias}):
        del_sprint = [h for h in historias if h.sprint == sprint]
        acumulado = Resultado()
        con_prueba = 0
        detalle += [
            f"## Sprint {sprint}",
            "",
            "| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
        for h in del_sprint:
            r = Resultado()
            for archivo in h.archivos:
                r.sumar(resultados.get(archivo, Resultado()))
            acumulado.sumar(r)
            if h.archivos:
                con_prueba += 1
                estado = "✅" if r.total and not r.fallidas else ("❌" if r.fallidas else "⚠️ sin ejecutar")
            else:
                estado = "📋 evidencia manual"
            citadas = "<br>".join(f"`{a}`" for a in h.archivos) or (h.verificacion or "—")
            detalle.append(
                f"| **{h.clave}** {h.titulo} | {citadas} | {r.total} | {r.aprobadas} | {r.fallidas}"
                f" | {r.omitidas} | {estado} |"
            )
        detalle.append("")
        total_global.sumar(acumulado)
        estado_sprint = "❌" if acumulado.fallidas else ("✅" if con_prueba == len(del_sprint) else "✅ + 📋 manual")
        resumen.append(
            f"| {sprint} | {len(del_sprint)} | {con_prueba} | {acumulado.total} | {acumulado.aprobadas}"
            f" | {acumulado.fallidas} | {acumulado.omitidas} | {estado_sprint} |"
        )
    resumen.append("")
    resumen.append("Una prueba citada por varias historias se cuenta en cada una (ej. `test_production_views.py`).")
    resumen.append("Las omitidas llevan su motivo en el reporte JUnit (ej. permisos POSIX que solo existen en Linux).")
    resumen.append("")
    destino = SALIDA / "EVIDENCIA_POR_SPRINT.md"
    destino.write_text("\n".join(lineas + resumen + detalle), encoding="utf-8")
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--python-backend", default=sys.executable)
    parser.add_argument("--python-servicio", action="append", default=[], metavar="SERVICIO=PYTHON")
    parser.add_argument("--settings", default="TexCore.settings_test_local")
    parser.add_argument("--sin-frontend", action="store_true")
    args = parser.parse_args()
    pythons = dict(s.split("=", 1) for s in args.python_servicio)

    historias = leer_backlog()
    (SALIDA / "junit").mkdir(parents=True, exist_ok=True)
    archivos = sorted({a for h in historias for a in h.archivos})

    resultados: dict[str, Resultado] = {}
    django = [a for a in archivos if tipo_de(a) == "django"]
    if django:
        resultados |= correr_django(django, args)
    for servicio in SERVICIOS:
        if any(tipo_de(a) == servicio for a in archivos):
            resultados |= correr_servicio(servicio, pythons.get(servicio, sys.executable))
    frontend = [a for a in archivos if tipo_de(a) == "frontend"]
    if frontend and not args.sin_frontend:
        resultados |= correr_frontend(frontend)

    destino = escribir_informe(historias, resultados, args)
    fallidas = sum(r.fallidas for r in resultados.values())
    total = sum(r.total for r in resultados.values())
    print(f"\nInforme: {destino.relative_to(RAIZ)} · {total} pruebas, {fallidas} fallidas")
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main())
