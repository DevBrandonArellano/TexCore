import { describe, it, expect } from 'vitest';
import {
  parseFechaPedido, calculateItemsTotal, calcularDiasMora,
  normalizarInputNumerico, calcularPorcentajeCredito,
} from './pedidoUtils';

describe('parseFechaPedido', () => {
  it('dado valor vacio o nulo cuando parsea entonces retorna la fecha actual', () => {
    expect(parseFechaPedido('')).toBeInstanceOf(Date);
    expect(parseFechaPedido(undefined as any)).toBeInstanceOf(Date);
  });

  it('dado solo espacios cuando parsea entonces retorna la fecha actual', () => {
    expect(parseFechaPedido('   ')).toBeInstanceOf(Date);
  });

  it('dado fecha con T sin timezone cuando parsea entonces asume UTC agregando Z', () => {
    const d = parseFechaPedido('2026-03-09T19:30:00');
    expect(d.toISOString()).toBe('2026-03-09T19:30:00.000Z');
  });

  it('dado fecha con T y Z cuando parsea entonces la usa directamente', () => {
    const d = parseFechaPedido('2026-03-09T19:30:00Z');
    expect(d.toISOString()).toBe('2026-03-09T19:30:00.000Z');
  });

  it('dado fecha con T y offset explicito cuando parsea entonces respeta ese offset', () => {
    const d = parseFechaPedido('2026-03-09T19:30:00-05:00');
    expect(d.toISOString()).toBe('2026-03-10T00:30:00.000Z');
  });

  it('dado fecha sin T (solo YYYY-MM-DD) cuando parsea entonces asume mediodia UTC', () => {
    const d = parseFechaPedido('2026-03-09');
    expect(d.toISOString()).toBe('2026-03-09T12:00:00.000Z');
  });
});

describe('calculateItemsTotal', () => {
  it('dado items con IVA cuando calcula entonces suma subtotal mas 15%', () => {
    const total = calculateItemsTotal([{ peso: 10, precio_unitario: 2, incluye_iva: true }]);
    expect(total).toBeCloseTo(23, 5); // 20 + 15% de 20
  });

  it('dado items sin IVA cuando calcula entonces suma solo el subtotal', () => {
    const total = calculateItemsTotal([{ peso: 10, precio_unitario: 2 }]);
    expect(total).toBe(20);
  });

  it('dado lista vacia cuando calcula entonces retorna cero', () => {
    expect(calculateItemsTotal([])).toBe(0);
  });
});

describe('calcularDiasMora', () => {
  it('dado sin fecha de ultima compra cuando calcula entonces retorna cadena vacia', () => {
    expect(calcularDiasMora(undefined, '100')).toBe('');
  });

  it('dado cartera vencida en cero cuando calcula entonces retorna cadena vacia', () => {
    expect(calcularDiasMora('2026-01-01', '0')).toBe('');
  });

  it('dado cartera vencida negativa cuando calcula entonces retorna cadena vacia', () => {
    expect(calcularDiasMora('2026-01-01', -5)).toBe('');
  });

  it('dado fecha y cartera vencida positiva cuando calcula entonces retorna el texto de dias', () => {
    const hace5Dias = new Date();
    hace5Dias.setDate(hace5Dias.getDate() - 5);
    const result = calcularDiasMora(hace5Dias.toISOString(), 100);
    expect(result).toMatch(/Últ\. factura hace \d+ días/);
  });
});

describe('normalizarInputNumerico', () => {
  it('dado coma decimal cuando normaliza entonces la convierte a punto', () => {
    expect(normalizarInputNumerico('10,5')).toBe('10.5');
  });

  it('dado ceros a la izquierda cuando normaliza entonces los quita', () => {
    expect(normalizarInputNumerico('007')).toBe('7');
  });

  it('dado solo ceros cuando normaliza entonces retorna 0', () => {
    expect(normalizarInputNumerico('000')).toBe('0');
  });

  it('dado valor decimal que empieza con 0 cuando normaliza entonces lo deja intacto', () => {
    expect(normalizarInputNumerico('0.5')).toBe('0.5');
  });

  it('dado un solo caracter cuando normaliza entonces lo deja intacto', () => {
    expect(normalizarInputNumerico('5')).toBe('5');
  });
});

describe('calcularPorcentajeCredito', () => {
  it('dado limite de credito en cero cuando calcula entonces retorna cero', () => {
    expect(calcularPorcentajeCredito(500, 0)).toBe(0);
  });

  it('dado limite de credito negativo cuando calcula entonces retorna cero', () => {
    expect(calcularPorcentajeCredito(500, -100)).toBe(0);
  });

  it('dado saldo menor al limite cuando calcula entonces retorna el porcentaje real', () => {
    expect(calcularPorcentajeCredito(50, 200)).toBe(25);
  });

  it('dado saldo mayor al limite cuando calcula entonces acota a 100', () => {
    expect(calcularPorcentajeCredito(500, 200)).toBe(100);
  });
});
