# Guía de importación a Jira — TexCore

> Guía paso a paso para crear el proyecto en Jira desde cero e importar el backlog
> completo. Escrita asumiendo que **es la primera vez que usas Jira**.
>
> **Archivo a importar:** `texcore_jira_import.csv` (63 filas: 9 épicas + 54 historias)
> **Tiempo estimado:** 30–40 minutos

---

## Antes de empezar: cómo se organiza Jira

Tres conceptos y el resto se entiende solo:

| Concepto | Qué es | En TexCore |
|---|---|---|
| **Proyecto** | El contenedor de todo el trabajo | TexCore (clave `TEX`) |
| **Issue** | Una unidad de trabajo. Tiene un tipo: Epic, Story, Task, Bug | 9 Epics + 54 Stories |
| **Board** | El tablero donde se visualiza y se gestionan los sprints | Un board Scrum |

La jerarquía del archivo es **Epic → Story**. Cada épica corresponde a un sprint del
documento Capstone, y cada historia cuelga de su épica.

> **Importante:** los sprints **no se crean con la importación**. Se crean en el board
> y la importación asigna las historias a ellos por su nombre. Por eso el orden de los
> pasos importa: primero el proyecto, luego el board, luego la importación.

---

## Paso 1 · Crear la cuenta

1. Entra en **https://www.atlassian.com/software/jira** y pulsa **Get it free**.
2. Regístrate con tu correo.
3. Elige **Jira Software** y el plan **Free** (hasta 10 usuarios, suficiente para el
   proyecto).
4. Define el nombre de tu sitio: quedará como `<tu-nombre>.atlassian.net`. Anótalo.

---

## Paso 2 · Crear el proyecto (el paso crítico)

1. Pulsa **Create project**.
2. Elige la plantilla **Scrum**.
3. Cuando pregunte por el tipo de proyecto, elige **Company-managed project**.

> ### ⚠️ Esta elección es irreversible
>
> Jira ofrece *Team-managed* y *Company-managed*. **Debe ser Company-managed.**
>
> El importador de CSV solo gestiona de forma fiable los campos **Epic Link**,
> **Sprint** y **Story Points** en proyectos company-managed. En un proyecto
> team-managed la importación deja las historias sueltas, sin vincular a sus épicas
> ni a sus sprints, y **el tipo de proyecto no se puede cambiar después**: habría que
> borrar el proyecto y empezar de nuevo.
>
> Si no ves la opción, busca el enlace pequeño **"Show more templates"** o
> **"Select a project type"** al final del formulario.

4. **Nombre del proyecto:** `TexCore`
5. **Clave del proyecto:** `TEX` — respétala, porque las referencias del backlog usan
   ese prefijo.
6. Pulsa **Create**.

---

## Paso 3 · Habilitar el campo Story Points

En algunos proyectos nuevos el campo de estimación no viene activo. Compruébalo antes
de importar:

1. Abre el proyecto → **Project settings** (rueda dentada, abajo a la izquierda).
2. Entra en **Features**.
3. Verifica que **Estimation** esté activado.
4. Entra en **Board settings → Estimation** y confirma que *Estimation Statistic* sea
   **Story Points**.

Si el campo no existe al llegar al mapeo del paso 6, vuelve aquí.

---

## Paso 4 · Crear el board y los nueve sprints

1. En el menú lateral del proyecto, abre **Backlog**.
2. Verás un sprint vacío creado por defecto, llamado `TEX Sprint 1`.
3. Renómbralo: pulsa sobre los tres puntos `···` junto a su nombre → **Edit sprint** →
   escribe exactamente **`Sprint 0`** → **Update**.
4. Pulsa **Create sprint** ocho veces más y renombra cada uno, en orden, a:

```
Sprint 0     Sprint 1     Sprint 2     Sprint 3     Sprint 4
Sprint 5     Sprint 6     Sprint 7     Sprint 8
```

> **El nombre debe coincidir carácter por carácter** con la columna `Sprint` del CSV.
> `Sprint 1` funciona; `sprint 1`, `Sprint  1` (dos espacios) o `TEX Sprint 1` no.

5. **Opcional pero recomendado:** en cada sprint, pulsa `···` → **Edit sprint** y
   carga las fechas del documento Capstone:

| Sprint | Start date | End date |
|---|---|---|
| Sprint 0 | 21/Sep/26 | 02/Oct/26 |
| Sprint 1 | 05/Oct/26 | 16/Oct/26 |
| Sprint 2 | 19/Oct/26 | 30/Oct/26 |
| Sprint 3 | 02/Nov/26 | 13/Nov/26 |
| Sprint 4 | 16/Nov/26 | 27/Nov/26 |
| Sprint 5 | 30/Nov/26 | 11/Dic/26 |
| Sprint 6 | 14/Dic/26 | 25/Dic/26 |
| Sprint 7 | 04/Ene/27 | 15/Ene/27 |
| Sprint 8 | 18/Ene/27 | 29/Ene/27 |

---

## Paso 5 · Abrir el importador

1. Pulsa el engranaje ⚙ de la **barra superior** (no el de Project settings) →
   **System**.
2. En el menú lateral izquierdo, al final, busca **Import and Export** →
   **External System Import**.
3. Elige **CSV**.

> **Ruta directa:** `https://<tu-sitio>.atlassian.net/secure/admin/ExternalImport1.jspa`
>
> Si no ves esta opción, tu usuario no es administrador del sitio. Al haber creado tú
> la cuenta, deberías serlo; comprueba que iniciaste sesión con la cuenta correcta.

---

## Paso 6 · Cargar el archivo y mapear los campos

1. **Select CSV file:** elige `texcore_jira_import.csv`.
2. Despliega **Advanced** y confirma que el delimitador sea la **coma** `,` y la
   codificación **UTF-8**.
3. Pulsa **Next**.
4. **Select project:** elige el proyecto **TexCore (TEX)** ya creado. No dejes que
   Jira cree uno nuevo.
5. Pulsa **Next** y llega a la pantalla de mapeo de campos.

### Mapeo de columnas

| Columna del CSV | Mapear a | Nota |
|---|---|---|
| `Issue Type` | **Issue Type** | Distingue Epic de Story |
| `Issue Key` | **⚠️ No mapear** (*Don't map this field*) | Ver la advertencia de abajo |
| `Summary` | **Summary** | Obligatorio |
| `Description` | **Description** | Contiene los criterios de aceptación |
| `Priority` | **Priority** | High / Medium / Low |
| `Story Points` | **Story Points** | Si no aparece, vuelve al Paso 3 |
| `Sprint` | **Sprint** | Debe coincidir con los nombres del Paso 4 |
| `Epic Name` | **Epic Name** | Solo lo usan las 9 filas de tipo Epic |
| `Epic Link` | **Epic Link** | Vincula cada historia con su épica |
| `Status` | **Status** | Todo entra como `To Do` |
| `Labels` (las tres) | **Labels** | Mapea **las tres columnas** a Labels |

> ### ⚠️ No mapees la columna `Issue Key`
>
> Si la mapeas, Jira intentará forzar las claves `TEX-1`…`TEX-63` y puede fallar la
> importación entera por conflictos de numeración. Déjala sin mapear: el
> identificador de cada historia ya viaja dentro del `Summary`
> («TEX-12 Registro de lote…») y en la sección *TRAZABILIDAD* de la descripción.

6. Marca **Map field value** únicamente si Jira te lo pide para `Priority` o `Status`.
7. Pulsa **Next** y luego **Begin Import**.

---

## Paso 7 · Verificar la importación

Al terminar, Jira muestra cuántos issues creó. **Deben ser 63.**

Comprueba lo siguiente antes de darlo por bueno:

- [ ] **63 issues creados** (9 Epics + 54 Stories)
- [ ] En **Backlog**, los nueve sprints tienen historias asignadas
- [ ] Los puntos por sprint coinciden:

| Sprint | Puntos esperados |
|---|---:|
| Sprint 0 | 21 |
| Sprint 1 | 32 |
| Sprint 2 | 32 |
| Sprint 3 | 32 |
| Sprint 4 | 32 |
| Sprint 5 | 37 |
| Sprint 6 | 37 |
| Sprint 7 | 34 |
| Sprint 8 | 31 |
| **Total** | **288** |

- [ ] Abriendo cualquier historia, la descripción muestra la narrativa y sus criterios
      de aceptación
- [ ] Cada historia tiene su épica en el campo **Epic Link**
- [ ] Los acentos se ven correctamente (`Producción`, no `Producci√≥n`)

### Consulta rápida de verificación

Pega esto en la barra de búsqueda con **JQL** activado:

```jql
project = TEX ORDER BY Sprint ASC, "Story Points" DESC
```

Para contar por sprint:

```jql
project = TEX AND Sprint = "Sprint 5"
```

---

## Si algo sale mal

| Síntoma | Causa | Solución |
|---|---|---|
| Las historias no quedan en ningún sprint | Los sprints no existían al importar, o el nombre no coincide | Crea los sprints (Paso 4) con el nombre exacto y reimporta |
| Las historias no cuelgan de su épica | El proyecto es team-managed, o `Epic Link` quedó sin mapear | Verifica el tipo de proyecto; si es team-managed hay que recrearlo |
| `Story Points` no aparece en el mapeo | El campo de estimación está desactivado | Paso 3, luego reimporta |
| Acentos rotos (`Producci√≥n`) | El importador no leyó UTF-8 | En **Advanced**, fuerza la codificación a UTF-8 |
| La importación falla entera | `Issue Key` fue mapeado | Repite sin mapear esa columna |
| Se duplicaron los issues | Se importó dos veces | Ver abajo cómo borrar en lote |

### Deshacer una importación

1. Ve a **Filters → View all issues**.
2. Filtra con JQL: `project = TEX`.
3. Selecciona todo con la casilla de cabecera → **Bulk change** → **Delete Issues**.
4. Repite la importación corrigiendo el problema.

> El plan Free no ofrece «deshacer importación», así que el borrado en lote es la vía.

---

## Después de importar

### Regenerar el CSV si cambia el backlog

El CSV **se genera desde `PRODUCT_BACKLOG.md`**, que es la única fuente de verdad. Si
modificas el backlog, vuelve a generarlo en lugar de editar el CSV a mano:

```bash
python generar_csv_jira.py docs/gestion-proyecto/PRODUCT_BACKLOG.md \
                           docs/gestion-proyecto/texcore_jira_import.csv
```

### Iniciar el primer sprint

En **Backlog**, pulsa **Start sprint** sobre Sprint 0. A partir de ahí Jira habilita
el **burndown** en **Reports**, que es la evidencia de seguimiento para el documento
de tesis.

### Reportes útiles para la tesis

| Reporte | Dónde | Para qué sirve |
|---|---|---|
| **Burndown Chart** | Reports → Burndown | Avance dentro de un sprint |
| **Velocity Chart** | Reports → Velocity | Comparar comprometido contra completado |
| **Sprint Report** | Reports → Sprint Report | Resumen de cierre de cada sprint |
| **Cumulative Flow** | Reports → Cumulative Flow | Detectar cuellos de botella |

---

## Referencias

- `PRODUCT_BACKLOG.md` — las 54 historias con sus criterios de aceptación
- `PLANIFICACION_SPRINTS.md` — objetivos, DoD y riesgos de cada sprint
- Documento Capstone, §5.2 y Tabla 14 — fuente normativa de la planificación
- Documentación oficial: <https://support.atlassian.com/jira-cloud-administration/docs/import-data-from-a-csv-file/>
