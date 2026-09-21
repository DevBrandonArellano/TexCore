# Plan de Implementación: Reemplazo de 'Producto Intermedio' por 'Colorantes' en Catálogo

- **Especificación:** `docs/superpowers/specs/2026-09-21-tipo-producto-colorante-design.md`
- **Estado:** Completado

---

## Tareas

### FASE 1: Backend Django (Modelo, Migración y Pruebas Unitarias)
- [x] **Tarea 1.1:** Escribir prueba unitaria backend en `gestion/tests/test_catalogo_producto_colorante.py` (ISTQB CTFL v4.0).
- [x] **Tarea 1.2:** Modificar `gestion/models/catalogo.py` para reemplazar `('producto_intermedio', 'Producto Intermedio')` por `('colorante', 'Colorantes')` en `Producto.TIPO_CHOICES`.
- [x] **Tarea 1.3:** Crear archivo de migración Django `gestion/migrations/0013_replace_producto_intermedio_with_colorante.py` con migración de datos y alteración de campo.

### FASE 2: Frontend React / TypeScript (Tipos, Formulario, Filtro y Badges)
- [x] **Tarea 2.1:** Actualizar `frontend/src/lib/types.ts` para incluir `'colorante'` en la unión de tipos de `Producto.tipo`.
- [x] **Tarea 2.2:** Modificar `frontend/src/components/admin-sistemas/ManageProductos.tsx`:
  - Agregar opción `"colorante"` con etiqueta `"Colorantes"` en el selector del formulario de creación y edición.
  - Agregar opción `"colorante"` con etiqueta `"Colorantes"` en el selector de filtro por tipo.
  - Actualizar el badge de la tabla para representar `'colorante'` con estilo ámbar y texto `"Colorantes"`.
- [x] **Tarea 2.3:** Agregar pruebas unitarias en `frontend/src/components/admin-sistemas/ManageProductos.test.tsx` verificando el renderizado del badge `"Colorantes"` y el filtrado por este tipo.

### FASE 3: Verificación y Calidad
- [x] **Tarea 3.1:** Ejecutar `npx tsc --noEmit` en `frontend/` y validar 0 errores de compilación.
- [x] **Tarea 3.2:** Ejecutar suite de pruebas unitarias de frontend con Vitest (`ManageProductos.test.tsx` y `BodegueroDashboard.test.tsx`).
- [x] **Tarea 3.3:** Documentar cambios en `CHANGELOG.md` respetando estándares de TexCore.
