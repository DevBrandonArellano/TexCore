# Grafo de Conocimiento y Navegación del Código (Graphify)

TexCore utiliza **Graphify** para construir un grafo de conocimiento local e interactivo que mapea todas las clases, funciones, modelos, relaciones y dependencias dentro de la base de código. Este grafo sirve tanto para desarrolladores como para que los agentes de IA (como Claude o Antigravity) entiendan la arquitectura del proyecto sin necesidad de realizar lecturas completas y costosas de archivos.

---

## 1. Estructura de Salida (`graphify-out/`)

El análisis de Graphify genera y mantiene los siguientes archivos dentro del directorio `graphify-out/` (excluido en `.gitignore`):

* **`graph.json`**: El modelo de datos completo del grafo (nodos, aristas y pertenencia a comunidades).
* **`graph.html`**: Visualización interactiva en 3D/2D del grafo completo. Se puede abrir directamente en cualquier navegador web.
* **`GRAPH_REPORT.md`**: Reporte técnico detallado con métricas de cohesión, comunidades de código, acoplamiento, nodos principales (God Nodes) y dependencias sorprendentes.
* **`AGENTS.md`**: Reglas de contexto de Graphify para que herramientas y agentes externos consuman el grafo prioritariamente antes de realizar búsquedas directas.

---

## 2. Configuración de Exclusiones (`.graphifyignore`)

Para optimizar el rendimiento de la extracción y evitar la saturación del grafo con dependencias externas o archivos no ejecutables, se configuró el archivo [.graphifyignore](../../.graphifyignore) en la raíz del proyecto. Este archivo excluye:

* Dependencias externas (`node_modules/`, `bower_components/`).
* Carpetas de compilación y empaquetado (`dist/`, `build/`, `.next/`, `out/`, `target/`).
* Entornos virtuales de Python (`venv/`, `.venv/`, `env/`, `.env/`).
* Directorios y cachés de herramientas (`.git/`, `.agent/`, `.claude/`, `.gemini/`, `.omc/`, `.pytest_cache/`, `logs/`, `__pycache__/`).
* Archivos multimedia y binarios pesados (`*.png`, `*.jpg`, `*.zip`, `*.pdf`, etc.).

---

## 3. Automatización y Ciclo de Vida del Grafo

Para garantizar que el grafo de conocimiento nunca quede desactualizado, se han establecido tres mecanismos de actualización:

### A. Git Hooks (Automático en Commits y Ramas)
Se instalaron hooks mediante el comando `graphify hook install`.
* Cada vez que se realiza un commit (`post-commit`) o se cambia de rama (`post-checkout`), el grafo y el reporte se regeneran automáticamente en segundo plano de manera incremental.

### B. Reglas del Agente (Automático en Edición)
Se configuró la integración nativa con el agente a través del archivo de reglas [.agents/rules/graphify.md](../../.agents/rules/graphify.md).
* Cada vez que el asistente de IA realiza un cambio de código en la sesión, ejecutará de forma proactiva `graphify update .` antes de finalizar para mantener el grafo alineado.

### C. Escucha en Tiempo Real (Manual)
Durante sesiones de desarrollo activas, puedes dejar corriendo el observador de cambios:
```powershell
graphify watch .
```
Esto escuchará el sistema de archivos y actualizará el grafo en tiempo real al guardar cambios.

---

## 4. Comandos de Utilidad

* **Visualizar Grafo Interactivo:** Abre directamente `graphify-out/graph.html` en un navegador web.
* **Generar Árbol de Directorios en D3:**
  ```powershell
  graphify tree --output graphify-out/GRAPH_TREE.html
  ```
  Esto genera una representación jerárquica colapsable que facilita la navegación en repositorios grandes.
* **Consultas directas al Grafo:**
  * Encontrar el camino más corto entre dos módulos:
    ```powershell
    graphify path "ModuloA" "ModuloB"
    ```
  * Obtener un resumen de un módulo y sus vecinos:
    ```powershell
    graphify explain "ClasePrincipal"
    ```
