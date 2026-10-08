import type { StockItem } from '../../types/inventario';

export type { StockItem };

export const ITEMS_PER_PAGE = 20;

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
