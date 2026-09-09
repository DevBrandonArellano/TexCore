# Manual de Usuario — Jefe de Área

## 1. ¿Qué hace usted en TexCore?

Usted supervisa la eficiencia y la calidad de una sección específica de producción: asigna las órdenes que crea el Jefe de Planta a máquina y operario, controla el estado de las máquinas de su área, registra paros y decide cuándo un lote no cumple la calidad esperada.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Control - Área de Producción**. A diferencia de otros roles, no está dividido en pestañas: todo se organiza en secciones dentro de la misma pantalla.

## 3. Indicadores de su área (KPIs)

En la parte superior se muestran las tarjetas de desempeño del área, calculadas con datos reales (no estimados):

- **Producción Total (Kg)**.
- **Rendimiento (Yield)** = peso neto producido / (peso neto + merma).
- **First Pass Yield (FPY)** = kg de primera calidad / kg total — mide cuánto sale bien a la primera.
- **Distribución por Calidad** (primera / segunda / saldo).
- **Tiempo Promedio** por lote.
- **OEE** (Disponibilidad × Rendimiento × Calidad), con el desglose de sus tres componentes. La Disponibilidad se calcula a partir de los paros de máquina registrados (vea la sección 5).

## 4. Asignar Órdenes de Producción

Solo pueden **asignarse** órdenes que el Jefe de Planta ya creó para el área — no es posible crear órdenes nuevas.

1. En el panel de órdenes disponibles para el área, elija la orden a asignar.
2. Seleccione la **máquina** y el **operario** que la van a ejecutar.
3. Confirme — la orden pasa a "En Proceso" para ese operario.

## 5. Gestionar máquinas y registrar paros

En **Gestión de Máquinas** pueden crearse/editarse máquinas del área y verse, en cada tarjeta, su badge de **OEE** individual.

**Registrar un paro (downtime):**
1. Haga clic en **Registrar Paro** sobre la máquina correspondiente.
2. Elija la **categoría** (una de las Seis Grandes Pérdidas): Avería, Setup, Microparo, Velocidad Reducida, Rechazo de Arranque, Defecto de Proceso, Falta de Material, Mantenimiento Planificado, u Otro.
3. Indique **inicio** y, si ya terminó, la **hora de fin** (puede dejarse vacío si el paro sigue en curso).
4. Marque la casilla **Planificado** si se trata de un paro programado (mantenimiento, cambio de turno) — los paros planificados **no penalizan** la Disponibilidad del OEE.
5. Agregue una descripción y guarde.

## 6. Gestionar Líneas de Producción

En **Líneas de Producción** pueden crearse, editarse o eliminarse líneas del área, asignando varias máquinas a cada una. Esto permite compartir máquinas rápidas entre distintas líneas sin duplicar la capacidad calculada del área.

## 7. Rechazar un lote

Si un lote no cumple calidad:

1. Debe ubicarse (en los lotes recientes o en el buscador) y seleccionarse **Rechazar**.
2. Escriba el **motivo obligatorio** — queda trazado para auditoría de calidad (ISO 9001).
3. Al confirmar, el sistema **revierte automáticamente** el stock, el consumo de mezcla y la merma que ese lote había generado.

## 8. Reetiquetar un lote

Como supervisor, es posible corregir el peso o reclasificar la calidad de un lote ya registrado:

1. En el **Buscador de Lotes**, ubique el lote y haga clic en **Reetiquetar**.
2. Corrija el peso y/o la calidad, escriba el motivo obligatorio y confirme.
3. Se anula la etiqueta anterior y se imprime una nueva versión; si cambió el peso, el stock se ajusta automáticamente. El código de lote y el QR de trazabilidad **nunca cambian**.

También es posible autorizar in situ un reetiquetado que un operario de Empaquetado inicie desde su propio panel: debe ingresarse el usuario y la contraseña del supervisor en el modal correspondiente, sin necesidad de cerrar la sesión activa de dicho operario.

## 9. Otras secciones de su panel

- **Alertas de Insumos**: avisos de químicos/hilos críticos para el área.
- **Movimientos de su Área** y **Lotes Recientes**: historial reciente de actividad.
- **Consumo de Mezcla**: seguimiento de los componentes usados en órdenes de mezcla.
- **Transformaciones y trazabilidad**: permite registrar y consultar la cadena de transformaciones máquina a máquina de las órdenes del área (igual que el Operario, pero con visión de toda el área).

## 10. Reglas que debe conocer

- Todo lo que se ve y se gestiona está limitado al **área y sede** del usuario.
- No es posible crear Órdenes de Producción — solo asignarlas.
- Rechazar y reetiquetar siempre exigen motivo obligatorio.

## 11. Preguntas frecuentes

**No aparece la opción de crear una orden nueva.** Es correcto: esa función es exclusiva del Jefe de Planta/Administrador. La función de este rol es asignar las órdenes ya existentes.

**El OEE se ve bajo aunque no hubo fallas grandes.** Debe revisarse que los paros planificados estén marcados como tales — si no lo están, penalizan la Disponibilidad aunque hayan sido programados.

**Un operario necesita reetiquetar un lote y el supervisor no está en su puesto.** Puede autorizarse a distancia si el supervisor está junto a la pantalla: el modal de reetiquetado solicita usuario y contraseña sin afectar la sesión del operario.
