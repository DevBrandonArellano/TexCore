export interface StockItem {
  id: number;
  producto: string;
  producto_id: number;
  bodega: string;
  bodega_id: number;
  lote: string | null;
  lote_id: number | null;
  lote_codigo: string | null;
  cantidad: string;
}

export const ITEMS_PER_PAGE = 20;

/**
 * API envía str(Bodega) = "Nombre (Sede)" (ver gestion.models.Bodega.__str__);
 * el selector solo tiene `nombre`, así que comparamos por nombre base sin sufijo " (sede)".
 */
export const normalizeBodegaKey = (raw: any): string => {
  if (raw == null || raw === '') return '';
  const s =
    typeof raw === 'string'
      ? raw
      : typeof raw === 'object' && raw && 'nombre' in raw && typeof (raw as any).nombre === 'string'
        ? (raw as any).nombre
        : String(raw);
  const t = s.trim().toLowerCase();
  const idx = t.indexOf(' (');
  return idx >= 0 ? t.slice(0, idx).trim() : t;
};

/**
 * Calcula el saldo corrido en cliente (no usar saldo_resultante fila a fila, viene como
 * snapshot del movimiento y a veces en string; el acumulado depende de esta bodega y del orden).
 * Devuelve los movimientos ordenados por fecha ascendente para el cálculo, y luego invertidos
 * (más reciente primero) para mostrar.
 */
export function calcularSaldoAcumulado(data: any[], selectedBodegaNombre: string | undefined): any[] {
  const selectedKey = normalizeBodegaKey(selectedBodegaNombre);

  const sorted = [...data].sort((a: any, b: any) => new Date(a.fecha).getTime() - new Date(b.fecha).getTime());

  let saldoAcumulado = 0;
  const withSaldo = sorted.map((mov: any) => {
    const cant = parseFloat(String(mov.cantidad).replace(',', '.'));
    const destinoKey = normalizeBodegaKey(mov.bodega_destino);
    const origenKey = normalizeBodegaKey(mov.bodega_origen);
    const esEntrada = !!selectedKey && destinoKey === selectedKey;
    const esSalida = !!selectedKey && origenKey === selectedKey;

    if (esEntrada) saldoAcumulado += cant;
    else if (esSalida) saldoAcumulado -= cant;

    return {
      ...mov,
      producto: mov.producto_nombre || mov.producto,
      bodega_origen: mov.bodega_origen_nombre || mov.bodega_origen,
      bodega_destino: mov.bodega_destino_nombre || mov.bodega_destino,
      saldo_acumulado: saldoAcumulado,
      esEntrada,
      esSalida,
    };
  });

  return withSaldo.reverse();
}

interface TransferFormData {
  producto_id: string;
  bodega_origen_id: string;
  bodega_destino_id: string;
  cantidad: string;
  lote_id: string;
  _justificacion_auditoria: string;
}

export function validateTransfer(formData: TransferFormData, availableLots: StockItem[]): Record<string, string> {
  const newErrors: Record<string, string> = {};
  if (!formData.producto_id) newErrors.producto_id = 'Producto es requerido.';
  if (!formData.bodega_origen_id) newErrors.bodega_origen_id = 'Bodega origen requerida.';
  if (!formData.bodega_destino_id) newErrors.bodega_destino_id = 'Bodega destino requerida.';
  if (!formData.cantidad || parseFloat(formData.cantidad) <= 0) newErrors.cantidad = 'Cantidad inválida.';
  if (!formData._justificacion_auditoria) newErrors._justificacion_auditoria = 'Justificación requerida.';

  // Validar stock disponible
  if (formData.producto_id && formData.bodega_origen_id) {
    const selectedStock = availableLots.find(s =>
      (formData.lote_id && formData.lote_id !== 'null' ? String(s.lote_id ?? '') === formData.lote_id : s.lote_id === null)
    );
    if (!selectedStock) {
      newErrors.stock = 'No hay stock disponible para este producto' + (formData.lote_id ? ' y lote' : '') + ' en esta bodega.';
    } else if (parseFloat(formData.cantidad) > parseFloat(selectedStock.cantidad)) {
      newErrors.cantidad = `Stock insuficiente. Disponible: ${selectedStock.cantidad}`;
    }
  }

  return newErrors;
}
