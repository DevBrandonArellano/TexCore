# TexCore - Credenciales y Guía de Uso

## 🔐 Credenciales de Acceso

### Usuarios de Demostración

| Rol | Usuario | Contraseña | Sede Asignada |
|-----|---------|------------|---------------|
| **Operario** | `operario1` | `password` | Sede Norte |
| **Jefe de Área** | `jefe_area1` | `password` | Sede Norte |
| **Jefe de Planta** | `jefe_planta1` | `password` | Sede Norte |
| **Admin de Sede** | `admin_sede1` | `password` | Sede Norte |
| **Ejecutivo** | `ejecutivo1` | `password` | Todas las sedes |
| **Admin de Sistemas** | `admin` | `admin` | Todas las sedes |

---

## ✨ Nuevas Funcionalidades

### 1. Botón de Cerrar Sesión
- **Ubicación**: Esquina superior derecha del header
- **Cómo usar**: Haz clic en tu avatar → "Cerrar Sesión"
- El botón está disponible en todos los roles

### 2. Sidebar de Sedes (Admin de Sistemas)
- **Ubicación**: Panel izquierdo del dashboard de Admin de Sistemas
- **Funcionalidad**:
  - Selecciona cualquier sede para ver sus datos específicos
  - Muestra estadísticas en tiempo real: Áreas, Usuarios, Bodegas, Órdenes
  - Indica el estado de cada sede (Activo/Inactivo)

---

## 📊 Módulos del Sistema

### Módulo 1: Usuarios y Perfiles
- Gestión de usuarios del sistema
- Asignación de roles y permisos
- Vinculación con sedes y áreas

### Módulo 2: Catálogos y Bodegas
- **Productos**: Hilos, Telas y Subproductos
  - Ejemplo: CASIMIR BQ (Código: 1000014)
- **Químicos**: Insumos para tintorería
  - Ejemplo: ACIDO CITRICO (Código: 8100000001)
- **Bodegas**: Almacenes por sede
  - Bodega Producto Terminado
  - Bodega Residuos
  - Bodega Químicos
  - Bodega Materia Prima
- **Inventario**: Control de stock por bodega y lote

### Módulo 3: Producción
- **Órdenes de Producción**: Gestión de órdenes de tintorería
  - Ejemplo: Orden 21715T - CASIMIR BQ
- **Lotes de Producción (Baños)**: Control de lotes producidos
  - Ejemplo: Lote 21680H-18
  - Registro de operario, máquina, turno, horarios
- **Fórmulas de Color**: Catálogo de recetas
  - Ejemplo: 22191T - MANCHESTER AZUL
- **Detalle de Fórmulas**: Químicos y cantidades por fórmula

### Módulo 4: Ventas y Clientes
- **Clientes**: Base de datos de clientes
  - RUC/Cédula
  - Razón Social
  - Nivel de precio (Mayorista/Normal)
- **Pedidos de Venta (Packing List)**: Gestión de pedidos
  - Guía de remisión
  - Estados: Pendiente, Despachado, Facturado
- **Detalle de Pedidos**: Productos, cantidades, precios

---

## 🎯 Navegación por Rol

### Admin de Sistemas
**Acceso a 4 secciones principales:**

1. **Resumen**
   - Estadísticas de la sede seleccionada
   - Vista general de áreas y bodegas
   - Contadores de usuarios y pedidos

2. **Producción**
   - Órdenes de producción activas
   - Fórmulas de color disponibles
   - Lotes producidos con detalles

3. **Inventario**
   - Catálogo de productos (hilos, telas, subproductos)
   - Catálogo de químicos
   - Stock actual por bodega

4. **Gestión**
   - Gestión de Usuarios
   - Gestión de Sedes
   - Gestión de Áreas

---

## 📍 Sedes Disponibles

### Sede Norte
- **Ubicación**: Ciudad de México
- **Estado**: Activo
- **Áreas**: Producción A, Producción B, Almacén, Control de Calidad
- **Bodegas**: 4

### Sede Sur
- **Ubicación**: Guadalajara
- **Estado**: Activo
- **Áreas**: Producción A, Producción B
- **Bodegas**: 2

### Sede Centro
- **Ubicación**: Monterrey
- **Estado**: Activo
- **Áreas**: Ninguna
- **Bodegas**: Ninguna

---

## 💡 Datos de Ejemplo

### Productos
- **1000014** - CASIMIR BQ (Tela, Metros)
- **1000025** - HILO POLIESTER 40/2 (Hilo, Kg)
- **1000036** - TELA JERSEY COTTON (Tela, Metros)
- **1000047** - RESIDUO TEXTIL (Subproducto, Kg)

### Químicos
- **8100000001** - ACIDO CITRICO
- **8100000002** - SODA CAUSTICA
- **8100000003** - PERÓXIDO DE HIDRÓGENO
- **8100000004** - DISPERSANTE TEXTIL

### Órdenes de Producción
- **21715T** - CASIMIR BQ (500 Kg) - En Proceso
- **21716T** - TELA JERSEY COTTON (300 Kg) - Pendiente
- **21717T** - CASIMIR BQ (450 Kg) - Finalizada

### Clientes
- **TEXTILES DEL NORTE S.A.** (RUC: 1792345678001) - Mayorista
- **CONFECCIONES ECUATEX** (RUC: 0992345678001) - Mayorista
- **MARÍA LÓPEZ** (Cédula: 1023456789) - Normal

---

## 🔄 Próximos Pasos Sugeridos

1. **Conectar con Supabase** para persistencia real de datos
2. **Implementar reportes** de producción y ventas
3. **Añadir notificaciones** en tiempo real
4. **Dashboard de métricas avanzadas** con gráficos interactivos
5. **Sistema de permisos granulares** por funcionalidad

---

## 📝 Notas Técnicas

- **Frontend**: React + TypeScript
- **Estilos**: Tailwind CSS + Shadcn/UI
- **Gráficos**: Recharts
- **Autenticación**: Mock data (localStorage)
- **Estado**: React Hooks (useState, useContext)

---

**TexCore v1.0** - Sistema de Gestión Textil Integral
