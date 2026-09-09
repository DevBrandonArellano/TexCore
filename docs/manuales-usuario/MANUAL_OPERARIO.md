# Manual de Usuario — Operario

## 1. ¿Qué hace usted en TexCore?

Usted es quien registra, en la máquina, lo que realmente se produce: cuánto peso salió, cuántas unidades y si hubo desperdicio. Ese registro es lo que alimenta el stock, la trazabilidad y los indicadores de toda la planta — por eso debe ser exacto.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Al ingresar verá el **Panel de Operario**, con el saludo "Bienvenido, [su usuario]" y sus órdenes de producción activas.

## 3. Su panel principal

El panel tiene dos partes:

1. **Sus órdenes activas** — una tarjeta por cada Orden de Producción (OP) asignada a su máquina y turno. Solo se muestran las que están **En Proceso**; si no tiene ninguna, el panel lo indica y sugiere avisar al Jefe de Área.
2. **Últimos Ingresos** — una tabla con los últimos 10 registros realizados por el propio usuario, para revisarlos o corregirlos rápidamente.

Cada tarjeta de orden muestra:
- Producto y código de la OP.
- Fórmula asignada.
- Meta en Kg y una barra de **Avance** con lo ya **Producido** y lo **Pendiente**.
- Un aviso amarillo si está por completarse la meta (≥90%), y uno verde si ya se alcanzó.
- Dos botones: **Avance** (registrar producción) y **Transformación** (ver/registrar el flujo de máquina a máquina).

## 4. Registrar producción (botón "Avance")

1. En la tarjeta de la orden correspondiente, haga clic en **Avance**.
2. Se abre el formulario **Registrar Producción**:
   - **Peso Neto (Kg)** — obligatorio. Es el dato más importante: se recomienda revisar la balanza antes de ingresarlo.
   - **Unidades (Bobinas/Conos)** — si no se conoce el número exacto, puede dejarse en 1.
   - **Desperdicio (Kg)** — opcional. Si hubo merma, indíquela y seleccione el **Motivo**: Falla Técnica/Máquina, Calidad de Hilo/Material, Arranque/Setup, Corte/Empalme, u Otro.
   - Si la orden usa una mezcla de varios lotes de entrada, el formulario solicitará el **ID del lote de origen** y la **cantidad (kg)** consumida de cada uno — de no contar con el ID, puede solicitarlo al Jefe de Área.
3. El sistema no permite registrar una merma mayor a lo que falta por producir en la orden — si aparece ese aviso, se debe revisar el número ingresado.
4. Haga clic en **Confirmar Registro**.

## 5. Registrar una transformación (botón "Transformación")

Se utiliza cuando el producto cambia de una máquina a otra dentro del mismo proceso (por ejemplo, de una etapa a la siguiente).

1. Haga clic en **Transformación** en la tarjeta de la orden.
2. Se abre **Flujo de Producción**: allí se registra el producto de salida, la máquina, el peso de entrada/salida y observaciones. El sistema calcula la merma automáticamente.
3. En la misma ventana puede revisarse el **árbol completo de transformaciones** de esa orden (todas las etapas anteriores y la merma acumulada).

Solo pueden registrarse transformaciones en órdenes del área y sede del propio usuario.

## 6. Corregir o eliminar un registro ya hecho

En la tabla **Últimos Ingresos**:

- **Editar** (ícono de lápiz): permite corregir Peso Neto, Unidades o Merma directamente en la fila. Se confirma con el ícono de check ✓ o se cancela con la ✗.
- **Eliminar** (ícono de basura): abre una confirmación que advierte que esta acción **revertirá automáticamente**:
  - el peso producido que se había sumado al stock,
  - la materia prima que se había descontado,
  - los químicos consumidos.
  Debe escribirse una **Justificación** (ej. "Error de registro", "lote duplicado") — sin ella el sistema no permite continuar. Esta acción no se puede deshacer, por lo que se recomienda usarla solo cuando el registro esté realmente incorrecto.

## 7. Preguntas frecuentes

**No aparece ninguna orden asignada.** Comuníquese con su Jefe de Área — es quien asigna las órdenes a máquina y operario.

**Se cometió un error al escribir el peso hace un momento.** Si el lote sigue en la lista de "Últimos Ingresos", puede corregirse con el ícono de editar. Si ya no aparece allí, solicite al Jefe de Área que lo revise (puede reetiquetarlo).

**El sistema rechaza la merma ingresada.** Verifique que el número no sea mayor a lo que le falta a la orden por completarse.
