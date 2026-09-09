# Manual de Usuario — Despacho

## 1. ¿Qué hace usted en TexCore?

Usted es el último control antes de que la mercancía salga de la bodega hacia el cliente. Verifica, escaneando cada bulto, que lo que se carga al camión coincide exactamente con lo que el pedido solicita.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Despacho**.

## 3. Su panel principal

Se muestra una tabla de **Pedidos Pendientes** con casillas de selección, buscador (por cliente o guía de remisión) y las columnas: Pedido, Cliente, Items, Estado (Pagado/Crédito) y Total Peso. Un pedido marcado **Parcial** indica que ya tuvo un despacho incompleto anterior y sigue pendiente por el resto.

Arriba a la derecha se encuentra el botón **Ver Historial**, que lleva al registro de despachos ya realizados (con lotes y pesos) y desde donde también se gestionan **devoluciones** (reingreso de mercancía previamente despachada).

## 4. Iniciar un despacho

1. Marque la casilla de uno o varios pedidos que van a salir en el mismo viaje.
2. Si se seleccionan pedidos de clientes distintos, el sistema advierte al respecto — debe confirmarse solo si es intencional (varios clientes en el mismo camión).
3. Haga clic en **Iniciar Despacho**.

## 5. Escanear y confirmar la carga

Al iniciar, se ingresa al modo **Procesando Despacho**:

1. En el campo de texto (con el foco automático), debe escanearse el **código de barras** de cada bulto/etiqueta a medida que se sube al camión. El cursor vuelve automáticamente al campo después de cada escaneo.
2. Cada lote escaneado aparece en la tabla de la izquierda con su producto y peso. Un ítem escaneado por error puede quitarse con la ✗.
3. A la derecha, **Estado de la Carga** compara en tiempo real lo **Requerido** contra lo **Escaneado**, producto por producto, con una barra de progreso que se pone verde al completarse.
4. Si se escanea un código ya escaneado, el sistema lo advierte y no lo duplica.

## 6. Finalizar el despacho

1. Cuando todo esté completo, haga clic en **Confirmar Salida**.
2. Si falta algo por escanear, aparece el aviso **Despacho incompleto** con una tabla de lo Requerido/Escaneado/Faltante por producto. Hay dos opciones:
   - **Cancelar — seguir escaneando**: regresa a la pantalla de escaneo.
   - **Despachar de todas formas**: confirma el despacho como **parcial**; lo que falta queda pendiente y el pedido se marca "Parcial" para completarlo después.
3. Al confirmar (completo o parcial), el sistema **rebaja el stock automáticamente** y genera la nota de venta/guía en PDF de lo efectivamente despachado, que se abre en una pestaña nueva por cada pedido.
4. Si se necesita cancelar antes de confirmar, debe usarse **Cancelar** para salir sin afectar nada.

## 7. Preguntas frecuentes

**Al escanear un código aparece "no válido o no disponible".** El lote puede no pertenecer a los pedidos seleccionados, estar ya despachado, o el código puede estar mal impreso o mal leído. Puede intentarse de nuevo o consultarse con el Bodeguero/Jefe de Área.

**Se necesita registrar una devolución.** Debe accederse a **Ver Historial** — allí se encuentra la opción para registrar el reingreso de mercancía ya despachada.

**El despacho quedó a medias, ¿se pierde lo escaneado?** No — al confirmarse como "parcial", lo escaneado se procesa y el resto del pedido queda pendiente en la lista con la etiqueta "Parcial" hasta completarlo.
