# Manual de Usuario — Tintorero

## 1. ¿Qué hace usted en TexCore?

Usted es el especialista en color y formulación química: crea y mantiene las recetas de color que usa producción, las aprueba cuando están listas para planta, y consulta el stock de químicos disponible para tinturar.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Tintorería**, con dos pestañas: **Fórmulas Químicas** y **Stock Disponible**.

## 3. Pestaña Fórmulas Químicas

Aquí se gestionan las recetas de color por tipo de sustrato (tipo de tela/hilo). La tabla muestra, por cada fórmula, su **Código**, **Nombre**, **Estado** (En Pruebas / Aprobada) y **Versión oficial** (por ejemplo `v2`, o `—` si todavía no se aprobó nunca). Cada fila tiene estos botones:

| Botón | Qué hace |
|---|---|
| ✏️ **Editar** | Abre el editor de la receta. |
| ✔️ **Aprobar** | Solo aparece en fórmulas **En Pruebas**. Crea la versión oficial (ver 3.2). |
| 🕘 **Historial de versiones** | Abre el panel lateral con todas las versiones y la comparación entre ellas (ver 3.4). |
| 📄 **Crear variante** | Copia la receta en una fórmula nueva (ver 3.5). |

### 3.1 Editar una receta

Una receta se compone de **fases** (baños) en orden. En cada fase se elige:

- **Proceso**: se selecciona del catálogo de procesos de su sede (por ejemplo *Descrude Alcalino*, *Tintura Principal*, *Jabonado Final*). Solo aparecen los procesos activos. Si la lista dice *«Sin procesos en el catálogo»*, pida al Administrador de Sistemas que registre los procesos de la sede (el catálogo aún no tiene pantalla propia en el panel; se administra desde el panel de administración del sistema).
- **Ciclo**: número de ciclo de la hoja de tintura (opcional).
- **Temperatura (°C)** y **Tiempo (min)**.
- **Insumos**: cada químico o colorante con su dosificación en **g/L** (concentración en el baño) o en **%** (agotamiento sobre el peso de la tela).

El **estado** de la fórmula se muestra en el editor pero **no se cambia desde allí**: una fórmula solo se aprueba con el botón **Aprobar** de la lista.

- **Fórmula En Pruebas:** se edita libremente; los cambios se guardan sobre la misma receta, sin crear versiones (aún no se usó en producción).
- **Fórmula Aprobada:** el editor pide un **Motivo del cambio** (mínimo 10 caracteres). Al guardar, el sistema crea una **versión oficial nueva** (v2, v3…) y la anterior queda intacta en el historial.

### 3.2 Aprobar una fórmula

Al pulsar **Aprobar** se pide el **motivo de la aprobación** (mínimo 10 caracteres, por ejemplo *«Aprobada tras prueba de laboratorio»*). El sistema congela la receta tal como está en ese momento como **versión oficial v1** y la fórmula pasa a **Aprobada**.

> Una orden de producción con fórmula **solo puede lanzarse si su fórmula tiene versión oficial**. Si planta intenta lanzar una orden con una fórmula que sigue En Pruebas, el sistema lo rechaza con el mensaje *«La fórmula no tiene una versión oficial: apruébela antes de lanzar la orden»*.

### 3.3 Qué versión usa producción

Cuando una orden de producción se lanza (pasa de *Pendiente* a *En Proceso*, normalmente al registrar su primer lote), el sistema **fija en la orden la versión oficial vigente** de la fórmula. A partir de ese momento:

- Esa orden **siempre** queda asociada a esa versión, aunque usted edite la fórmula después: sus cambios crean una versión nueva que usarán las **próximas** órdenes.
- Una orden lanzada no puede cambiar de fórmula ni de versión.
- Una fórmula con órdenes asociadas **no se puede eliminar**: las órdenes conservan la receta con la que se produjeron.

### 3.4 Historial y comparación de versiones

El botón **Historial de versiones** abre un panel lateral con cada versión: número, etiqueta **Oficial** en la vigente, motivo, fecha y usuario que la creó.

Con dos o más versiones aparece **Comparar versiones**: elija *Desde* y *Hasta* y pulse **Comparar**. El sistema muestra qué cambió: datos de la fórmula, fases agregadas o eliminadas, y en cada fase modificada los campos cambiados (por ejemplo `temperatura: 90 → 95`) y los insumos agregados, eliminados o con otra dosificación.

### 3.5 Crear una variante

**Crear variante** pide un **código** y un **nombre de color** nuevos y crea otra fórmula con la misma receta, **En Pruebas** y **sin versiones**. Úsela para desarrollar un color parecido sin tocar la fórmula original. No es una versión nueva de la misma fórmula: para eso se edita la fórmula aprobada (ver 3.1).

### 3.6 Otras herramientas del editor

- **Pesaje en Laboratorio**: se ingresa el volumen de tela (kg) y la relación de baño, y el sistema calcula los gramajes de cada químico a dosificar.
- **Exportar Dosificador (Infotint)**: exporta la fórmula en formato JSON listo para cargar en las máquinas dosificadoras automáticas.

## 4. Pestaña Stock Disponible

Muestra la tabla de químicos con Código, Descripción, Cantidad y Stock Mínimo, más tres indicadores: **Total**, **Stock Bajo** y **Disponibles**. Los productos por debajo del mínimo aparecen con una etiqueta roja **STOCK BAJO**.

Al hacer clic en un químico se muestra su **historial de descargas** (consumos registrados contra ese insumo).

> Importante: el stock de químicos **no se descuenta manualmente**. El descuento ocurre automáticamente cuando el Jefe de Planta crea o modifica una Orden de Producción con la fórmula correspondiente asignada. Esta pestaña sirve para **consultar** el resultado, no para operarlo.

## 5. Preguntas frecuentes

**¿Cuándo debo aprobar una fórmula?** Cuando la receta ya fue validada en laboratorio. Aprobar es una decisión de calidad — coordínela con el Jefe de Área o el Administrador, porque desde ese momento producción puede lanzar órdenes con ella. Escriba en el motivo quién la validó o con qué prueba.

**Edité una fórmula aprobada, ¿se cambiaron las órdenes que ya están en proceso?** No. Las órdenes ya lanzadas conservan la versión con la que empezaron. Su cambio queda como versión nueva y la usarán las órdenes que se lancen de ahora en adelante.

**Me equivoqué al editar una fórmula aprobada, ¿puedo borrar la versión?** No: las versiones son inmutables, para que el historial sea confiable. Corrija la receta y guarde de nuevo con un motivo como *«Corrige error de la v3»*; se creará la v4.

**Planta no puede lanzar una orden y dice que la fórmula no tiene versión oficial.** La fórmula sigue En Pruebas. Apruébela (ver 3.2) si ya está validada.

**No encuentro el proceso que necesito en la lista de fases.** El catálogo de procesos es por sede; pida al Administrador de Sistemas que lo registre.

**El stock de un químico bajó sin que se haya consumido directamente.** Es normal: baja automáticamente cada vez que se crea o ajusta una Orden de Producción que usa la fórmula correspondiente. Puede revisarse el historial de descargas de ese químico para ver en qué orden se utilizó.

**¿Cómo se evitan errores de dosificación?** Se recomienda usar siempre la calculadora integrada del editor en vez de calcular manualmente — debe considerarse la relación de baño real de la orden.
