# Plan de Implementación: Sincronización Bidireccional Reactiva entre Productos y Químicos

- **Especificación:** `docs/superpowers/specs/2026-09-21-sincronizacion-productos-quimicos-design.md`
- **Estado:** Completado

---

## Tareas

### FASE 1: Motor de Sincronización Pura
- [x] **Tarea 1.1:** Crear `frontend/src/lib/catalogSync.ts` con funciones puras e inmutables para adición, actualización, eliminación y comprobación de tipo de químicos/productos.
- [x] **Tarea 1.2:** Crear suite de pruebas unitarias `frontend/src/lib/catalogSync.test.ts` cubriendo el 100% de ramas y casos límite (14/14 tests pasando).

### FASE 2: Integración en BodegueroDashboard
- [x] **Tarea 2.1:** Integrar `catalogSync` en `frontend/src/components/bodeguero/BodegueroDashboard.tsx` (`handleChemicalCreate`, `handleChemicalUpdate`, `handleChemicalDelete`, `handleProductCreate`, `handleProductUpdate`, `handleProductDelete`).
- [x] **Tarea 2.2:** Agregar pruebas unitarias en `frontend/src/components/bodeguero/BodegueroDashboard.test.tsx` validando la sincronización cruzada entre las pestañas de Productos y Químicos (34/34 tests pasando).

### FASE 3: Integración en useSedeSpecificData (AdminSistemas)
- [x] **Tarea 3.1:** Integrar `catalogSync` en `frontend/src/components/admin-sistemas/useSedeSpecificData.ts`.
- [x] **Tarea 3.2:** Actualizar pruebas unitarias en `frontend/src/components/admin-sistemas/useSedeSpecificData.test.ts` verificando la coherencia entre `productos` y `quimicos` (62/62 tests pasando).

### FASE 4: Verificación Integral y Documentación
- [x] **Tarea 4.1:** Ejecutar `npx tsc --noEmit` en `frontend/` y validar 0 errores de compilación.
- [x] **Tarea 4.2:** Ejecutar suite completa de Vitest para los componentes afectados (131/131 tests pasando).
- [x] **Tarea 4.3:** Actualizar `CHANGELOG.md` con los detalles de la solución implementada.
- [x] **Tarea 4.4:** Crear walkthrough artifact documentando la arquitectura y resultados.
