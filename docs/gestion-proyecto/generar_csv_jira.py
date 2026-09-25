# -*- coding: utf-8 -*-
"""
Genera el CSV importable a Jira Cloud a partir de PRODUCT_BACKLOG.md.

El backlog en Markdown es la unica fuente de verdad: este script no contiene
datos de historias, solo los extrae. Si el backlog cambia, se vuelve a ejecutar.

Uso:  python generar_csv_jira.py <ruta_backlog.md> <ruta_salida.csv>
"""
import csv
import re
import sys

# Must/Should/Could -> prioridades nativas de Jira
PRIORIDAD_JIRA = {"Must": "High", "Should": "Medium", "Could": "Low"}

# Fechas de cada sprint segun la Tabla 14 del documento Capstone
FECHAS_SPRINT = {
    "Sprint 0": "21 Sep 2026 - 02 Oct 2026",
    "Sprint 1": "05 Oct 2026 - 16 Oct 2026",
    "Sprint 2": "19 Oct 2026 - 30 Oct 2026",
    "Sprint 3": "02 Nov 2026 - 13 Nov 2026",
    "Sprint 4": "16 Nov 2026 - 27 Nov 2026",
    "Sprint 5": "30 Nov 2026 - 11 Dic 2026",
    "Sprint 6": "14 Dic 2026 - 25 Dic 2026",
    "Sprint 7": "04 Ene 2027 - 15 Ene 2027",
    "Sprint 8": "18 Ene 2027 - 29 Ene 2027",
}

OBJETIVO_EPICA = {
    "EP-00": "Establecer la infraestructura y automatizar los despliegues.",
    "EP-01": "Habilitar el acceso seguro y la gestion de roles de la empresa.",
    "EP-02": "Digitalizar el registro en planta y el control de Ordenes de Produccion.",
    "EP-03": "Sustituir los registros manuales de bodega por un Kardex digital auditable.",
    "EP-04": "Conectar la produccion con el inventario y sugerir compras de materiales.",
    "EP-05": "Automatizar el ciclo de ventas, validacion de creditos y pagos.",
    "EP-06": "Estandarizar las recetas de tintoreria y emitir etiquetas de empaque.",
    "EP-07": "Asegurar despachos con escaner y proveer tableros de control a gerencia.",
    "EP-08": "Permitir la autoadministracion de catalogos y congelar el sistema.",
}


def limpiar(texto):
    """Quita el enfasis Markdown, dejando texto plano legible en Jira."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"\*(.+?)\*", r"\1", texto)
    texto = re.sub(r"`(.+?)`", r"\1", texto)
    return texto.strip()


def parsear_epicas(contenido):
    """Extrae {codigo: nombre} de las cabeceras '## EP-XX - Nombre'."""
    epicas = {}
    for codigo, nombre in re.findall(r"^## (EP-\d\d) · (.+)$", contenido, re.M):
        epicas[codigo] = nombre.strip()
    return epicas


def parsear_historias(contenido):
    """Extrae cada historia con sus metadatos y criterios de aceptacion."""
    historias = []
    # Corta el documento en bloques que empiezan en cada '### TEX-NN'
    bloques = re.split(r"^### (TEX-\d+) · (.+)$", contenido, flags=re.M)

    for i in range(1, len(bloques), 3):
        clave, titulo, cuerpo = bloques[i], bloques[i + 1].strip(), bloques[i + 2]

        # Narrativa: parrafo que empieza por '**Como**'
        narrativa = ""
        m = re.search(r"^\*\*Como\*\* (.+?)(?=\n\n)", cuerpo, re.M | re.S)
        if m:
            narrativa = limpiar("Como " + m.group(1))
            narrativa = re.sub(r"\s*\n\s*", " ", narrativa)

        # Fila de metadatos: | EP-XX | Sprint N | pts | Prioridad | Requisitos |
        meta = re.search(
            r"\| (EP-\d\d) \| (Sprint \d) \| (\d+) \| (Must|Should|Could) \| (.+?) \|",
            cuerpo,
        )
        if not meta:
            print("  AVISO: sin metadatos ->", clave)
            continue
        epica, sprint, puntos, prioridad, requisitos = meta.groups()

        # Criterios de aceptacion
        criterios = []
        for bloque_ca in re.findall(
            r"^- \*\*(CA-\d+)\*\* — (.+?)(?=^- \*\*CA-|\n\n|\Z)", cuerpo, re.M | re.S
        ):
            etiqueta, texto = bloque_ca
            texto = re.sub(r"\s*\n\s*", " ", limpiar(texto)).strip().rstrip(".")
            criterios.append("{}: {}.".format(etiqueta, texto))

        # Linea de verificacion (archivos de prueba + tecnicas ISTQB)
        verificacion = ""
        v = re.search(r"^> \*\*Verificación:\*\* (.+)$", cuerpo, re.M)
        if v:
            verificacion = limpiar(v.group(1))

        historias.append(
            {
                "clave": clave,
                "titulo": titulo,
                "narrativa": narrativa,
                "epica": epica,
                "sprint": sprint,
                "puntos": puntos,
                "prioridad": prioridad,
                "requisitos": [r.strip() for r in requisitos.split(",")],
                "criterios": criterios,
                "verificacion": verificacion,
            }
        )
    return historias


def construir_descripcion(h):
    """Arma el campo Description con narrativa + criterios + verificacion."""
    partes = [h["narrativa"], "", "CRITERIOS DE ACEPTACION", ""]
    partes.extend("* " + c for c in h["criterios"])
    if h["verificacion"]:
        partes += ["", "VERIFICACION", "", h["verificacion"]]
    partes += [
        "",
        "TRAZABILIDAD",
        "",
        "Requisitos: " + ", ".join(h["requisitos"]),
        "Referencia: " + h["clave"] + " del Product Backlog de TexCore",
    ]
    return "\n".join(partes)


def main():
    ruta_backlog, ruta_csv = sys.argv[1], sys.argv[2]
    contenido = open(ruta_backlog, encoding="utf-8").read()

    epicas = parsear_epicas(contenido)
    historias = parsear_historias(contenido)
    print("Epicas encontradas:   ", len(epicas))
    print("Historias encontradas:", len(historias))

    # Cuantas etiquetas como maximo necesita una fila (Jira repite la columna)
    max_etiquetas = max(len(h["requisitos"]) for h in historias) + 1

    cabecera = [
        "Issue Type", "Issue Key", "Summary", "Description", "Priority",
        "Story Points", "Sprint", "Epic Name", "Epic Link", "Status",
    ] + ["Labels"] * max_etiquetas

    filas = []

    # Primero las epicas: Jira las necesita creadas antes de enlazar las historias
    for codigo in sorted(epicas):
        nombre = epicas[codigo]
        sprint = "Sprint " + codigo[-1]
        descripcion = "\n".join([
            "Objetivo del Sprint: " + OBJETIVO_EPICA.get(codigo, ""),
            "",
            "Periodo: " + FECHAS_SPRINT.get(sprint, ""),
            "Referencia: Tabla 14 del documento Capstone.",
        ])
        fila = [
            "Epic", codigo, "{} {}".format(codigo, nombre), descripcion,
            "High", "", "", nombre, "", "To Do",
        ] + [codigo] + [""] * (max_etiquetas - 1)
        filas.append(fila)

    # Luego las historias
    for h in historias:
        etiquetas = [h["epica"]] + h["requisitos"]
        etiquetas += [""] * (max_etiquetas - len(etiquetas))
        fila = [
            "Story",
            h["clave"],
            "{} {}".format(h["clave"], h["titulo"]),
            construir_descripcion(h),
            PRIORIDAD_JIRA[h["prioridad"]],
            h["puntos"],
            h["sprint"],
            "",
            epicas[h["epica"]],  # Epic Link apunta al Epic Name
            "To Do",
        ] + etiquetas[:max_etiquetas]
        filas.append(fila)

    # UTF-8 sin BOM: es lo que espera el importador de Jira Cloud.
    # newline='' evita que Windows duplique los saltos de linea del CSV.
    with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, quoting=csv.QUOTE_ALL)
        escritor.writerow(cabecera)
        escritor.writerows(filas)

    print("CSV generado:", ruta_csv)
    print("Filas totales:", len(filas), "({} epicas + {} historias)".format(
        len(epicas), len(historias)))
    print("Puntos totales:", sum(int(h["puntos"]) for h in historias))
    print("Criterios de aceptacion:", sum(len(h["criterios"]) for h in historias))


if __name__ == "__main__":
    main()
