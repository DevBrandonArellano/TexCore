# Grafo de Conocimiento y Navegación del Código (Graphify)

TexCore usa **Graphify** para construir un grafo de conocimiento local con las clases, funciones, modelos, relaciones y dependencias del código. El grafo sirve a los desarrolladores y a los agentes de IA (Claude, Antigravity) para entender la arquitectura sin leer archivos completos.

---

## 1. Estructura de salida (`graphify-out/`)

El grafo **se versiona en el repositorio**, así que cualquier clon lo trae listo para consultar:

| Archivo | Contenido |
|---|---|
| `graph.json` | Modelo de datos del grafo: nodos, aristas y comunidades |
| `GRAPH_REPORT.md` | Reporte con comunidades de código, acoplamiento, nodos principales (*god nodes*) y dependencias inesperadas |
| `AGENTS.md` | Reglas para que los agentes consulten el grafo antes de buscar en el código |
| `manifest.json` | Archivos analizados y su huella, para las actualizaciones incrementales |
| `converted/` | Documentos no textuales (por ejemplo, el backlog en Excel) convertidos a Markdown para incluirlos en el grafo |

`.gitignore` excluye solo los artefactos de trabajo: `graphify-out/cache/`, las carpetas por fecha `graphify-out/20*/`, `.graphify_analysis.json` y `.graphify_labels.json`.

---

## 2. Exclusiones (`.graphifyignore`)

[.graphifyignore](../../.graphifyignore), en la raíz, deja fuera del análisis:

* dependencias externas (`node_modules/`, `bower_components/`);
* carpetas de compilación (`dist/`, `build/`, `.next/`, `out/`, `target/`);
* entornos virtuales de Python (`venv/`, `.venv/`, `env/`);
* directorios y cachés de herramientas (`.git/`, `.agent/`, `.claude/`, `.gemini/`, `.omc/`, `.pytest_cache/`, `logs/`, `__pycache__/`);
* binarios y multimedia (`*.png`, `*.jpg`, `*.zip`, `*.pdf`, etc.).

---

## 3. Cómo se mantiene actualizado

### A. Después de cada cambio de código (obligatorio)

`CLAUDE.md` (§1) y [.agents/rules/graphify.md](../../.agents/rules/graphify.md) exigen ejecutar, al terminar de modificar código:

```bash
graphify update .
```

Reextrae solo el AST de los archivos cambiados (sin costo de API) y reescribe `graph.json` y `GRAPH_REPORT.md`, que se versionan junto con el cambio.

### B. Hook `post-commit` (opcional, por desarrollador)

Los hooks de Git no se versionan. Quien quiera la actualización automática puede crear `.git/hooks/post-commit` (ejecutable):

```bash
#!/bin/bash
# Actualiza el grafo de conocimiento después de cada commit
graphify . --code-only --quiet 2>/dev/null || true
```

### C. Observador en tiempo real (manual)

```bash
graphify watch .
```

Reconstruye el grafo al guardar cambios mientras dure la sesión.

---

## 4. Consultas

| Necesidad | Comando |
|---|---|
| Pregunta sobre el código (recorrido acotado del grafo) | `graphify query "¿cómo se calcula el MRP por sede?"` |
| Camino más corto entre dos conceptos | `graphify path "MRPEngine" "ReposicionService"` |
| Resumen de un nodo y sus vecinos | `graphify explain "DescargaQuimicosService"` |
| Qué se ve afectado si cambia algo | `graphify affected "MovimientoInventario"` |
| Árbol HTML navegable del grafo | `graphify tree` |

Para una revisión general de la arquitectura, `GRAPH_REPORT.md`; para el resto, primero `query`, `path` o `explain`, y solo después la lectura de archivos.
