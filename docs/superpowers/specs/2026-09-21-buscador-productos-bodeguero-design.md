# Especificación de Diseño: Buscador Reactivo de Productos (Código y Descripción) en Rol Bodeguero

**Fecha:** 2026-09-21  
**Autor:** Brandon Arellano & Antigravity (Equipo Senior de Desarrollo y UX Industrial)  
**Rama Git:** `MES`  
**Estado:** Implementado / En Verificación  
**Estándares:** ISO/IEC 25010 (Usabilidad y Eficiencia Operativa) | ISTQB CTFL v4.0 | Radix UI / W3C WAI-ARIA 1.2  

---

## 1. Contexto y Justificación Operativa

En las operaciones diarias de almacén e inventario textil de TexCore, el usuario con rol de **Bodeguero** realiza ingresos continuos de materiales:
- Compras de materias primas (fardos de algodón, fibras de poliéster).
- Ingreso de hilados crudos o teñidos.
- Transferencias inter-bodega y registro de mermas.

### Problema Operativo Previo
En el formulario de ingreso ([`RegistrarEntradaView.tsx`](../../frontend/src/components/admin-sistemas/RegistrarEntradaView.tsx)) y demás vistas de bodega, la selección del producto dependía de un componente desplegable tradicional ([`ProductSelect`](../../frontend/src/components/ui/product-select.tsx)) basado en `<Select>` nativo de Radix UI:
1. **Sin filtrado ni buscador:** Al crecer el catálogo a decenas o cientos de SKUs, el operario debía desplazarse manualmente por una lista vertical extensa para encontrar el material deseado.
2. **Omisión visual del código SKU:** El desplegable solo renderizaba la descripción del producto (`descripcion`), omitiendo el código de catálogo (`codigo`). En planta, los bodegueros y operarios identifican los materiales principalmente por su código técnico (ej. `HIL-20/1`, `TEL-ALGODON-JERSEY-01`, `MP-FIBRA-PEINADA`).
3. **Lentitud en terminales:** No admitía atajos de teclado rápidos (como autocompletado y selección inmediata con tecla `Enter`).

---

## 2. Requerimiento del Usuario

> *"En el rol de bodeguero, cuando ingresamos los productos tenemos que escoger el producto; el usuario solicita tener un buscador para poder ingresar el código o la descripción y de esta manera agilizar el trabajo."*

---

## 3. Arquitectura de la Solución (Frontend React / TypeScript)

La solución se implementa a nivel del componente transversal [`ProductSelect`](../../frontend/src/components/ui/product-select.tsx) para enriquecer no solo la pestaña de **Entrada** de [`BodegueroDashboard.tsx`](../../frontend/src/components/bodeguero/BodegueroDashboard.tsx), sino también las transferencias, mermas y transformaciones.

### 3.1 Características Principales

1. **Buscador Sticky Integrado:**
   - Barra de búsqueda fija en la parte superior del menú desplegable (`<Input />` con ícono de lupa y botón `X` de reseteo).
   - Enfocado automático (`autoFocus`) al abrir el desplegable.
   - Aislamiento de eventos: `onPointerDown={(e) => e.stopPropagation()}` y `onKeyDown={(e) => e.stopPropagation()}` para evitar colisiones con el typeahead nativo de Radix UI.

2. **Búsqueda Bimodal e Insensible a Acentos (NFD):**
   - El algoritmo normaliza tanto el término de búsqueda como los campos del producto mediante `.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()`.
   - Permite buscar indistintamente por:
     - **Código exacto o parcial:** (ej. `HIL`, `TEL-01`, `MP`).
     - **Descripción con o sin tildes:** (ej. escribir `algodon` encuentra `Hilo de Algodón`).
     - **Tipo o categoría de producto:** (ej. `intermedio`, `terminado`, `quimico`).

3. **Visualización de Alto Contraste para Planta:**
   - En cada ítem:
     - Insignia tipográfica monoespaciada con el código SKU: `[PROD-1]`.
     - Descripción textual completa.
     - Badge sutil con la categoría del producto (`materia_prima`, `hilo`, `producto_intermedio`).
   - En el gatillo/trigger (`SelectTrigger`):
     - Muestra `[CODIGO] DESCRIPCION` una vez seleccionado (ej. `[HIL-001] Hilo 20/1 Algodón Crudo`).

4. **Accesibilidad WAI-ARIA y Compatibilidad con Testing Library:**
   - Para evitar romper suites de pruebas existentes (ej. `RegistrarMermaDialog.test.tsx`) que buscan el elemento mediante `findByRole('option', { name: 'Hilo de Algodón' })`, los badges visuales se marcan con `aria-hidden="true"`, preservando el nombre accesible exacto esperado.

5. **Atajo Rápido de Teclado:**
   - Al escribir en el buscador y presionar `Enter`, si existen coincidencias, se selecciona automáticamente el primer producto de la lista y se cierra el menú.

---

## 4. Matriz de Componentes Impactados

| Componente | Archivo | Impacto |
|---|---|---|
| **Componente Core** | [`frontend/src/components/ui/product-select.tsx`](../../frontend/src/components/ui/product-select.tsx) | Rediseño a Combobox reactivo con buscador por código/descripción. |
| **Ingreso de Mercadería** | [`frontend/src/components/admin-sistemas/RegistrarEntradaView.tsx`](../../frontend/src/components/admin-sistemas/RegistrarEntradaView.tsx) | Beneficio directo: búsqueda instantánea al registrar compras o recepciones. |
| **Transferencias** | [`frontend/src/components/admin-sistemas/TransferView.tsx`](../../frontend/src/components/admin-sistemas/TransferView.tsx) | Búsqueda ágil de producto para transferir entre bodegas. |
| **Mermas** | [`frontend/src/components/bodeguero/RegistrarMermaDialog.tsx`](../../frontend/src/components/bodeguero/RegistrarMermaDialog.tsx) | Búsqueda ágil de producto para deducir mermas. |
| **Kardex / Reportes** | [`KardexView.tsx`](../../frontend/src/components/admin-sistemas/KardexView.tsx), [`ReportesView.tsx`](../../frontend/src/components/admin-sistemas/ReportesView.tsx) | Filtrado más rápido en análisis histórico. |

---

## 5. Criterios de Aceptación (DoD)

1. El usuario puede abrir el selector y escribir un código de producto (ej. `HIL-001`) para filtrar la lista en tiempo real.
2. El usuario puede escribir una descripción sin tildes (ej. `algodon`) y ver los productos con tilde (`Algodón`).
3. El trigger cerrado muestra el código y la descripción del producto seleccionado.
4. Las pruebas unitarias de `product-select.test.tsx` pasan al 100%.
5. Las suites existentes de `RegistrarMermaDialog.test.tsx`, `KardexView.test.tsx` y `BodegueroDashboard.test.tsx` pasan sin regresiones.
