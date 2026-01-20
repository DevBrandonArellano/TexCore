# Diagrama de Casos de Uso - TexCore

```mermaid
usecaseDiagram
    actor "Administrador (Sistemas)" as Admin
    actor "Operario Producción" as Operario
    actor "Gerente / Supervisor" as Gerente
    actor "Bodeguero" as Bodeguero
    actor "Vendedor" as Vendedor

    package "Gestión de Usuarios y Configuración" {
        usecase "Gestionar Usuarios y Roles" as UC1
        usecase "Configurar Sedes y Áreas" as UC2
        usecase "Gestionar Catálogo de Productos" as UC3
    }

    package "Producción" {
        usecase "Crear Orden de Producción" as UC4
        usecase "Registrar Lote de Producción" as UC5
        usecase "Visualizar Estado de Órdenes" as UC6
        usecase "Gestionar Fórmulas" as UC7
    }

    package "Inventario y Bodega" {
        usecase "Registrar Ingreso de Material (Batch)" as UC8
        usecase "Realizar Transferencias entre Bodegas" as UC9
        usecase "Consultar Kardex/Movimientos" as UC10
        usecase "Ajustar Inventario" as UC11
    }

    package "Ventas y Despacho" {
        usecase "Registrar Pedido de Venta" as UC12
        usecase "Gestionar Clientes" as UC13
        usecase "Despachar y Facturar Pedido" as UC14
    }

    Admin --> UC1
    Admin --> UC2
    Admin --> UC3
    Admin --> UC7

    Gerente --> UC3
    Gerente --> UC4
    Gerente --> UC6
    Gerente --> UC10

    Operario --> UC5
    Operario --> UC6

    Bodeguero --> UC8
    Bodeguero --> UC9
    Bodeguero --> UC10
    Bodeguero --> UC11
    Bodeguero --> UC14

    Vendedor --> UC12
    Vendedor --> UC13
    Vendedor --> UC6
```
