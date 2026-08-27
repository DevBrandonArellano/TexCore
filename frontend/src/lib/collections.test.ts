import { describe, it, expect } from 'vitest';
import { toArray } from './collections';

describe('toArray', () => {
  it('dado un array plano cuando normaliza entonces lo retorna igual', () => {
    expect(toArray([1, 2, 3])).toEqual([1, 2, 3]);
  });

  it('dado una respuesta paginada con results cuando normaliza entonces extrae el array interno', () => {
    expect(toArray({ results: [1, 2] })).toEqual([1, 2]);
  });

  it('dado results ausente cuando normaliza entonces retorna arreglo vacio', () => {
    expect(toArray({})).toEqual([]);
  });

  it('dado results no es array cuando normaliza entonces retorna arreglo vacio', () => {
    expect(toArray({ results: 'no-es-array' })).toEqual([]);
  });

  it('dado null o undefined cuando normaliza entonces retorna arreglo vacio', () => {
    expect(toArray(null)).toEqual([]);
    expect(toArray(undefined)).toEqual([]);
  });
});
