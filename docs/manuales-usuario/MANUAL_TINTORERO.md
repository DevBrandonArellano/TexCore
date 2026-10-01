# Manual de Usuario — Tintorero

## 1. ¿Qué hace usted en TexCore?

Usted es el especialista en color y formulación química: crea y mantiene las recetas de color que usa producción, registra los ensayos de laboratorio, decide qué versión de cada receta es la **oficial** para planta y consulta el stock y las descargas de químicos.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Tintorería** y tiene cuatro pestañas: **Fórmulas**, **Stock de Químicos**, **Historial de Órdenes** y **Descargas de Químicos**.

## 3. Pestaña Fórmulas

La tabla **Fórmulas Químicas** muestra, por cada fórmula, su **Código**, **Nombre**, **Estado** (*En Pruebas* / *Aprobada*) y **Versión oficial** (por ejemplo `v2`, o `—` si todavía no tiene). Tiene un buscador y la casilla **Mostrar fórmulas de laboratorio**: las fórmulas marcadas como de laboratorio se ocultan por defecto.

Arriba está **Nueva Fórmula**. Cada fila tiene tres botones:

| Botón | Qué hace |
|---|---|
| ✏️ **Editar** | Abre el editor de la receta (ver 3.1). |
| 👁 **Ver detalle** | Abre la fórmula con sus pestañas de receta, dosificación, versiones, derivadas y órdenes (ver 3.2). |
| 📄 **Crear variante** | Pide un **Código** y un **Nombre del color** nuevos y crea otra fórmula con la misma receta actual, *En Pruebas* y sin versiones. Sirve para desarrollar un color parecido sin tocar el original. |

### 3.1 Editar una receta (la receta «viva»)

Una receta se compone de **fases** (baños) en orden; con **Agregar Fase** se añade una nueva. En cada fase se indican:

- **Proceso**: se elige del catálogo de procesos de tintorería de su sede (por ejemplo *Descrude Alcalino*, *Tintura Principal*, *Jabonado Final*). Si la lista dice *«Sin procesos en el catálogo»*, pida al Administrador de Sistemas que gestione su registro (hoy lo carga el equipo técnico).
- **Ciclo** (opcional), **Temperatura (°C)** y **Tiempo (min)**.
- **Insumos**: cada químico o colorante con su dosificación en **g/L** (concentración en el baño) o en **% (Agot.)** (agotamiento sobre el peso de la tela).

La casilla **Fórmula de laboratorio** marca las fórmulas que son solo de laboratorio.

Guardar el editor **cambia la receta viva** y no pide motivo. La receta viva es el borrador de trabajo: **no afecta a ninguna orden**, porque las órdenes usan versiones congeladas (ver 3.3). El **Estado** se muestra en el editor pero no se cambia allí: pasa a *Aprobada* al marcar una versión como oficial.

Herramientas del editor:
- **Pesaje en Laboratorio**: se ingresa el peso de tela (kg) y los litros de baño, y el sistema calcula los gramajes de cada insumo.
- **Exportar Dosificador (Infotint)**: exporta la fórmula en el formato que cargan las máquinas dosificadoras.

### 3.2 Detalle de una fórmula

**Ver detalle** muestra en la cabecera el código, el color, la versión oficial (o **Sin oficial**) y, si corresponde, la etiqueta **Laboratorio**, junto al botón **Editar receta**. Debajo, cinco pestañas:

| Pestaña | Qué muestra |
|---|---|
| **Receta** | Las fases con sus procesos, temperaturas, tiempos e insumos. |
| **Dosificación** | Ingrese **Peso de la tela (kg)** y **Litros de baño** y pulse **Calcular**: el sistema devuelve la cantidad de cada químico (kg y g) según la receta viva y la relación de baño resultante. |
| **Versiones** | Los ensayos y la versión oficial (ver 3.3). |
| **Derivadas** | Las fórmulas derivadas de esta: código, color, versión de origen («Desde»), estado y motivo. |
| **Órdenes** | Las órdenes de producción que usaron la fórmula: código, estado, peso, litros de baño y **versión usada**. |

### 3.3 Versiones: ensayos y versión oficial

1. **Guardar un ensayo.** En la pestaña **Versiones**, **Guardar versión actual (ensayo)** congela la receta viva como una versión nueva (`v1`, `v2`…). Pide **Observaciones del ensayo** (mínimo 10 caracteres, por ejemplo *«sale muy rojizo, falta igualación»*). Una fórmula en desarrollo acumula ensayos sin versión oficial: es lo normal.
2. **Marcar oficial.** Cuando un ensayo es el bueno, pulse **Marcar oficial** en esa versión. Pasa a ser la versión que usará planta, la anterior deja de serlo y la fórmula queda *Aprobada*. También se puede volver a una versión anterior marcándola oficial de nuevo.
3. **Ver receta** (ícono de ojo): muestra la receta exacta de esa versión, aunque la receta viva haya cambiado después.
4. **Comparar versiones**: con dos o más versiones, elija *Desde* y *Hasta* y pulse **Comparar**. Se ven los cambios en los datos de la fórmula, las fases agregadas o eliminadas y, en cada fase, los campos e insumos que cambiaron.
5. **Derivar desde una versión** (ícono de bifurcación): crea una fórmula **nueva** a partir de esa versión. Pide **Código**, **Nombre del color**, **Sustrato** (opcional; por defecto el del origen) y **Motivo de la derivación** (opcional). La nueva fórmula empieza *En Pruebas* con su propio historial y aparece en la pestaña **Derivadas** del origen.

Las versiones son **inmutables**: no se editan ni se borran.

### 3.4 Qué versión usa producción

- Una orden con fórmula **solo puede lanzarse si la fórmula tiene versión oficial**. Si no la tiene, planta recibe el mensaje *«La fórmula no tiene una versión oficial: apruébela antes de lanzar la orden»*.
- Al lanzarse (normalmente al registrar su primer lote), la orden **fija la versión oficial vigente** y la conserva aunque usted marque otra después.
- Una fórmula con órdenes asociadas no se puede eliminar.

## 4. Pestaña Stock de Químicos

Muestra los químicos con **Código**, **Descripción**, **Cantidad (kg)**, **Disponible (kg)**, **Mínimo (kg)** y **Estado**, y tres indicadores: **Total Químicos**, **Stock Bajo** y **Disponibles**. Con el botón de la columna **Acciones** se ve el historial de descargas de ese químico.

> El stock de químicos **no se descuenta a mano**: baja automáticamente cuando se crea o ajusta una orden de producción con fórmula. Esta pestaña es de consulta.

## 5. Pestaña Historial de Órdenes

Lista las órdenes con fórmula, filtrables por **Desde**, **Hasta**, **Máquina**, **Fórmula** y **Estado**. Por cada orden: código, producto, fórmula, versión, peso, litros de baño, relación de baño, máquina y estado. El botón de descargas muestra los químicos que se descontaron para esa orden.

## 6. Pestaña Descargas de Químicos

Elija un químico en **Selecciona un químico** para ver todas sus descargas: fecha, orden, bodega, cantidad y estado.

## 7. Preguntas frecuentes

**¿Cuándo marco una versión como oficial?** Cuando el ensayo ya fue validado en laboratorio. Desde ese momento producción puede lanzar órdenes con ella; coordínelo con el Jefe de Área o de Planta.

**Edité la receta y planta sigue produciendo con la anterior.** Es correcto: la receta viva no afecta a planta. Guarde un ensayo y márquelo oficial para que lo usen las órdenes que se lancen después.

**Me equivoqué en una versión, ¿puedo borrarla?** No. Corrija la receta viva, guarde un ensayo nuevo y márquelo oficial.

**¿Variante o derivada?** **Crear variante** (en la lista) copia la receta viva. **Derivar** (en Versiones) parte de una versión concreta y queda registrada como derivada del origen. En ambos casos se crea una fórmula nueva.

**No encuentro una fórmula en la lista.** Puede ser de laboratorio: marque **Mostrar fórmulas de laboratorio**.

**No encuentro el proceso que necesito en las fases.** El catálogo de procesos de tintorería es por sede; pida al Administrador de Sistemas que gestione su registro.
