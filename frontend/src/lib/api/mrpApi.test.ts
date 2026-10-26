/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): bloque y sede / todas las sedes / sede / alcance / un fallo del motor.
 * - Caja blanca (CB): ramas de error — un error sin ejecuciones.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mrpApi } from './mrpApi';

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...a: unknown[]) => mockGet(...a),
    post: (...a: unknown[]) => mockPost(...a),
  },
}));

describe('mrpApi', () => {
  beforeEach(() => {
    [mockGet, mockPost].forEach((m) => { m.mockReset(); m.mockResolvedValue({ data: { ok: true } }); });
  });

  it('listarSugerencias dado bloque y sede cuando consulta entonces pagina en el servidor por sede', async () => {
    await mrpApi.listarSugerencias(2, 120, '3');
    expect(mockGet).toHaveBeenCalledWith('/inventory/sugerencias-compra/', { params: { page: 2, page_size: 120, sede: '3' } });
  });

  it('listarRequerimientos dado todas las sedes cuando consulta entonces no envía sede', async () => {
    await mrpApi.listarRequerimientos(1, 60);
    expect(mockGet).toHaveBeenCalledWith('/inventory/requerimientos-material/', { params: { page: 1, page_size: 60 } });
  });

  it('ultimaEjecucion y necesidadesProduccion dado sede cuando consultan entonces filtran por sede', async () => {
    await mrpApi.ultimaEjecucion('4');
    await mrpApi.necesidadesProduccion('4');
    expect(mockGet).toHaveBeenCalledWith('/inventory/sugerencias-compra/ultima-ejecucion/', { params: { sede: '4' } });
    expect(mockGet).toHaveBeenCalledWith('/inventory/sugerencias-compra/necesidades-produccion/', { params: { sede: '4' } });
  });

  it('ejecutar dado alcance cuando calcula entonces envía todas, la sede o nada', async () => {
    await mrpApi.ejecutar({ todas: true });
    await mrpApi.ejecutar({ sede_id: 5 });
    await mrpApi.ejecutar({});
    expect(mockPost).toHaveBeenNthCalledWith(1, '/inventory/sugerencias-compra/ejecutar-mrp/', { todas: true });
    expect(mockPost).toHaveBeenNthCalledWith(2, '/inventory/sugerencias-compra/ejecutar-mrp/', { sede_id: 5 });
    expect(mockPost).toHaveBeenNthCalledWith(3, '/inventory/sugerencias-compra/ejecutar-mrp/', {});
  });

  it('ejecutar dado un fallo del motor cuando responde 500 con ejecuciones entonces las devuelve', async () => {
    const ejecuciones = [{ id: 1, estado: 'fallida', mensaje_error: 'Error interno' }];
    mockPost.mockRejectedValueOnce({ response: { status: 500, data: { ejecuciones } } });
    await expect(mrpApi.ejecutar({})).resolves.toEqual(ejecuciones);
  });

  it('ejecutar dado un error sin ejecuciones cuando falla entonces propaga el error', async () => {
    mockPost.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'Prohibido' } } });
    await expect(mrpApi.ejecutar({ sede_id: 9 })).rejects.toMatchObject({ response: { status: 403 } });
  });
});
