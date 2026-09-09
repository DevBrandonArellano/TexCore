# Manuales de Usuario — TexCore

Guías paso a paso para cada rol del sistema, pensadas para entregarse directamente a los usuarios finales (no requieren conocimientos técnicos). Cada manual describe **su propio panel**: qué pestañas verá, qué botones puede usar y qué hacer ante los errores más comunes.

Si busca la referencia técnica de permisos (para el equipo de desarrollo/QA), consulte [Roles y Permisos](../historias-usuarios/ROLES_Y_PERMISOS.md).

---

## Cómo ingresar al sistema (todos los roles)

1. Abra TexCore en su navegador, con la dirección que le indicó el Administrador del Sistema.
2. Ingrese su **Usuario** y **Contraseña** (se los entrega el Administrador de Sistemas o de Sede al crear su cuenta).
3. Haga clic en **Ingresar**.
4. Al ingresar, el sistema abre directamente su panel según su rol — no hay menús que navegar, cada usuario ve solo lo que le corresponde.
5. Para salir, haga clic en **Cerrar Sesión** (botón arriba a la derecha, junto a su nombre) o en el ícono de su usuario → **Cerrar Sesión**.

Si olvidó su contraseña o su cuenta no funciona, comuníquese con el **Administrador de Sistemas** — solo esa persona puede crear o restablecer cuentas.

---

## Manuales por rol

| Manual | Rol | Función principal |
|---|---|---|
| [Operario](MANUAL_OPERARIO.md) | Operario | Registrar producción y transformaciones en máquina |
| [Empaquetado](MANUAL_EMPAQUETADO.md) | Empaquetado | Pesar, etiquetar e imprimir bultos/cajas |
| [Despacho](MANUAL_DESPACHO.md) | Despacho | Escanear y confirmar la salida de pedidos |
| [Bodeguero](MANUAL_BODEGUERO.md) | Bodeguero | Controlar stock, transferencias y alertas |
| [Vendedor](MANUAL_VENDEDOR.md) | Vendedor | Clientes, pedidos de venta y cobros |
| [Jefe de Planta](MANUAL_JEFE_PLANTA.md) | Jefe de Planta | Crear y planificar Órdenes de Producción |
| [Jefe de Área](MANUAL_JEFE_AREA.md) | Jefe de Área | Supervisar máquinas, KPIs y calidad |
| [Tintorero](MANUAL_TINTORERO.md) | Tintorero | Fórmulas de color y stock de químicos |
| [Ejecutivo](MANUAL_EJECUTIVO.md) | Ejecutivo | Reportes gerenciales de solo lectura |
| [Administrador de Sede](MANUAL_ADMIN_SEDE.md) | Admin de Sede | Aprobaciones y auditoría de su sede |
| [Administrador de Sistemas](MANUAL_ADMIN_SISTEMAS.md) | Admin de Sistemas | Maestros globales, usuarios y roles |

---

## Reglas generales que aplican a todos los roles

- **Aislamiento por sede:** por lo general, el usuario solo verá datos de su propia sede (bodega, área, clientes). Si algo que esperaba ver no aparece, puede pertenecer a otra sede.
- **Justificación obligatoria:** toda acción que revierte o corrige algo ya registrado (eliminar un lote, revertir un abono, reetiquetar, ajustar inventario) solicitará un motivo. Es obligatorio y queda guardado de forma permanente para auditoría — se recomienda ser específico.
- **No hay stock negativo:** el sistema no permite retirar más mercancía de la que existe realmente en la bodega.
- **Todo queda registrado:** cada movimiento guarda quién lo realizó, cuándo y con qué documento de referencia. Esto es normal y forma parte del control de calidad del sistema, no una limitación.
