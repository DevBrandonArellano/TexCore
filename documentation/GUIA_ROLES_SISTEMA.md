# 👥 Manual de Roles y Permisos - TexCore

Este documento detalla las funciones, responsabilidades y capacidades de cada tipo de usuario dentro de la plataforma TexCore. El sistema utiliza un control de acceso basado en roles (RBAC) para garantizar la seguridad y la integridad de los datos.

---

## 📋 Resumen de Roles

| Rol | Función Principal | Ámbito de Acción |
| :--- | :--- | :--- |
| **Operario** | Registro de producción | Maquinaria y Lotes |
| **Bodeguero** | Control de inventario | Bodegas y Movimientos |
| **Vendedor** | Gestión Comercial | Clientes, Ventas y Cobros |
| **Jefe de Planta** | Planificación de Producción | Órdenes de Producción y Fórmulas |
| **Jefe de Área** | Supervisión de Sección | Área específica y Maquinaria |
| **Ejecutivo** | Análisis y Reportes | Consultas de Solo Lectura |
| **Admin de Sede** | Administración Local | Gestión total de la sede asignada |
| **Admin de Sistemas** | Administración Global | Configuración de plataforma y parámetros |

---

## 🛠 Detalle por Rol

### 1. Operario
**Función:** Es el encargado de reportar la actividad física en la planta. Su interacción principal ocurre en las estaciones de trabajo de las máquinas.
*   **¿Qué puede hacer?**
    *   Registrar el inicio y fin de la producción de un lote.
    *   Ingresar el peso neto producido, tara y bultos.
    *   Vincular la producción a una máquina y turno específico.
    *   Generar etiquetas ZPL/QR para la trazabilidad de los bultos producidos.
    *   Consultar las órdenes de producción asignadas para su ejecución.

### 2. Bodeguero
**Función:** Responsable de la custodia y el movimiento físico de la mercancía (materia prima, insumos y producto terminado).
*   **¿Qué puede hacer?**
    *   Visualizar el stock en tiempo real por bodega y lote.
    *   Registrar movimientos de inventario (Entradas, Salidas, Ajustes).
    *   Gestionar la recepción de lotes provenientes de producción.
    *   Realizar transferencias entre bodegas.
    *   Consultar el historial (Kardex) de movimientos para auditoría.

### 3. Vendedor (Ejecutivo de Ventas)
**Función:** Gestiona la relación comercial con los clientes y asegura el flujo de ingresos de la empresa.
*   **¿Qué puede hacer?**
    *   Crear y actualizar la información de sus clientes asignados.
    *   Generar **Pedidos de Venta** (Notas de Venta).
    *   Registrar **Pagos y Cobros** (Efectivo, Transferencia, Cheque).
    *   Consultar el estado de cuenta y límite de crédito de sus clientes.
    *   Descargar documentos PDF de las ventas realizadas.
    *   *Restricción:* No puede vender por debajo del "Precio Base" ni exceder límites de crédito sin autorización.

### 4. Jefe de Planta
**Función:** Director de la orquesta de producción. Planifica qué se produce, con qué recursos y bajo qué especificaciones.
*   **¿Qué puede hacer?**
    *   Crear y gestionar **Órdenes de Producción (OP)**.
    *   Definir **Fórmulas de Color** (Recetas químicas para tintorería).
    *   Gestionar el catálogo de **Maquinaria** (Estados: Operativa, Mantenimiento).
    *   Supervisar el avance de las órdenes en tiempo real.
    *   Gestionar el catálogo de productos y sus costos base.

### 5. Jefe de Área
**Función:** Supervisa una sección específica (ej: Tintorería, Tejeduría, Hilatura).
*   **¿Qué puede hacer?**
    *   Gestionar operarios asignados a su área.
    *   Controlar el estado y eficiencia de las máquinas de su sección.
    *   Validar la producción reportada por los operarios bajo su mando.
    *   Consultar stock de materiales necesarios para su área.

### 6. Ejecutivo
**Función:** Perfil gerencial o administrativo que requiere información para la toma de decisiones sin intervenir en la operación diaria.
*   **¿Qué puede hacer?**
    *   Visualizar KPIs de producción y ventas.
    *   Consultar stock consolidado de todas las bodegas.
    *   Ver estados de cuenta de clientes.
    *   Auditar órdenes de producción y pedidos de venta.
    *   *Restricción:* Acceso de **solo lectura**. No puede crear ni modificar registros.

### 7. Administrador de Sede
**Función:** Responsable operativo de una sucursal o sede física completa.
*   **¿Qué puede hacer?**
    *   Gestión total de usuarios, áreas, inventarios y ventas **dentro de su sede**.
    *   Configurar parámetros locales.
    *   Corregir errores en registros de producción o ventas de su jurisdicción.
    *   Auditoría de todos los movimientos de la sede.

### 8. Administrador de Sistemas
**Función:** Máximo nivel de acceso para soporte técnico y configuración global.
*   **¿Qué puede hacer?**
    *   Crear y gestionar **Sedes** nuevas.
    *   Configurar grupos de permisos y roles.
    *   Acceso a logs de auditoría global.
    *   Gestión de parámetros críticos de la base de datos.

---

## 🔒 Reglas de Seguridad Transversales

1.  **Aislamiento de Sede:** Los usuarios (excepto Admin de Sistemas) solo pueden interactuar con datos de la sede a la que pertenecen.
2.  **Seguridad por Cartera:** Los vendedores solo pueden visualizar clientes y pedidos que tengan asignados.
3.  **Trazabilidad:** Cada acción de creación o modificación guarda el usuario responsable y la marca de tiempo (Timestamp).
4.  **Integridad de Stock:** Los movimientos que resulten en stock negativo están bloqueados por regla de negocio.
