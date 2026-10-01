import { describe, it, expect, vi, beforeEach } from 'vitest';
import { indicadoresApi } from './indicadoresApi';

const mockGet = vi.fn();
vi.mock('../axios', () => ({ default: { get: (...a: unknown[]) => mockGet(...a) } }));

describe('indicadoresApi', () => {
  beforeEach(() => { mockGet.mockReset(); mockGet.mockResolvedValue({ data: { ok: true } }); });

  it('reporteEficienciaArea dado área cuando consulta entonces usa la acción del área', async () => {
    await expect(indicadoresApi.reporteEficienciaArea(4)).resolves.toEqual({ ok: true });
    expect(mockGet).toHaveBeenCalledWith('/areas/4/reporte-eficiencia/');
  });

  it('desempenoOperario dado usuario cuando consulta entonces usa la acción desempeno', async () => {
    await indicadoresApi.desempenoOperario(7);
    expect(mockGet).toHaveBeenCalledWith('/users/7/desempeno/');
  });

  it('vendedores cuando consulta entonces usa la acción vendedores', async () => {
    await indicadoresApi.vendedores();
    expect(mockGet).toHaveBeenCalledWith('/users/vendedores/');
  });
});
