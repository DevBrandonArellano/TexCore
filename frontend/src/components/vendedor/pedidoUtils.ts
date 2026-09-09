/**
 * Parsea fecha_pedido del backend (UTC).
 * - Con Z o +00:00: ya es UTC → JS convierte a hora local al formatear.
 * - Sin timezone: se asume UTC para evitar desfase (ej: "2026-03-09T19:30" sin Z = local en JS, añadimos Z).
 */
export function parseFechaPedido(value: string): Date {
  if (!value) return new Date();
  const trimmed = (value || '').trim();
  if (!trimmed) return new Date();
  if (trimmed.includes('T') && !/Z|[+-]\d{2}:?\d{2}$/.test(trimmed)) {
    return new Date(trimmed.endsWith('Z') ? trimmed : trimmed + 'Z');
  }
  if (trimmed.includes('T')) return new Date(trimmed);
  return new Date(trimmed + 'T12:00:00Z');
}

interface ItemConTotal {
  peso: number;
  precio_unitario: number;
  incluye_iva?: boolean;
}

/** Suma subtotal + IVA (15% si incluye_iva) de una lista de items de pedido. */
export function calculateItemsTotal(items: ItemConTotal[]): number {
  return items.reduce((acc, item) => {
    const subtotal = item.peso * item.precio_unitario;
    const iva = item.incluye_iva ? subtotal * 0.15 : 0;
    return acc + subtotal + iva;
  }, 0);
}

/** Texto de días en mora desde la última compra, solo si hay cartera vencida. */
export function calcularDiasMora(fechaUltimaCompra: string | undefined, carteraVencida: string | number | undefined): string {
  if (!fechaUltimaCompra || parseFloat(carteraVencida?.toString() || '0') <= 0) return '';
  const lastPurchase = new Date(fechaUltimaCompra);
  const today = new Date();
  const diffTime = Math.abs(today.getTime() - lastPurchase.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return `Últ. factura hace ${diffDays} días`;
}

/** Limpia un input numérico de texto libre: coma→punto, quita ceros a la izquierda salvo "0.x". */
export function normalizarInputNumerico(raw: string): string {
  let valStr = raw.replace(',', '.');
  if (valStr.length > 1 && valStr.startsWith('0') && !valStr.startsWith('0.')) {
    valStr = valStr.replace(/^0+/, '');
    if (valStr === '') valStr = '0';
  }
  return valStr;
}

/** Porcentaje de saldo usado sobre el límite de crédito, acotado a 100%. */
export function calcularPorcentajeCredito(saldo: number, limiteCredito: number): number {
  if (limiteCredito <= 0) return 0;
  return Math.min((saldo / limiteCredito) * 100, 100);
}
