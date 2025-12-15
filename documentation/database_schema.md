# Esquema de la Base de Datos - TexCore

Este documento detalla la estructura de las tablas de la base de datos del proyecto TexCore, basado en los modelos de Django. Cada modelo corresponde a una tabla en la base de datos.

---

## Aplicación: `gestion`

Contiene los modelos principales para la gestión de la empresa, usuarios, y el flujo de producción y ventas.

### `gestion_sede` (Modelo: `Sede`)
Almacena las diferentes sedes o sucursales de la empresa.

| Nombre del Campo | Tipo de Dato       | PK/FK  | Descripción                               |
|------------------|--------------------|--------|-------------------------------------------|
| `id`             | AutoField (Integer)| **PK** | Identificador único de la sede.           |
| `nombre`         | CharField(100)     | -      | Nombre único de la sede.                  |
| `location`       | CharField(100)     | -      | Ubicación física de la sede.              |
| `status`         | CharField(10)      | -      | Estado de la sede ('activo', 'inactivo'). |

### `gestion_area` (Modelo: `Area`)
Define las áreas funcionales dentro de cada sede.

| Nombre del Campo | Tipo de Dato       | PK/FK                | Descripción                               |
|------------------|--------------------|----------------------|-------------------------------------------|
| `id`             | AutoField (Integer)| **PK**               | Identificador único del área.             |
| `nombre`         | CharField(100)     | -                    | Nombre del área (ej. "Tinturado").        |
| `sede_id`        | ForeignKey         | **FK** a `gestion_sede` | Sede a la que pertenece el área.          |

### `gestion_customuser` (Modelo: `CustomUser`)
Modelo de usuario extendido de Django. Almacena todos los usuarios del sistema.

| Nombre del Campo | Tipo de Dato       | PK/FK                | Descripción                               |
|------------------|--------------------|----------------------|-------------------------------------------|
| `id`             | AutoField (Integer)| **PK**               | Identificador único del usuario.          |
| `username`       | CharField          | -                    | Nombre de usuario para el login.          |
| `password`       | CharField          | -                    | Contraseña hasheada.                      |
| `first_name`     | CharField          | -                    | Nombre del usuario.                       |
| `last_name`      | CharField          | -                    | Apellido del usuario.                     |
| `email`          | EmailField         | -                    | Correo electrónico.                       |
| `is_staff`       | BooleanField       | -                    | Define si puede acceder al admin de Django. |
| `is_active`      | BooleanField       | -                    | Define si el usuario está activo.         |
| `date_joined`    | DateTimeField      | -                    | Fecha de creación del usuario.            |
| `sede_id`        | ForeignKey         | **FK** a `gestion_sede` | Sede a la que está asociado el usuario.   |
| `area_id`        | ForeignKey         | **FK** a `gestion_area` | Área a la que está asociado el usuario.   |
| `date_of_birth`  | DateField          | -                    | Fecha de nacimiento (opcional).           |

*Nota: También tiene relaciones ManyToMany con `Group` y `Permission` de Django.*

### `gestion_producto` (Modelo: `Producto`)
Catálogo maestro de todos los artículos que se pueden inventariar, incluyendo materia prima, productos semiterminados, productos finales y químicos.

| Nombre del Campo  | Tipo de Dato        | PK/FK  | Descripción                                       |
|-------------------|---------------------|--------|---------------------------------------------------|
| `id`              | AutoField (Integer) | **PK** | Identificador único del producto.                 |
| `codigo`          | CharField(100)      | -      | Código único para el producto.                    |
| `descripcion`     | CharField(255)      | -      | Nombre o descripción del producto.                |
| `tipo`            | CharField(20)       | -      | Tipo: 'hilo', 'tela', 'subproducto', 'quimico'.   |
| `unidad_medida`   | CharField(20)       | -      | Unidad de medida: 'kg', 'metros', 'unidades'.     |
| `stock_minimo`    | DecimalField        | -      | Nivel de stock mínimo para generar alertas.       |

### `gestion_bodega` (Modelo: `Bodega`)
Almacena las bodegas o almacenes de la empresa, asociadas a una sede.

| Nombre del Campo | Tipo de Dato       | PK/FK                | Descripción                               |
|------------------|--------------------|----------------------|-------------------------------------------|
| `id`             | AutoField (Integer)| **PK**               | Identificador único de la bodega.         |
| `nombre`         | CharField(100)     | -                    | Nombre de la bodega.                      |
| `sede_id`        | ForeignKey         | **FK** a `gestion_sede` | Sede a la que pertenece la bodega.        |

### `gestion_formulacolor` (Modelo: `FormulaColor`)
Define las recetas para los colores, compuestas por productos de tipo 'quimico'.

| Nombre del Campo | Tipo de Dato       | PK/FK  | Descripción                               |
|------------------|--------------------|--------|-------------------------------------------|
| `id`             | AutoField (Integer)| **PK** | Identificador único de la fórmula.        |
| `codigo`         | CharField(100)     | -      | Código único para la fórmula.             |
| `nombre_color`   | CharField(100)     | -      | Nombre del color resultante.              |
| `description`    | TextField          | -      | Descripción adicional.                    |
| `productos`      | ManyToManyField    | **FK** a `gestion_producto` | Relación con los químicos que la componen. |

### `gestion_detalleformula` (Modelo: `DetalleFormula`)
Tabla intermedia que define la cantidad de cada químico en una `FormulaColor`.

| Nombre del Campo    | Tipo de Dato        | PK/FK                       | Descripción                                     |
|---------------------|---------------------|-----------------------------|-------------------------------------------------|
| `id`                | AutoField (Integer) | **PK**                      | Identificador único del detalle.                |
| `formula_color_id`  | ForeignKey          | **FK** a `gestion_formulacolor`| Fórmula a la que pertenece este detalle.     |
| `producto_id`       | ForeignKey          | **FK** a `gestion_producto`   | Químico (producto de tipo 'quimico') usado.    |
| `gramos_por_kilo`   | DecimalField        | -                           | Cantidad en gramos requerida por cada kg de producto a teñir. |

### `gestion_ordenproduccion` (Modelo: `OrdenProduccion`)
Planifica un trabajo de producción.

| Nombre del Campo        | Tipo de Dato        | PK/FK                        | Descripción                                                  |
|-------------------------|---------------------|------------------------------|--------------------------------------------------------------|
| `id`                    | AutoField (Integer) | **PK**                       | Identificador único de la orden.                             |
| `codigo`                | CharField(100)      | -                            | Código único de la orden.                                    |
| `producto_id`           | ForeignKey          | **FK** a `gestion_producto`    | Producto principal a consumir o transformar (ej. Hilo Crudo).|
| `formula_color_id`      | ForeignKey          | **FK** a `gestion_formulacolor`| Fórmula de color a aplicar (si es una orden de tinturado). |
| `bodega_id`             | ForeignKey          | **FK** a `gestion_bodega`      | Bodega donde se realiza la producción y se consumen insumos. |
| `peso_neto_requerido`   | DecimalField        | -                            | Cantidad total a producir.                                   |
| `estado`                | CharField(20)       | -                            | Estado: 'pendiente', 'en_proceso', 'finalizada'.             |
| `sede_id`               | ForeignKey          | **FK** a `gestion_sede`        | Sede donde se ejecuta la orden.                              |

### `gestion_loteproduccion` (Modelo: `LoteProduccion`)
Registra el resultado tangible de una `OrdenProduccion`.

| Nombre del Campo      | Tipo de Dato        | PK/FK                             | Descripción                                     |
|-----------------------|---------------------|-----------------------------------|-------------------------------------------------|
| `id`                  | AutoField (Integer) | **PK**                            | Identificador único del lote.                   |
| `orden_produccion_id` | ForeignKey          | **FK** a `gestion_ordenproduccion`| Orden de producción a la que pertenece.         |
| `codigo_lote`         | CharField(100)      | -                                 | Código único para este lote específico.         |
| `peso_neto_producido` | DecimalField        | -                                 | Cantidad real producida en este lote.           |
| `operario_id`         | ForeignKey          | **FK** a `gestion_customuser`     | Usuario que registró el lote.                   |
| `maquina`             | CharField(100)      | -                                 | Máquina utilizada.                              |
| `turno`               | CharField(50)       | -                                 | Turno de producción.                            |
| `hora_inicio`         | DateTimeField       | -                                 | Fecha y hora de inicio del lote.                |
| `hora_final`          | DateTimeField       | -                                 | Fecha y hora de finalización del lote.          |

---

## Aplicación: `inventory`

Contiene los modelos para gestionar el stock y los movimientos de inventario.

### `inventory_stockbodega` (Modelo: `StockBodega`)
Representa el saldo o stock actual de un producto en una bodega específica. Es la "foto" actual del inventario.

| Nombre del Campo | Tipo de Dato        | PK/FK                         | Descripción                                     |
|------------------|---------------------|-------------------------------|-------------------------------------------------|
| `id`             | AutoField (Integer) | **PK**                        | Identificador único del registro de stock.      |
| `bodega_id`      | ForeignKey          | **FK** a `gestion_bodega`     | Bodega donde se encuentra el stock.             |
| `producto_id`    | ForeignKey          | **FK** a `gestion_producto`   | Producto inventariado.                          |
| `lote_id`        | ForeignKey          | **FK** a `gestion_loteproduccion`| Lote de producción al que pertenece el stock (si aplica). |
| `cantidad`       | DecimalField        | -                             | Cantidad actual disponible.                     |

### `inventory_movimientoinventario` (Modelo: `MovimientoInventario`)
Registra cada transacción que afecta al inventario (entradas, salidas, transferencias). Es la fuente de verdad para la trazabilidad (Kardex).

| Nombre del Campo   | Tipo de Dato        | PK/FK                         | Descripción                                                  |
|--------------------|---------------------|-------------------------------|--------------------------------------------------------------|
| `id`               | AutoField (Integer) | **PK**                        | Identificador único del movimiento.                          |
| `fecha`            | DateTimeField       | -                             | Fecha y hora en que se registró el movimiento.               |
| `tipo_movimiento`  | CharField(20)       | -                             | Tipo: 'COMPRA', 'PRODUCCION', 'TRANSFERENCIA', 'CONSUMO', etc.|
| `producto_id`      | ForeignKey          | **FK** a `gestion_producto`   | Producto que se está moviendo.                               |
| `lote_id`          | ForeignKey          | **FK** a `gestion_loteproduccion`| Lote asociado al movimiento (si aplica).                   |
| `bodega_origen_id` | ForeignKey          | **FK** a `gestion_bodega`     | Bodega de donde sale el producto (para transferencias, consumos). |
| `bodega_destino_id`| ForeignKey          | **FK** a `gestion_bodega`     | Bodega a la que entra el producto (para compras, producción).   |
| `cantidad`         | DecimalField        | -                             | Cantidad de producto movida.                                 |
| `documento_ref`    | CharField(100)      | -                             | Referencia a un documento externo (ej. 'OP-2025-001').      |
| `usuario_id`       | ForeignKey          | **FK** a `gestion_customuser` | Usuario que realizó la operación.                            |
| `saldo_resultante` | DecimalField        | -                             | Campo denormalizado para facilitar cálculos de Kardex.       |