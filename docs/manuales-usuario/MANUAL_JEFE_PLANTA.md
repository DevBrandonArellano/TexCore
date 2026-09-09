# Manual de Usuario — Jefe de Planta

## 1. ¿Qué hace usted en TexCore?

Usted es el planificador central de producción: **es el único rol que crea Órdenes de Producción (OP)** y las asigna a una sede. El Jefe de Área, después, asigna esa orden a una máquina y un operario específicos — pero no crea órdenes nuevas.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Jefe de Planta**, centrado en la **Gestión de Órdenes de Producción**: una tabla con buscador (por código o producto) y filtros por estado y máquina.

## 3. Crear una nueva Orden de Producción

1. Haga clic en **Nueva Orden de Producción**.
2. Complete el formulario:
   - **Código** (obligatorio).
   - **Peso Neto Requerido (Kg)** (obligatorio) — la meta de producción.
   - **Producto Entrada** (obligatorio) y su **Bodega Entrada**.
   - **Producto Salida** (obligatorio) y su **Bodega Salida**.
   - **Área Responsable** (obligatorio) — a qué área de la sede se asigna.
   - **Prioridad** (obligatorio).
   - **Fecha Inicio** y **Fecha Fin** planificadas.
   - **Observaciones** (libre).
   - Si el producto requiere tintura, también deben seleccionarse la **Fórmula de color** y la **Bodega de Químicos**: al guardar, el sistema **descuenta automáticamente** los químicos necesarios de esa bodega según la fórmula.
3. Guarde la orden. Queda visible para que el Jefe de Área de esa área pueda asignarla a máquina y operario.

## 4. Verificar materiales antes de asignar

Antes de confirmar una orden, puede revisarse el detalle de **Requisitos de Materiales** para comprobar que hay disponibilidad suficiente de insumos antes de comprometer la planificación.

## 5. Editar o eliminar una orden

- **Editar**: si la orden ya tiene químicos descontados (por tener fórmula asignada), cambiar el **peso** o la **fórmula** solicitará una **justificación obligatoria** — el sistema revierte automáticamente el descuento anterior y aplica el nuevo cálculo.
- **Eliminar**: también exige justificación si ya se habían descontado químicos; al confirmar, el sistema revierte automáticamente el stock consumido.

## 6. Consultar trazabilidad (solo lectura)

Desde el detalle de cualquier orden puede verse el **árbol completo de transformaciones** que ha tenido (todas las etapas registradas por Operarios/Jefes de Área) con la merma acumulada en porcentaje. El Jefe de Planta **no registra** transformaciones directamente — esa función corresponde a Operarios y Jefes de Área.

## 7. Registrar un lote directamente (excepcional)

De ser necesario registrar producción manualmente sobre una orden (por ejemplo, para corregir una situación en planta), puede abrirse el diálogo de **Registrar Lote** desde el detalle de la orden — el mismo formulario que usa un Operario.

## 8. Preguntas frecuentes

**¿Por qué el Jefe de Área no puede crear órdenes?** Es una regla de negocio: la planificación (crear la OP) corresponde al Jefe de Planta; la ejecución (asignar máquina/operario y producir) corresponde al Jefe de Área.

**¿Por qué no se puede cambiar el peso de una orden sin dar un motivo?** Porque ya se descontaron químicos de bodega con el cálculo anterior — el motivo queda en auditoría y el sistema reajusta el inventario automáticamente.

**Se necesita ver el avance real, no solo lo planificado.** Debe usarse la vista de detalle de la orden (trazabilidad) para ver lo producido y la merma acumulada en tiempo real.
