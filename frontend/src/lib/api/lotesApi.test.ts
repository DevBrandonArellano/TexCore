import { describe, it, expect, vi, beforeEach } from 'vitest';
import { lotesApi } from './lotesApi';

const mockGet = vi.fn();
vi.mock('../axios', () => ({ default: { get: (...args: unknown[]) => mockGet(...args) } }));

describe('lotesApi', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockGet.mockResolvedValue({ data: { ok: true } });
  });

  it('listar dado página, tamaño y filtros cuando consulta entonces los envía como parámetros', async () => {
    await lotesApi.listar(2, 120, { operario: 7, ordering: '-hora_final' });
    expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/', {
      params: { operario: 7, ordering: '-hora_final', page: 2, page_size: 120 },
    });
  });

  it('listar dado filtros con page cuando consulta entonces la paginación no se sobrescribe', async () => {
    await lotesApi.listar(3, 30, { page: 99 } as never);
    expect(mockGet.mock.calls[0][1].params.page).toBe(3);
  });

  it('resumenHoy dado el resumen del día cuando consulta entonces usa la acción resumen-hoy', async () => {
    await expect(lotesApi.resumenHoy()).resolves.toEqual({ ok: true });
    expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/resumen-hoy/');
  });

  it('ficha dado id cuando consulta entonces usa la acción genealogia del lote', async () => {
    await lotesApi.ficha(5);
    expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/5/genealogia/');
  });

  it('genealogia dado código y dirección cuando consulta entonces usa el grafo MES', async () => {
    await lotesApi.genealogia('LOT-1', 'adelante');
    expect(mockGet).toHaveBeenCalledWith('/corridas-produccion/trazabilidad-lote/', {
      params: { codigo: 'LOT-1', direccion: 'adelante' },
    });
  });

  it('movimientos dado código con caracteres especiales cuando consulta entonces lo codifica', async () => {
    await lotesApi.movimientos('LOT A/1');
    expect(mockGet).toHaveBeenCalledWith('/inventory/lotes/LOT%20A%2F1/movimientos/');
  });

  it('materiasPrimas dado id cuando consulta entonces envía lote_id', async () => {
    await lotesApi.materiasPrimas(9);
    expect(mockGet).toHaveBeenCalledWith('/trazabilidad/lote-produccion/', { params: { lote_id: 9 } });
  });

  it('consumos dado lote cuando consulta entonces filtra el consumo por lote', async () => {
    mockGet.mockResolvedValueOnce({ data: { count: 1, results: [{ id: 1 }] } });
    await expect(lotesApi.consumos(3)).resolves.toEqual([{ id: 1 }]);
    expect(mockGet).toHaveBeenCalledWith('/consumo-lote-detalle/', { params: { lote_produccion: 3, page_size: 500 } });
  });

  it('costo dado lote cuando consulta entonces usa la acción obtener-costo', async () => {
    await lotesApi.costo(3);
    expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/3/obtener-costo/');
  });
});

