# Manual de Usuario — Empaquetado

## 1. ¿Qué hace usted en TexCore?

Usted es la última estación de producción: pesa, etiqueta y empaca el producto terminado. Su registro genera la etiqueta física que identifica cada bulto/caja hasta que llega al cliente, por lo que la exactitud del peso y del código de lote es crítica para toda la trazabilidad.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Estación de Empaque**.

## 3. Su panel principal

En la parte superior:
- **Selector de Impresión**: permite elegir cómo se imprimen las etiquetas — **Automático (Zebra → PDF)** (recomendado), **Zebra ZPL Nativo** o **PDF Universal (Navegador)**. La selección se guarda en el navegador de la estación.
- **Conectar Balanza (COM)**: si el puesto cuenta con una balanza conectada por cable USB/serial, debe hacerse clic aquí una vez al iniciar el turno — un punto verde confirma que está conectada y el peso se completará automáticamente.
- Tres indicadores del turno: **Bultos Empacados Hoy**, **Peso Total del Turno**, **Promedio por Bulto**.

Debajo, dos columnas: el formulario de registro (izquierda) y el **Historial Reciente** (derecha). Más abajo, el **Buscador de Lotes**.

## 4. Registrar un bulto/caja nuevo

1. En **Orden de Producción**, seleccione la orden activa correspondiente. El sistema muestra el progreso (kg producidos de los kg requeridos).
2. **Código Lote/Bulto**: normalmente se sugiere automáticamente; puede escribirse manualmente si el proceso lo requiere.
3. **Presentación**: Caja, Funda, Cono o Rollo. Al seleccionarla, el sistema sugiere una **Tara** automática que puede ajustarse manualmente.
4. **Unidades** y **Turno** (Mañana/Tarde/Noche).
5. **Peso Bruto (Kg)**: se completa solo si hay balanza conectada; de lo contrario, debe ingresarse manualmente.
6. **Tara (Kg)**: puede ajustarse si el empaque real difiere del valor sugerido.
7. **Hora de Inicio** y **Hora Final** de ese bulto (el sistema las usa para calcular el rendimiento del turno).
8. Si el producto es tela, aparece **Cantidad de Metros** (opcional).
9. Debe revisarse el **Peso Neto Calculado** (Peso Bruto − Tara), que se muestra en grande antes de confirmar.
10. Si se trata del último bulto de la orden, debe marcarse **Finalizar Orden de Producción**.
11. Haga clic en **Registrar e Imprimir Etiqueta** — la etiqueta se imprime automáticamente al guardar (Zebra, PDF, o se copia el código si no hay impresora disponible).

## 5. Reimprimir una etiqueta (etiqueta dañada, perdida o atasco)

1. En **Historial Reciente** o en el **Buscador de Lotes**, haga clic en el ícono de impresora (Reimprimir) junto al lote.
2. Seleccione el **motivo** (obligatorio: dañada, perdida, atasco de impresora, etc.).
3. Confirme — se imprime una copia **idéntica** a la original. Esta acción no requiere autorización de un supervisor, pero sí queda registrada en auditoría.

> Reimprimir no cambia ningún dato del lote — solo repite la misma etiqueta.

## 6. Solicitar un reetiquetado (corregir peso o calidad)

Si se detecta que el peso o la calidad de un lote ya registrado están incorrectos, **el operador de empaque no puede corregirlo directamente** — se requiere autorización del Jefe de Área o Supervisor:

1. En el **Buscador de Lotes**, ubique el lote y haga clic en **Reetiquetar**.
2. Se abre el formulario con los campos a corregir (peso neto y/o calidad).
3. El sistema solicita **usuario y contraseña del supervisor** en el mismo modal — el supervisor los ingresa allí mismo, sin necesidad de cerrar la sesión activa.
4. Debe escribirse el **motivo** del cambio (obligatorio).
5. Al confirmar, se imprime una **nueva versión** de la etiqueta. El código de lote y el código QR de trazabilidad **nunca cambian**, aunque el peso sí ajusta el stock automáticamente.

## 7. Control de tolerancia de peso

Si al pesar un bulto el sistema detecta que el peso difiere **más del 10%** de lo esperado, se mostrará una advertencia. Debe marcarse una casilla de confirmación explícita para poder continuar — se recomienda revisar la balanza antes de forzar el guardado.

## 8. Buscar lotes de otras fechas

El **Buscador de Lotes** permite encontrar bultos que no aparecen en el historial reciente, filtrando por rango de fechas, turno, código de lote o calidad. Desde allí también pueden reimprimirse etiquetas o, si hay un supervisor autorizando in situ, reetiquetarse.

## 9. Ver el historial de una etiqueta

Junto a cada lote en **Historial Reciente** hay un ícono de reloj que muestra todos los eventos de esa etiqueta (original, reimpresiones, reetiquetados), con fecha, usuario y motivo, y permite reimprimir la versión vigente desde allí mismo.

## 10. Preguntas frecuentes

**La balanza no se conecta.** Debe usarse Chrome o Edge (otros navegadores no soportan la conexión por puerto serial); si el problema persiste, el peso puede ingresarse manualmente.

**No hay impresora Zebra en el puesto.** Cambie el selector de impresión a "PDF Universal" — se abrirá un diálogo de impresión normal con cualquier impresora.

**Se cometió un error en el peso y el lote ya no está en el Historial Reciente.** Debe solicitarse al Jefe de Área que lo busque en el Buscador de Lotes y lo reetiquete — el rol de Empaquetado no tiene permiso para corregir peso/calidad directamente.
