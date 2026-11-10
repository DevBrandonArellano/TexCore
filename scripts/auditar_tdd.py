"""Gate TDD: el código de producción no cambia sin sus pruebas.

La tesis afirma que el desarrollo se rige por TDD (Beck, 2003; §«Estrategias de calidad»).
Este gate lo verifica en cada merge request: si cambia el código de producción de un
componente, en el mismo MR cambian también las pruebas de ese componente. Componentes:
backend (gestion, inventory, internal_api, TexCore), frontend y cada microservicio.

No cuentan como producción las migraciones, los comandos de management (datos de demo y
utilitarios), los archivos de tipos `.d.ts`, la documentación ni la configuración.

Excepción: un commit del MR con la línea `Sin-pruebas: <motivo>` (refactor sin cambio de
comportamiento, configuración). El motivo se imprime en el log del pipeline.

Uso (desde la raíz del repo):
    python scripts/auditar_tdd.py [--base <sha>]
Sin --base toma CI_MERGE_REQUEST_DIFF_BASE_SHA o, en una rama, CI_COMMIT_BEFORE_SHA.
Termina con código 1 si algún componente cambió sin pruebas.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

BACKEND = ("gestion/", "inventory/", "internal_api/", "TexCore/")
MICROSERVICIOS = ("scanning_service", "printing_service", "reporting_excel")
FUERA_DEL_ALCANCE = re.compile(r"/migrations/|/management/commands/|\.d\.ts$")
EXCEPCION = re.compile(r"^Sin-pruebas:[ \t]*(\S.*?)\s*$", re.MULTILINE)
SHA_VACIO = "0" * 40
SHA = re.compile(r"[0-9a-fA-F]{7,40}")


def clasificar(ruta):
    """("produccion" | "prueba", componente) o None si el archivo no entra en la regla."""
    if FUERA_DEL_ALCANCE.search(ruta):
        return None
    if ruta.startswith("frontend/src/") and ruta.endswith((".ts", ".tsx")):
        return ("prueba" if re.search(r"\.test\.tsx?$", ruta) else "produccion", "frontend")
    if not ruta.endswith(".py"):
        return None
    for servicio in MICROSERVICIOS:
        if ruta.startswith(f"{servicio}/tests/"):
            return ("prueba", servicio)
        if ruta.startswith(f"{servicio}/src/"):
            return ("produccion", servicio)
    if ruta.startswith(BACKEND):
        nombre = ruta.rsplit("/", 1)[-1]
        es_prueba = "/tests/" in ruta or nombre.startswith(("test_", "tests_"))
        return ("prueba" if es_prueba else "produccion", "backend")
    return None


def evaluar(archivos, mensajes):
    """(componentes con producción cambiada sin pruebas, motivos de excepción declarados)."""
    motivos = [m for mensaje in mensajes for m in EXCEPCION.findall(mensaje)]
    produccion, pruebas = set(), set()
    for ruta in archivos:
        clase = clasificar(ruta)
        if clase:
            (produccion if clase[0] == "produccion" else pruebas).add(clase[1])
    faltan = sorted(produccion - pruebas)
    return ([] if motivos else faltan), motivos


def _git(*args):
    git = shutil.which("git")
    if git is None:
        raise SystemExit("Gate TDD: no se encontró git en el PATH.")
    # Sin shell y con argumentos fijos; la única entrada externa (la base) se valida como SHA.
    return subprocess.run([git, *args], capture_output=True, text=True, check=True).stdout  # noqa: S603


def _base(argumento):
    for candidato in (
        argumento,
        os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA"),
        os.environ.get("CI_COMMIT_BEFORE_SHA"),
    ):
        if candidato and candidato != SHA_VACIO:
            if not SHA.fullmatch(candidato):
                raise SystemExit(f"Gate TDD: commit base inválido: {candidato!r}")
            return candidato
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="commit base del cambio (por defecto, el del MR)")
    base = _base(parser.parse_args().base)
    if base is None:
        print("Gate TDD: sin commit base (rama nueva o pipeline programado); no hay cambio que evaluar.")
        return 0

    archivos = _git("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD").split()
    mensajes = _git("log", "--format=%B%x00", f"{base}..HEAD").split("\x00")
    faltan, motivos = evaluar(archivos, mensajes)

    for motivo in motivos:
        print(f"Gate TDD: excepción declarada — Sin-pruebas: {motivo}")
    for componente in faltan:
        print(f"Gate TDD: cambió el código de producción de «{componente}» sin cambiar sus pruebas.")
    if faltan:
        print("Agregue la prueba (en rojo antes del cambio) o declare `Sin-pruebas: <motivo>` en un commit.")
        return 1
    print(f"Gate TDD: {len(archivos)} archivos revisados; cada componente cambiado trae sus pruebas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
