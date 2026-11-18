/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): respuesta paginada o lista / todos o solo activos / crear / actualizar.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { materialesSustratoApi } from './materialesSustratoApi';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...a: unknown[]) => mockGet(...a),
    post: (...a: unknown[]) => mockPost(...a),
    patch: (...a: unknown[]) => mockPatch(...a),
  },
}));

describe('materialesSustratoApi', () => {
  beforeEach(() => {
    [mockGet, mockPost, mockPatch].forEach((m) => { m.mockReset(); m.mockResolvedValue({ data: [] }); });
  });

  it('listar dado respuesta paginada o lista cuando consulta entonces devuelve el arreglo', async () => {
    mockGet.mockResolvedValueOnce({ data: { count: 1, results: [{ id: 1, clave: 'lino' }] } });
    await expect(materialesSustratoApi.listar()).resolves.toEqual([{ id: 1, clave: 'lino' }]);
    expect(mockGet).toHaveBeenCalledWith('/materiales-sustrato/', { params: {} });
    mockGet.mockResolvedValueOnce({ data: [{ id: 2, clave: 'seda' }] });
    await expect(materialesSustratoApi.listar()).resolves.toEqual([{ id: 2, clave: 'seda' }]);
  });

  it('listar dado solo activos cuando consulta entonces filtra por activo', async () => {
    await materialesSustratoApi.listar({ soloActivos: true });
    expect(mockGet).toHaveBeenCalledWith('/materiales-sustrato/', { params: { activo: 'true' } });
  });

  it('crear y actualizar dado un material cuando se llaman entonces usan el catálogo de la sede', async () => {
    await materialesSustratoApi.crear({ nombre: 'Lino' });
    expect(mockPost).toHaveBeenCalledWith('/materiales-sustrato/', { nombre: 'Lino' });
    await materialesSustratoApi.actualizar(4, { activo: false });
    expect(mockPatch).toHaveBeenCalledWith('/materiales-sustrato/4/', { activo: false });
  });
});
