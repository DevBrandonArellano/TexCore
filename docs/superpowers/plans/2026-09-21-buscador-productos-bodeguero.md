# Plan de Implementación: Buscador Reactivo de Productos (Código y Descripción) en Bodeguero

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, misma sesión — sin `git commit` automático, Brandon gestiona commits).

**Goal:** Dotar al componente selector de productos ([`ProductSelect`](../../frontend/src/components/ui/product-select.tsx)) de un buscador reactivo bimodal (filtrado instantáneo por código SKU y por descripción con normalización de acentos), para que los bodegueros y operarios puedan seleccionar materiales en segundos durante el registro de entradas, transferencias, transformaciones y mermas.

**Architecture:**
1. **Tipado Estricto:** Saneamiento de tipos en [`frontend/src/lib/types.ts`](../../frontend/src/lib/types.ts) (`LoteProduccion.pedido_venta_reserva` y `PedidoVenta.numero_pedido`) para garantizar compilación limpia con `tsc`.
2. **Componente Combobox Reactivo ([`ProductSelect`](../../frontend/src/components/ui/product-select.tsx)):**
   - Integración de `<Input />` sticky en cabecera de `<SelectContent />` con autoenfoque y botón de reseteo.
   - Algoritmo de normalización NFD insensible a mayúsculas y acentos (`normalizeText`).
   - Insignias de alto contraste (`[codigo]`) visibles en el desplegable y en el trigger una vez seleccionado.
   - Atajo de teclado: tecla `Enter` para selección rápida del primer resultado coincidente.
   - Accesibilidad: `aria-hidden="true"` en insignias visuales para compatibilidad total con tests existentes (evitando colisión de nombres accesibles).
3. **Pruebas y Verificación:**
   - Suite unitaria dedicada en [`frontend/src/components/ui/product-select.test.tsx`](../../frontend/src/components/ui/product-select.test.tsx).
   - Verificación de no-regresión sobre suites de `bodeguero` y `admin-sistemas` (512 tests).

**Tech Stack:** React 18, TypeScript 5, Radix UI Select, Tailwind CSS, Lucide React, Vitest, Testing Library.

**Spec:** [`docs/superpowers/specs/2026-09-21-buscador-productos-bodeguero-design.md`](../specs/2026-09-21-buscador-productos-bodeguero-design.md).

## Global Constraints

- No ejecutar `git add`/`git commit`/`git push` — Brandon gestiona todos los commits del repositorio.
- Convención de tests ISTQB CTFL v4.0: `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`.
- Cero regresiones en los 26 archivos de prueba de `bodeguero` y `admin-sistemas`.

---

### Task 1: Saneamiento de Tipos Base en Frontend

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [x] **Step 1: Agregar campos opcionales a `LoteProduccion` y `PedidoVenta`**
  - Añadir `pedido_venta_reserva?: number | null;` a `LoteProduccion`.
  - Añadir `numero_pedido?: string;` a `PedidoVenta`.
- [x] **Step 2: Verificar compilación TypeScript**
  - Run: `cd frontend && npx tsc --noEmit`

---

### Task 2: Rediseño de `ProductSelect` con Buscador Bimodal

**Files:**
- Modify: `frontend/src/components/ui/product-select.tsx`

- [x] **Step 1: Implementar barra de búsqueda y filtrado reactivo**
  - Input de búsqueda con lupa y botón `X`.
  - Función de normalización de texto NFD para tildes y diacríticos.
  - Filtrado reactivo sobre `codigo`, `descripcion` y `tipo`.
- [x] **Step 2: Estilizar ítems e integrar atajo `Enter`**
  - Visualización del código SKU como badge monoespaciado.
  - Selección rápida del primer resultado al presionar `Enter` en el buscador.
- [x] **Step 3: Ajustar accesibilidad WAI-ARIA**
  - Marcar insignias con `aria-hidden="true"` para que el nombre accesible coincida exactamente con la descripción en Testing Library.

---

### Task 3: Suite de Pruebas Unitarias TDD

**Files:**
- Create: `frontend/src/components/ui/product-select.test.tsx`

- [x] **Step 1: Escribir pruebas unitarias siguiendo estándar ISTQB**
  - Renderizado inicial con placeholder.
  - Búsqueda por código exacto/parcial.
  - Búsqueda por descripción con y sin tildes.
  - Disparo de `onValueChange` al seleccionar.
  - Mensaje descriptivo cuando no hay coincidencias.
- [x] **Step 2: Ejecutar suite de pruebas**
  - Run: `npx vitest run src/components/ui/product-select.test.tsx src/components/bodeguero/RegistrarMermaDialog.test.tsx`
  - Resultado: 14/14 tests pasando (100%).

---

### Task 4: Verificación Integral de No-Regresión

- [x] **Step 1: Ejecución completa de suites de bodega y administración**
  - Run: `npx vitest run src/components/bodeguero/ src/components/admin-sistemas/`
  - Resultado: **26 test files en verde, 512 tests pasando (100%)**.

---

### Task 5: Documentación y Trazabilidad

- [x] **Step 1: Registrar en `CHANGELOG.md` la nueva funcionalidad del rol bodeguero**
- [x] **Step 2: Mantener sincronizada la especificación y el plan de trabajo en `docs/superpowers/`**
