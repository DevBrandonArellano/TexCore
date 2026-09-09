# Manual de Usuario — Tintorero

## 1. ¿Qué hace usted en TexCore?

Usted es el especialista en color y formulación química: crea y mantiene las recetas de color que usa producción, y consulta el stock de químicos disponible para tinturar.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Tintorería**, con dos pestañas: **Fórmulas Químicas** y **Stock Disponible**.

## 3. Pestaña Fórmulas Químicas

Aquí se gestionan las recetas de color por tipo de sustrato (tipo de tela/hilo):

- **Crear/editar/versionar** una fórmula: cada vez que se ajusta una receta, el sistema guarda la nueva versión sin perder el historial de las anteriores.
- **Calculadora de pesajes**: se ingresa el volumen de tela y la relación de baño, y el sistema calcula los gramajes exactos de cada químico a dosificar.
- **Sincronización Infotint**: permite exportar la fórmula en formato JSON listo para cargar directamente en las máquinas dosificadoras automáticas.
- **Fórmulas en pruebas vs. aprobadas**: el sistema distingue visualmente las que aún están en fase de laboratorio de las ya aprobadas para producción — debe verificarse que una fórmula esté aprobada antes de usarla en una orden real.

## 4. Pestaña Stock Disponible

Muestra la tabla de químicos con Código, Descripción, Cantidad y Stock Mínimo, más tres indicadores: **Total**, **Stock Bajo** y **Disponibles**. Los productos por debajo del mínimo aparecen con una etiqueta roja **STOCK BAJO**.

Al hacer clic en un químico se muestra su **historial de descargas** (consumos registrados contra ese insumo).

> Importante: el stock de químicos **no se descuenta manualmente**. El descuento ocurre automáticamente cuando el Jefe de Planta crea o modifica una Orden de Producción con la fórmula correspondiente asignada. Esta pestaña sirve para **consultar** el resultado, no para operarlo.

## 5. Preguntas frecuentes

**Se necesita que una fórmula deje de estar "en pruebas".** Aprobarla es una decisión de calidad — debe coordinarse con el Jefe de Área o Administrador antes de marcarla como aprobada, ya que producción la usará tal cual.

**El stock de un químico bajó sin que se haya consumido directamente.** Es normal: baja automáticamente cada vez que se crea o ajusta una Orden de Producción que usa la fórmula correspondiente. Puede revisarse el historial de descargas de ese químico para ver en qué orden se utilizó.

**¿Cómo se evitan errores de dosificación?** Se recomienda usar siempre la calculadora integrada de la pestaña Fórmulas Químicas en vez de calcular manualmente — debe considerarse la relación de baño real de la orden.
