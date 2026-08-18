---
description: Gestión global de infraestructura, usuarios, RBAC, catálogos e inventarios globales.
---

1. **Gestión de Infraestructura Global**: Configurar Sedes (`ManageSedes.tsx`), Áreas (`ManageAreas.tsx`) y Bodegas (`ManageBodegas.tsx`) del sistema.
2. **Gestión de Usuarios y RBAC**: Crear usuarios y asignar roles de los 11 grupos del sistema (`admin_sistemas`, `admin_sede`, `jefe_planta`, `jefe_area`, `operario`, `tintorero`, `empaquetado`, `despacho`, `bodeguero`, `vendedor`, `ejecutivo`) en `ManageUsers.tsx`.
3. **Maestro de Productos**: Administrar el catálogo de productos (hilos, telas con precisión métrica `DECIMAL(12,4)`, insumos químicos) y sus existencias mínimas (`ManageProductos.tsx`).
4. **Fórmulas e Insumos Industriales**: Administrar el catálogo de fórmulas de color (`ManageFormulas.tsx`), químicos (`ManageQuimicos.tsx`), proveedores (`ManageProveedores.tsx`) y clientes (`ManageClientes.tsx`).
5. **Dashboard Global de Inventario y Auditoría**: Monitorear existencias globales (`InventoryDashboard.tsx`), registro unificado de auditoría (`AuditLogViewer.tsx`) y la vista del grafo topológico de transformaciones (`TransformationView.tsx`).

