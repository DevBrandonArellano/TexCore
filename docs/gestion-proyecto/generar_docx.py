# -*- coding: utf-8 -*-
"""
Convierte PRODUCT_BACKLOG.md y PLANIFICACION_SPRINTS.md en un unico documento Word
con portada e indice, para anexar al documento Capstone.

Uso: python generar_docx.py <backlog.md> <planificacion.md> <salida.docx>
"""
import re
import sys

import docx
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AZUL = RGBColor(0x1F, 0x3B, 0x63)
GRIS = RGBColor(0x59, 0x59, 0x59)


# --------------------------------------------------------------------------- #
# Utilidades de formato
# --------------------------------------------------------------------------- #
def texto_con_formato(parrafo, texto, base_negrita=False):
    """Escribe texto aplicando **negrita**, *cursiva* y `monoespaciado`."""
    partes = re.split(r"(\*\*.+?\*\*|\*[^*]+?\*|`.+?`)", texto)
    for parte in partes:
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**"):
            run = parrafo.add_run(parte[2:-2])
            run.bold = True
        elif parte.startswith("`") and parte.endswith("`"):
            run = parrafo.add_run(parte[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
            run = parrafo.add_run(parte[1:-1])
            run.italic = True
        else:
            run = parrafo.add_run(parte)
        if base_negrita:
            run.bold = True


def sombrear_celda(celda, color_hex):
    tc_pr = celda._tc.get_or_add_tcPr()
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:fill"), color_hex)
    tc_pr.append(sombra)


def insertar_indice(doc):
    """Inserta un campo TOC que Word rellena al abrir el documento."""
    parrafo = doc.add_paragraph()
    run = parrafo.add_run()
    for etiqueta, attrs, texto in (
        ("w:fldChar", {"w:fldCharType": "begin"}, None),
        ("w:instrText", {"xml:space": "preserve"}, r'TOC \o "1-2" \h \z \u'),
        ("w:fldChar", {"w:fldCharType": "separate"}, None),
        ("w:t", {}, "Pulse F9 sobre este indice para generarlo."),
        ("w:fldChar", {"w:fldCharType": "end"}, None),
    ):
        elem = OxmlElement(etiqueta)
        for k, v in attrs.items():
            elem.set(qn(k) if ":" in k else k, v)
        if texto:
            elem.text = texto
        run._r.append(elem)


# --------------------------------------------------------------------------- #
# Conversion de Markdown
# --------------------------------------------------------------------------- #
def es_separador_tabla(linea):
    return bool(re.match(r"^\|[\s:|-]+\|$", linea.strip()))


def celdas_de(linea):
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def agregar_tabla(doc, filas):
    cabecera = celdas_de(filas[0])
    cuerpo = [celdas_de(f) for f in filas[2:]]
    tabla = doc.add_table(rows=1, cols=len(cabecera))
    tabla.style = "Table Grid"
    tabla.autofit = True

    for i, titulo in enumerate(cabecera):
        celda = tabla.rows[0].cells[i]
        celda.text = ""
        p = celda.paragraphs[0]
        texto_con_formato(p, titulo, base_negrita=True)
        for run in p.runs:
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombrear_celda(celda, "1F3B63")

    for datos in cuerpo:
        celdas = tabla.add_row().cells
        for i, valor in enumerate(datos[: len(cabecera)]):
            celdas[i].text = ""
            p = celdas[i].paragraphs[0]
            texto_con_formato(p, valor)
            for run in p.runs:
                run.font.size = Pt(9)
    doc.add_paragraph()


def convertir(doc, contenido):
    lineas = contenido.split("\n")
    i = 0
    en_codigo = False
    buffer_codigo = []

    while i < len(lineas):
        linea = lineas[i]
        despojada = linea.strip()

        # Bloques de codigo
        if despojada.startswith("```"):
            if en_codigo:
                p = doc.add_paragraph()
                run = p.add_run("\n".join(buffer_codigo))
                run.font.name = "Consolas"
                run.font.size = Pt(8.5)
                p.paragraph_format.left_indent = Cm(0.6)
                p.paragraph_format.space_after = Pt(10)
                buffer_codigo, en_codigo = [], False
            else:
                en_codigo = True
            i += 1
            continue
        if en_codigo:
            buffer_codigo.append(linea)
            i += 1
            continue

        # Separador horizontal
        if despojada in ("---", "***", "___"):
            i += 1
            continue

        # Vacia
        if not despojada:
            i += 1
            continue

        # Tabla
        if despojada.startswith("|") and i + 1 < len(lineas) and es_separador_tabla(lineas[i + 1]):
            bloque = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                bloque.append(lineas[i])
                i += 1
            agregar_tabla(doc, bloque)
            continue

        # Encabezados
        m = re.match(r"^(#{1,4})\s+(.+)$", despojada)
        if m:
            nivel, titulo = len(m.group(1)), m.group(2)
            titulo = re.sub(r"[*`]", "", titulo)
            h = doc.add_heading(level=min(nivel, 4))
            run = h.add_run(titulo)
            run.font.color.rgb = AZUL
            i += 1
            continue

        # Cita
        if despojada.startswith(">"):
            bloque = []
            while i < len(lineas) and lineas[i].strip().startswith(">"):
                bloque.append(lineas[i].strip().lstrip(">").strip())
                i += 1
            texto = " ".join(x for x in bloque if x)
            if texto:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.8)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(8)
                texto_con_formato(p, texto)
                for run in p.runs:
                    run.font.size = Pt(9.5)
                    if run.font.color.rgb is None:
                        run.font.color.rgb = GRIS
            continue

        # Lista (con continuaciones indentadas)
        m = re.match(r"^([-*])\s+(.+)$", despojada)
        if m:
            item = m.group(2)
            i += 1
            while i < len(lineas):
                sig = lineas[i]
                if sig.startswith("  ") and sig.strip() and not re.match(r"^\s*[-*]\s", sig):
                    item += " " + sig.strip()
                    i += 1
                else:
                    break
            item = re.sub(r"^\[[ x]\]\s*", "", item)
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(3)
            texto_con_formato(p, item)
            for run in p.runs:
                run.font.size = Pt(10)
            continue

        # Parrafo normal: el Markdown viene cortado a 80 columnas, asi que se
        # acumulan las lineas consecutivas hasta la proxima linea en blanco o
        # el proximo elemento de bloque. Sin esto, cada linea del fuente se
        # convertiria en un parrafo suelto y la negrita partida entre dos
        # lineas no se resolveria.
        bloque = []
        while i < len(lineas):
            actual = lineas[i].strip()
            if not actual:
                break
            if re.match(r"^(#{1,4}\s|>|\||```|---$|\*\*\*$|___$)", actual):
                break
            if re.match(r"^[-*]\s", actual):
                break
            bloque.append(actual)
            i += 1
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        texto_con_formato(p, " ".join(bloque))


# --------------------------------------------------------------------------- #
def main():
    ruta_backlog, ruta_plan, ruta_salida = sys.argv[1], sys.argv[2], sys.argv[3]
    doc = docx.Document()

    # Estilo base
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    for seccion in doc.sections:
        seccion.top_margin = Cm(2.5)
        seccion.bottom_margin = Cm(2.5)
        seccion.left_margin = Cm(2.5)
        seccion.right_margin = Cm(2.5)

    # ---- Portada ----
    for _ in range(6):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("TexCore")
    run.bold = True
    run.font.size = Pt(34)
    run.font.color.rgb = AZUL

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Product Backlog y Planificacion de Sprints")
    run.font.size = Pt(17)
    run.font.color.rgb = GRIS

    doc.add_paragraph()
    for linea, tam in (
        ("Sistema de digitalizacion y seguimiento de Ordenes de Produccion", 11),
        ("Interfibra S.A.", 11),
        ("", 11),
        ("Brandon Arellano", 12),
        ("Proyecto Capstone", 11),
        ("Universidad de las Americas", 11),
        ("", 11),
        ("23 de septiembre de 2026", 10),
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(linea)
        run.font.size = Pt(tam)
        if linea in ("Brandon Arellano",):
            run.bold = True

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Documento derivado de las secciones 5.1 y 5.2 y de la Tabla 14 "
        "del documento Capstone. Marco de trabajo Scrum."
    )
    run.font.size = Pt(9)
    run.italic = True
    run.font.color.rgb = GRIS

    # ---- Indice ----
    doc.add_section(WD_SECTION.NEW_PAGE)
    h = doc.add_heading(level=1)
    run = h.add_run("Indice")
    run.font.color.rgb = AZUL
    insertar_indice(doc)

    # ---- Parte I: Backlog ----
    doc.add_section(WD_SECTION.NEW_PAGE)
    convertir(doc, open(ruta_backlog, encoding="utf-8").read())

    # ---- Parte II: Planificacion ----
    doc.add_section(WD_SECTION.NEW_PAGE)
    convertir(doc, open(ruta_plan, encoding="utf-8").read())

    # ---- Numeracion de pagina ----
    for seccion in doc.sections:
        p = seccion.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        for etiqueta, attrs, texto in (
            ("w:fldChar", {"w:fldCharType": "begin"}, None),
            ("w:instrText", {"xml:space": "preserve"}, "PAGE"),
            ("w:fldChar", {"w:fldCharType": "end"}, None),
        ):
            elem = OxmlElement(etiqueta)
            for k, v in attrs.items():
                elem.set(qn(k) if ":" in k else k, v)
            if texto:
                elem.text = texto
            run._r.append(elem)
        run.font.size = Pt(9)

    doc.save(ruta_salida)

    tablas = len(doc.tables)
    parrafos = len(doc.paragraphs)
    print("DOCX generado:", ruta_salida)
    print("Tablas:", tablas, "| Parrafos:", parrafos, "| Secciones:", len(doc.sections))


if __name__ == "__main__":
    main()
