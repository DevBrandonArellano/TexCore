# Especificación de Diseño: Sincronización Bidireccional Reactiva entre Productos y Químicos

- **Fecha:** 2026-09-21
- **Autor:** DevBrandonArellano / Antigravity
- **Estado:** Aprobado
- **Módulo:** Frontend (`catalogSync`, `BodegueroDashboard`, `useSedeSpecificData`)

---

## 1. Contexto y Problema

En TexCore, un **Químico** no es una entidad independiente en la base de datos, sino un subtipo de **Producto** con `tipo = 'quimico'` (o `'insumo'`). Ambos se persisten en la tabla `gestion_producto`.

Sin embargo, en el frontend:
- El estado `productos` se alimenta de `/api/productos/`.
- El estado `quimicos` se alimenta de `/api/chemicals/`.

Al mutar (crear, actualizar o eliminar) un químico desde la interfaz de *Químicos*, el cambio solo se reflejaba en el arreglo `quimicos`. De igual forma, si se creaba o actualizaba un producto de tipo `'quimico'` o `'insumo'` desde la interfaz de *Productos*, el arreglo `quimicos` no se enteraba hasta un refresco manual completo de la aplicación (F5).

---

## 2. Requerimientos Funcionales

1. **Creación de Químicos:** Al crear un químico en la pestaña correspondiente, debe agregarse inmediatamente a la lista de `productos` con `tipo: 'quimico'`.
2. **Actualización de Químicos:** Al editar un químico, cualquier cambio en código, descripción, unidad, presentación o precio debe reflejarse instantáneamente en la lista de `productos`.
3. **Eliminación de Químicos:** Al eliminar un químico, debe desaparecer inmediatamente de `quimicos` y de `productos`.
4. **Creación de Productos:** Si un nuevo producto tiene `tipo === 'quimico'` o `tipo === 'insumo'`, debe incorporarse automáticamente a la lista de `quimicos`.
5. **Actualización de Productos:**
   - Si un producto sigue siendo químico o insumo, se actualiza en `quimicos`.
   - Si cambió de otro tipo a químico/insumo, se agrega a `quimicos`.
   - Si cambió de químico a otro tipo (ej. `hilo`), se retira de `quimicos`.
6. **Eliminación de Productos:** Si se elimina un producto que estaba en `quimicos`, debe desaparecer también de `quimicos`.
7. **Reutilización DRY:** La lógica debe ser pura e inmutable, ubicada en `frontend/src/lib/catalogSync.ts`, utilizada tanto por `BodegueroDashboard` como por `useSedeSpecificData`.

---

## 3. Arquitectura y Métodos

### `frontend/src/lib/catalogSync.ts`
- `isChemicalType(tipo?: string): boolean`
- `syncAddChemicalToProducts<T extends { id: number }, C extends { id: number }>(productos: T[], chemical: C): T[]`
- `syncUpdateChemicalInProducts<T extends { id: number }, C extends { id: number }>(productos: T[], chemicalId: number, chemical: C): T[]`
- `syncAddProductToChemicals<C extends { id: number }, P extends { id: number; tipo?: string }>(quimicos: C[], product: P): C[]`
- `syncUpdateProductInChemicals<C extends { id: number }, P extends { id: number; tipo?: string }>(quimicos: C[], productId: number, product: P): C[]`
- `syncRemoveItemById<T extends { id: number }>(items: T[], id: number): T[]`

---

## 4. Estrategia de Testing (ISTQB CTFL v4.0)

- `frontend/src/lib/catalogSync.test.ts`: Pruebas exhaustivas de todos los casos de mutación pura.
- `frontend/src/components/bodeguero/BodegueroDashboard.test.tsx`: Pruebas de integración reactiva en el dashboard del bodeguero.
- `frontend/src/components/admin-sistemas/useSedeSpecificData.test.ts`: Pruebas de integración en el hook de sede de administración.
