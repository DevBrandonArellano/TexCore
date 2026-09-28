import { describe, it, expect } from 'vitest';
import { validateTransfer } from './inventoryUtils';

describe('validateTransfer', () => {
  const stockConLote = [{ id: 1, producto: 'P', producto_id: 1, bodega: 'B', bodega_id: 1, lote: 'L1', lote_id: 5, lote_codigo: 'L1', cantidad: '100' }];
  const stockSinLote = [{ id: 2, producto: 'P', producto_id: 1, bodega: 'B', bodega_id: 1, lote: null, lote_id: null, lote_codigo: null, cantidad: '50' }];

  function baseForm(overrides: Partial<Record<string, string>> = {}) {
    return {
      producto_id: '1', bodega_origen_id: '1', bodega_destino_id: '2',
      cantidad: '10', lote_id: '', _justificacion_auditoria: 'motivo',
      ...overrides,
    };
  }

  it('dado formulario vacio cuando valida entonces retorna error por cada campo requerido', () => {
    const errors = validateTransfer(baseForm({
      producto_id: '', bodega_origen_id: '', bodega_destino_id: '', cantidad: '', _justificacion_auditoria: '',
    }), []);
    expect(errors.producto_id).toBeDefined();
    expect(errors.bodega_origen_id).toBeDefined();
    expect(errors.bodega_destino_id).toBeDefined();
    expect(errors.cantidad).toBeDefined();
    expect(errors._justificacion_auditoria).toBeDefined();
  });

  it('dado cantidad cero o negativa cuando valida entonces marca cantidad invalida', () => {
    expect(validateTransfer(baseForm({ cantidad: '0' }), []).cantidad).toBe('Cantidad inválida.');
    expect(validateTransfer(baseForm({ cantidad: '-5' }), []).cantidad).toBe('Cantidad inválida.');
  });

  it('dado producto y bodega origen sin stock disponible cuando valida entonces marca stock faltante', () => {
    const errors = validateTransfer(baseForm(), []);
    expect(errors.stock).toBe('No hay stock disponible para este producto en esta bodega.');
  });

  it('dado lote_id especificado sin stock para ese lote cuando valida entonces menciona el lote en el mensaje', () => {
    const errors = validateTransfer(baseForm({ lote_id: '99' }), stockSinLote);
    expect(errors.stock).toBe('No hay stock disponible para este producto y lote en esta bodega.');
  });

  it('dado lote_id que coincide con stock disponible cuando valida entonces no marca error de stock', () => {
    const errors = validateTransfer(baseForm({ lote_id: '5', cantidad: '10' }), stockConLote);
    expect(errors.stock).toBeUndefined();
  });

  it('dado lote_id en null (string) cuando valida entonces busca stock sin lote', () => {
    const errors = validateTransfer(baseForm({ lote_id: 'null', cantidad: '10' }), stockSinLote);
    expect(errors.stock).toBeUndefined();
  });

  it('dado stock disponible pero cantidad mayor a la existente cuando valida entonces marca stock insuficiente', () => {
    const errors = validateTransfer(baseForm({ lote_id: '5', cantidad: '500' }), stockConLote);
    expect(errors.cantidad).toBe('Stock insuficiente. Disponible: 100');
  });

  it('dado formulario valido con stock suficiente cuando valida entonces no retorna errores', () => {
    const errors = validateTransfer(baseForm({ lote_id: '5', cantidad: '10' }), stockConLote);
    expect(Object.keys(errors)).toHaveLength(0);
  });
});
