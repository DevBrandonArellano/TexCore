import type { Producto, Quimico } from './types';

/**
 * Determina si el tipo de un producto corresponde a la categoría de químicos/insumos.
 */
export function isChemicalType(tipo?: string | null): boolean {
  if (!tipo) return false;
  const normalized = tipo.toLowerCase().trim();
  return normalized === 'quimico' || normalized === 'insumo';
}

/**
 * Convierte un Quimico a un Producto válido para el catálogo general.
 */
export function chemicalToProduct(chemical: Quimico): Producto {
  return {
    id: chemical.id,
    codigo: chemical.codigo,
    descripcion: chemical.descripcion,
    tipo: 'quimico',
    unidad_medida: (chemical.unidad_medida as any) || 'kg',
    stock_minimo: chemical.stock_minimo ?? 0,
    presentacion: chemical.presentacion || undefined,
    pais_origen: chemical.pais_origen || undefined,
    calidad: chemical.calidad || undefined,
    precio_base: Number(chemical.precio_base) || 0,
  };
}

/**
 * Convierte un Producto a un Quimico si su tipo corresponde a químico/insumo.
 */
export function productToChemical(product: Producto): Quimico {
  return {
    id: product.id,
    codigo: product.codigo,
    descripcion: product.descripcion,
    tipo: 'quimico',
    unidad_medida: product.unidad_medida || 'kg',
    stock_minimo: product.stock_minimo,
    presentacion: product.presentacion || undefined,
    pais_origen: product.pais_origen || undefined,
    calidad: product.calidad || undefined,
    precio_base: Number(product.precio_base) || 0,
  };
}

/**
 * Remueve un elemento por su ID de manera inmutable.
 */
export function syncRemoveItemById<T extends { id: number }>(items: T[], id: number): T[] {
  return items.filter(item => item.id !== id);
}

/**
 * Agrega o actualiza un químico dentro de la lista general de productos.
 */
export function syncAddChemicalToProducts(productos: Producto[], chemical: Quimico): Producto[] {
  const asProduct = chemicalToProduct(chemical);
  const exists = productos.some(p => p.id === chemical.id);
  if (exists) {
    return productos.map(p => (p.id === chemical.id ? { ...p, ...asProduct } : p));
  }
  return [...productos, asProduct];
}

/**
 * Actualiza los campos de un químico existente dentro de la lista de productos.
 */
export function syncUpdateChemicalInProducts(
  productos: Producto[],
  chemicalId: number,
  chemicalData: Partial<Quimico> & { id?: number }
): Producto[] {
  return productos.map(p => {
    if (p.id !== chemicalId) return p;
    return {
      ...p,
      codigo: chemicalData.codigo !== undefined ? chemicalData.codigo : p.codigo,
      descripcion: chemicalData.descripcion !== undefined ? chemicalData.descripcion : p.descripcion,
      unidad_medida: (chemicalData.unidad_medida as any) !== undefined ? (chemicalData.unidad_medida as any) : p.unidad_medida,
      presentacion: chemicalData.presentacion !== undefined ? chemicalData.presentacion : p.presentacion,
      precio_base: chemicalData.precio_base !== undefined ? Number(chemicalData.precio_base) : p.precio_base,
      stock_minimo: chemicalData.stock_minimo !== undefined ? Number(chemicalData.stock_minimo) : p.stock_minimo,
      pais_origen: chemicalData.pais_origen !== undefined ? chemicalData.pais_origen : p.pais_origen,
      calidad: chemicalData.calidad !== undefined ? chemicalData.calidad : p.calidad,
    };
  });
}

/**
 * Si un nuevo producto es químico o insumo, lo agrega a la lista de químicos evitando duplicados.
 */
export function syncAddProductToChemicals(quimicos: Quimico[], product: Producto): Quimico[] {
  if (!isChemicalType(product.tipo)) {
    return quimicos;
  }
  const asChemical = productToChemical(product);
  const exists = quimicos.some(q => q.id === product.id);
  if (exists) {
    return quimicos.map(q => (q.id === product.id ? { ...q, ...asChemical } : q));
  }
  return [...quimicos, asChemical];
}

/**
 * Actualiza la lista de químicos ante una mutación de un producto:
 * - Si el producto sigue siendo químico/insumo, lo actualiza (o agrega si antes era de otro tipo).
 * - Si el producto cambió a un tipo no químico (ej. 'hilo'), lo retira de la lista de químicos.
 */
export function syncUpdateProductInChemicals(
  quimicos: Quimico[],
  productId: number,
  product: Producto
): Quimico[] {
  const isNowChemical = isChemicalType(product.tipo);
  const existsInChemicals = quimicos.some(q => q.id === productId);

  if (!isNowChemical) {
    return existsInChemicals ? quimicos.filter(q => q.id !== productId) : quimicos;
  }

  const asChemical = productToChemical(product);
  if (existsInChemicals) {
    return quimicos.map(q => (q.id === productId ? { ...q, ...asChemical } : q));
  }
  return [...quimicos, asChemical];
}
