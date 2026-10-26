# Especificación de Diseño: Reemplazo de 'Producto Intermedio' por 'Colorantes' en Catálogo

- **Fecha:** 2026-09-21
- **Autor:** DevBrandonArellano / Antigravity
- **Estado:** Aprobado
- **Módulo:** Catálogo de Productos (`gestion`, `frontend`)

---

## 1. Contexto y Justificación

En la configuración inicial del motor MES se introdujo `'producto_intermedio'` en el catálogo. De acuerdo con las necesidades operativas de la planta textil, el catálogo de materias primas e insumos requiere tipificar específicamente los **Colorantes** utilizados en tintorería y acabados, reemplazando la opción *"Producto Intermedio"* por *"Colorantes"* tanto en el formulario de creación de productos (disponible para Administradores de Sistemas y Bodegueros) como en los filtros y badges de visualización.

---

## 2. Requerimientos Funcionales

1. **Creación de Productos:**
   - En el selector de `Tipo` de producto en el modal de creación/edición, la opción *"Producto Intermedio"* se reemplaza por la opción *"Colorantes"* (valor: `'colorante'`, etiqueta visible: `"Colorantes"`).
2. **Filtros de Catálogo:**
   - En el selector de filtro por tipo de producto, *"Producto Intermedio"* se sustituye por *"Colorantes"*.
3. **Visualización y Badges:**
   - En la tabla de productos, las filas con tipo `'colorante'` muestran una insignia (badge) distintiva (fondo ámbar/marrón textil `bg-amber-100 text-amber-800 border-amber-200`) con el texto `"Colorantes"`.
4. **Persistencia Backend y Migración:**
   - `Producto.TIPO_CHOICES` en Django incluye `('colorante', 'Colorantes')` en lugar de `('producto_intermedio', 'Producto Intermedio')`.
   - Se crea una migración de datos que convierte cualquier registro histórico con `tipo = 'producto_intermedio'` a `tipo = 'colorante'`, seguido de la actualización estructural (`AlterField`) de la columna `tipo`.

---

## 3. Modelo de Datos y Arquitectura

### 3.1 Backend (`gestion/models/catalogo.py`)

```python
class Producto(SedeResolvableMixin, AuditableModelMixin, models.Model):
    TIPO_CHOICES = [
        ('hilo', 'Hilo'),
        ('tela', 'Tela'),
        ('subproducto', 'Subproducto'),
        ('quimico', 'Químico'),
        ('insumo', 'Insumo'),
        ('materia_prima', 'Materia prima'),
        ('colorante', 'Colorantes'),
    ]
    ...
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
```

### 3.2 Migración Django (`gestion/migrations/0013_replace_producto_intermedio_with_colorante.py`)

1. `RunPython`: Función reversible para actualizar productos existentes:
   ```python
   def forward_func(apps, schema_editor):
       Producto = apps.get_model('gestion', 'Producto')
       Producto.objects.filter(tipo='producto_intermedio').update(tipo='colorante')

   def reverse_func(apps, schema_editor):
       Producto = apps.get_model('gestion', 'Producto')
       Producto.objects.filter(tipo='colorante').update(tipo='producto_intermedio')
   ```
2. `AlterField`: Modificación del campo `tipo` con los nuevos `choices`.

### 3.3 Frontend (`frontend/src/lib/types.ts` y `ManageProductos.tsx`)

- `types.ts`:
  ```typescript
  export interface Producto {
    id: number;
    codigo: string;
    descripcion: string;
    tipo: 'hilo' | 'tela' | 'subproducto' | 'quimico' | 'insumo' | 'materia_prima' | 'colorante' | 'merma' | 'producto_intermedio';
    ...
  }
  ```
- `ManageProductos.tsx`:
  - Formulario de creación: `<SelectItem value="colorante">Colorantes</SelectItem>`
  - Filtro por tipo: `<SelectItem value="colorante">Colorantes</SelectItem>`
  - Badge de tabla:
    ```tsx
    <Badge
      variant={producto.tipo === 'colorante' ? 'secondary' : 'outline'}
      className={producto.tipo === 'colorante' ? 'bg-amber-100 text-amber-800 border-amber-200' : ''}
    >
      {producto.tipo === 'colorante' ? 'Colorantes' : producto.tipo}
    </Badge>
    ```

---

## 4. Estrategia de Testing (ISTQB CTFL v4.0)

- **Backend (`gestion/tests/test_catalogo_producto_colorante.py`)**:
  - `test_producto_dado_tipo_colorante_cuando_se_crea_entonces_persiste_correctamente`
  - `test_producto_dado_tipo_colorante_cuando_se_consulta_por_tipo_entonces_filtra_correctamente`
- **Frontend (`frontend/src/components/admin-sistemas/ManageProductos.test.tsx`)**:
  - `test_producto_dado_tipo_colorante_cuando_se_renderiza_entonces_muestra_badge_colorantes`
  - `test_filtro_tipo_dado_opcion_colorantes_cuando_se_selecciona_entonces_filtra_productos_colorante`
- **Verificación Estática**:
  - `cd frontend && npx tsc --noEmit`
  - Vitest en `frontend`
