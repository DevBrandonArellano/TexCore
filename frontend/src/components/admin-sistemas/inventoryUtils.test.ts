import { describe, it, expect } from 'vitest';
import { normalizeBodegaKey, calcularSaldoAcumulado, validateTransfer } from './inventoryUtils';

describe('normalizeBodegaKey', () => {
  it('dado null o vacio cuando normaliza entonces retorna cadena vacia', () => {
    expect(normalizeBodegaKey(null)).toBe('');
    expect(normalizeBodegaKey(undefined)).toBe('');
    expect(normalizeBodegaKey('')).toBe('');
  });

  it('dado un string plano cuando normaliza entonces lo usa directamente', () => {
    expect(normalizeBodegaKey('Bodega Central')).toBe('bodega central');
  });

  it('dado un objeto con nombre cuando normaliza entonces usa esa propiedad', () => {
    expect(normalizeBodegaKey({ nombre: 'Bodega Norte' })).toBe('bodega norte');
  });

  it('dado un valor no string ni objeto con nombre cuando normaliza entonces usa String()', () => {
    expect(normalizeBodegaKey(42)).toBe('42');
  });

  it('dado un nombre con sufijo de sede cuando normaliza entonces recorta el sufijo', () => {
    expect(normalizeBodegaKey('Bodega Central (Sede Norte)')).toBe('bodega central');
  });
});

describe('calcularSaldoAcumulado', () => {
  it('dado movimientos de entrada y salida cuando calcula entonces acumula el saldo en orden cronologico inverso', () => {
    const data = [
      { fecha: '2026-01-02', cantidad: '10', bodega_destino: 'Central', bodega_origen: 'Norte' },
      { fecha: '2026-01-01', cantidad: '5', bodega_destino: 'Central', bodega_origen: 'Norte' },
      { fecha: '2026-01-03', cantidad: '3', bodega_destino: 'Norte', bodega_origen: 'Central' },
    ];
    const result = calcularSaldoAcumulado(data, 'Central');
    // Orden invertido: el más reciente primero (salida del 03, luego entrada del 02, luego del 01)
    expect(result[0].esSalida).toBe(true);
    expect(result[0].saldo_acumulado).toBe(12); // 5 + 10 - 3
    expect(result[2].esEntrada).toBe(true);
    expect(result[2].saldo_acumulado).toBe(5);
  });

  it('dado sin bodega seleccionada cuando calcula entonces no marca entrada ni salida', () => {
    const data = [{ fecha: '2026-01-01', cantidad: '10', bodega_destino: 'Central', bodega_origen: 'Norte' }];
    const result = calcularSaldoAcumulado(data, undefined);
    expect(result[0].esEntrada).toBe(false);
    expect(result[0].esSalida).toBe(false);
    expect(result[0].saldo_acumulado).toBe(0);
  });

  it('dado nombres de producto y bodega ya resueltos cuando calcula entonces usa los campos _nombre', () => {
    const data = [{
      fecha: '2026-01-01', cantidad: '1',
      producto_nombre: 'Hilo Azul', producto: 'PID-1',
      bodega_origen_nombre: 'Norte', bodega_origen: 1,
      bodega_destino_nombre: 'Central', bodega_destino: 2,
    }];
    const result = calcularSaldoAcumulado(data, undefined);
    expect(result[0].producto).toBe('Hilo Azul');
    expect(result[0].bodega_origen).toBe('Norte');
    expect(result[0].bodega_destino).toBe('Central');
  });

  it('dado cantidad con coma decimal cuando calcula entonces la interpreta como punto', () => {
    const data = [{ fecha: '2026-01-01', cantidad: '10,5', bodega_destino: 'Central', bodega_origen: 'Norte' }];
    const result = calcularSaldoAcumulado(data, 'Central');
    expect(result[0].saldo_acumulado).toBe(10.5);
  });
});

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
