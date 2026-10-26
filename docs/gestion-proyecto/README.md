# Gestión del Proyecto — TexCore

Artefactos de gestión ágil del proyecto, derivados del documento Capstone
(`Anteproyecto_Capstone_Final_Version.docx`, §5.1, §5.2 y Tabla 14).

## Contenido

| Archivo | Qué es | Para quién |
|---|---|---|
| [`PRODUCT_BACKLOG.md`](PRODUCT_BACKLOG.md) | Las 54 historias de usuario con 166 criterios de aceptación en Gherkin | Desarrollo y tribunal |
| [`PLANIFICACION_SPRINTS.md`](PLANIFICACION_SPRINTS.md) | Los 9 sprints con objetivo, backlog, DoD, métricas y riesgos | Desarrollo y tribunal |
| [`GUIA_IMPORTACION_JIRA.md`](GUIA_IMPORTACION_JIRA.md) | Guía paso a paso para crear el proyecto en Jira e importar el backlog | Quien administre el proyecto |
| `texcore_jira_import.csv` | Archivo importable a Jira Cloud (63 filas) | Importación a Jira |
| `TexCore_Backlog_y_Planificacion_Sprints.docx` | Los dos documentos anteriores en Word, con portada e índice | Entrega universitaria |
| `generar_csv_jira.py` | Genera el CSV a partir del backlog | Mantenimiento |
| `generar_docx.py` | Genera el Word a partir de los dos Markdown | Mantenimiento |

## Fuente de verdad

**`PRODUCT_BACKLOG.md` es la única fuente de verdad.** El CSV y el Word se *generan*
a partir de los Markdown; no deben editarse a mano, porque el siguiente regenerado
descartaría los cambios.

Tras modificar el backlog o la planificación, regenera los derivados:

```bash
# CSV para Jira
python docs/gestion-proyecto/generar_csv_jira.py \
       docs/gestion-proyecto/PRODUCT_BACKLOG.md \
       docs/gestion-proyecto/texcore_jira_import.csv

# Word para la entrega
python docs/gestion-proyecto/generar_docx.py \
       docs/gestion-proyecto/PRODUCT_BACKLOG.md \
       docs/gestion-proyecto/PLANIFICACION_SPRINTS.md \
       docs/gestion-proyecto/TexCore_Backlog_y_Planificacion_Sprints.docx
```

Ambos scripts requieren `python-docx` (ya presente en el entorno de desarrollo).

## Cifras de control

Si tras regenerar estas cifras no coinciden, algo se rompió en el parseo:

| Métrica | Valor |
|---|---:|
| Épicas | 9 |
| Historias | 54 |
| Criterios de aceptación | 166 |
| Puntos de historia | 288 |
| Filas del CSV (sin cabecera) | 63 |
| Velocidad objetivo por sprint | 33 |

## Trazabilidad

Cada historia declara los requisitos que implementa (RF-01…RF-05, RNF-01…RNF-05) y,
cuando existe cobertura automatizada, el archivo de pruebas que la verifica junto con
la técnica ISTQB aplicada. La matriz completa está en la §8 del backlog y se
complementa con [`../matriz_trazabilidad_pruebas.md`](../matriz_trazabilidad_pruebas.md).
