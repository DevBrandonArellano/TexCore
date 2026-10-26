/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): filtros completos / filtros vacíos / filtros / respuesta del servidor.
 * - Análisis de valores límite (BVA): filtros vacíos.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mantenimientoApi } from './mantenimientoApi';

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...a: unknown[]) => mockGet(...a),
    post: (...a: unknown[]) => mockPost(...a),
  },
}));

describe('mantenimientoApi', () => {
  beforeEach(() => {
    [mockGet, mockPost].forEach((m) => { m.mockReset(); m.mockResolvedValue({ data: { ok: true } }); });
  });

  it('historial dado filtros completos cuando consulta entonces los envía con la paginación', async () => {
    await mantenimientoApi.historial(
      { fecha_desde: '2026-09-14', fecha_hasta: '2026-10-14', maquina: 7, categoria: 'AVERIA', planificado: false },
      2,
      25,
    );

    expect(mockGet).toHaveBeenCalledWith('/paros-maquina/historial/', {
      params: {
        fecha_desde: '2026-09-14',
        fecha_hasta: '2026-10-14',
        maquina: 7,
        categoria: 'AVERIA',
        planificado: false,
        page: 2,
        page_size: 25,
      },
    });
  });

  it('historial dado filtros vacíos cuando consulta entonces no envía parámetros en blanco', async () => {
    await mantenimientoApi.historial({ fecha_desde: '2026-10-01', maquina: undefined, categoria: undefined });

    expect(mockGet).toHaveBeenCalledWith('/paros-maquina/historial/', {
      params: { fecha_desde: '2026-10-01', page: 1, page_size: 50 },
    });
  });

  it('imprimirHistorial dado filtros cuando imprime entonces pide el PDF como blob', async () => {
    await mantenimientoApi.imprimirHistorial({ fecha_desde: '2026-09-14', categoria: 'MANTENIMIENTO_PLANIFICADO' });

    expect(mockPost).toHaveBeenCalledWith(
      '/paros-maquina/imprimir-historial/',
      { fecha_desde: '2026-09-14', categoria: 'MANTENIMIENTO_PLANIFICADO' },
      { responseType: 'blob' },
    );
  });

  it('historial dado respuesta del servidor cuando resuelve entonces devuelve los datos tal cual', async () => {
    const datos = { rango: { fecha_desde: '2026-10-01', fecha_hasta: '2026-10-14' }, resumen: [], totales: {}, detalle: { results: [] } };
    mockGet.mockResolvedValue({ data: datos });

    await expect(mantenimientoApi.historial({})).resolves.toEqual(datos);
  });
});
