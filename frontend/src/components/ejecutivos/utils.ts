export const fmt = (n: number, dec = 2) =>
  n.toLocaleString('es-EC', { minimumFractionDigits: dec, maximumFractionDigits: dec });

export const abreviar = (s: string, max = 20) =>
  s.length <= max ? s : s.slice(0, max - 1) + '…';

export const toNum = (v: unknown): number => {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v) || 0;
  return 0;
};

/** Total de un pedido: usa `total` si viene calculado, o lo deriva de sus detalles. */
export const getPedidoTotal = (p: { total?: unknown; detalles?: any[] }) =>
  toNum(p.total) || (p.detalles?.reduce(
    (s: number, d: any) => s + toNum(d.peso) * toNum(d.precio_unitario), 0
  ) ?? 0);

// Re-exportado desde src/lib/collections.ts — punto único de verdad,
// usado también fuera del módulo ejecutivos (jefe-area, vendedor, shared).
export { toArray } from '../../lib/collections';
