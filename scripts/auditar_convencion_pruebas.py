"""Gate ISTQB de las pruebas: convención de nombres y técnicas declaradas.

La tesis afirma que los casos de prueba se diseñan con técnicas de caja negra del ISTQB
(CTFL v4.0, 2023). Este gate lo verifica en el pipeline sobre todas las suites:

- **Python** (núcleo y 3 microservicios): cada `def test_*` sigue
  `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`.
- **Frontend** (`*.test.ts(x)`): cada `it(...)`/`test(...)` dice «dado … cuando … entonces».
- **Cada archivo de prueba** declara sus técnicas: la palabra «ISTQB» y al menos una técnica
  (EP, BVA, TD, STT, CB, RND o su nombre completo).

Imprime un hallazgo por línea y termina con código 1 si hay alguno.

Uso (desde la raíz del repo):
    python scripts/auditar_convencion_pruebas.py
"""

import ast
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Suites de Python: archivos de prueba del núcleo y de cada microservicio.
DIRECTORIOS_PYTHON = (
    "gestion",
    "inventory",
    "internal_api",
    "TexCore",
    "scanning_service",
    "printing_service",
    "reporting_excel",
    "scripts",
)
DIRECTORIO_FRONT = RAIZ / "frontend" / "src"

NOMBRE_PYTHON = re.compile(r"^test_(?!dado_)\w+?_dado_\w+?_cuando_\w+?_entonces_\w+$")
# Las tres palabras separadas por espacios o por `_` (algunos archivos usan el estilo de Python).
NOMBRE_FRONT = re.compile(r"(?<![^\W_])dado[\s_].*[\s_]cuando[\s_].*[\s_]entonces(?![^\W_])", re.IGNORECASE | re.DOTALL)
TECNICA = re.compile(
    r"\b(EP|BVA|TD|STT|CB(?:-D)?|RND)\b"
    r"|partici[oó]n de equivalencia|valores? l[ií]mite|tabla de decisi[oó]n|transici[oó]n de estados|caja blanca",
    re.IGNORECASE,
)
# it('…'), test("…"), it.only(`…`) y it.each([...])(`…`): el nombre es el primer argumento.
CADENA = r"""(['"`])((?:\\.|(?!\1).)*)\1"""
LLAMADA_FRONT = re.compile(r"\b(?:it|test)(?:\.(?:only|skip|concurrent|todo))?\(\s*" + CADENA, re.DOTALL)
LLAMADA_EACH = re.compile(r"\b(?:it|test)\.each\((?:[^()]|\([^()]*\))*\)\(\s*" + CADENA, re.DOTALL)


def nombre_python_valido(nombre):
    return bool(NOMBRE_PYTHON.match(nombre))


def nombre_front_valido(nombre):
    return bool(NOMBRE_FRONT.search(nombre))


def declara_tecnicas(texto):
    return "ISTQB" in texto and bool(TECNICA.search(texto))


def pruebas_python(codigo):
    """Nombres de las funciones `test_*` del módulo, también dentro de clases y `async`."""
    return [
        nodo.name
        for nodo in ast.walk(ast.parse(codigo))
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.name.startswith("test_")
    ]


def pruebas_front(codigo):
    """Nombres de `it`/`test` en el orden en que aparecen, incluidos los `it.each`."""
    encontradas = [(m.start(), m.group(2)) for m in LLAMADA_FRONT.finditer(codigo)]
    encontradas += [(m.start(), m.group(2)) for m in LLAMADA_EACH.finditer(codigo)]
    return [nombre for _, nombre in sorted(encontradas)]


def archivos_python():
    for directorio in DIRECTORIOS_PYTHON:
        for ruta in sorted((RAIZ / directorio).rglob("*.py")):
            if "node_modules" in ruta.parts or "venv" in ruta.parts or "migrations" in ruta.parts:
                continue
            if ruta.name.startswith("test_") or ruta.name.startswith("tests_"):
                yield ruta


def archivos_front():
    yield from sorted(DIRECTORIO_FRONT.rglob("*.test.ts*"))


def _hallazgos_de(ruta, extraer, valido):
    texto = ruta.read_text(encoding="utf-8")
    relativa = ruta.relative_to(RAIZ).as_posix()
    hallazgos = [] if declara_tecnicas(texto) else [(relativa, "no declara sus técnicas ISTQB")]
    hallazgos.extend(
        (relativa, f"nombre fuera de la convención: {nombre}") for nombre in extraer(texto) if not valido(nombre)
    )
    return hallazgos


def auditar():
    """Hallazgos como `(ruta relativa, motivo)`; lista vacía si todo cumple."""
    hallazgos = []
    for ruta in archivos_python():
        hallazgos.extend(_hallazgos_de(ruta, pruebas_python, nombre_python_valido))
    for ruta in archivos_front():
        hallazgos.extend(_hallazgos_de(ruta, pruebas_front, nombre_front_valido))
    return hallazgos


def main():
    hallazgos = auditar()
    for ruta, motivo in hallazgos:
        print(f"{ruta}: {motivo}")
    print(f"\n{len(hallazgos)} hallazgos de la convención ISTQB", file=sys.stderr)
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
