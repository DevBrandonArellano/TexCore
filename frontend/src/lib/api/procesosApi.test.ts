import { describe, it, expect, vi, beforeEach } from 'vitest';
import { procesosApi } from './procesosApi';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...a: unknown[]) => mockGet(...a),
    post: (...a: unknown[]) => mockPost(...a),
    patch: (...a: unknown[]) => mockPatch(...a),
    delete: (...a: unknown[]) => mockDelete(...a),
  },
}));

describe('procesosApi', () => {
  beforeEach(() => {
    [mockGet, mockPost, mockPatch, mockDelete].forEach((m) => { m.mockReset(); m.mockResolvedValue({ data: [] }); });
  });

  it('listar dado respuesta paginada o lista cuando consulta entonces devuelve el arreglo', async () => {
    mockGet.mockResolvedValueOnce({ data: { count: 1, results: [{ id: 1, name: 'Tejido' }] } });
    await expect(procesosApi.listar()).resolves.toEqual([{ id: 1, name: 'Tejido' }]);
    expect(mockGet).toHaveBeenCalledWith('/process-steps/', { params: { page_size: 500 } });
    mockGet.mockResolvedValueOnce({ data: [{ id: 2, name: 'Teñido' }] });
    await expect(procesosApi.listar()).resolves.toEqual([{ id: 2, name: 'Teñido' }]);
  });

  it('crear, actualizar y eliminar cuando se llaman entonces usan el catálogo de procesos', async () => {
    await procesosApi.crear({ name: 'Teñido', description: '' });
    expect(mockPost).toHaveBeenCalledWith('/process-steps/', { name: 'Teñido', description: '' });
    await procesosApi.actualizar(3, { name: 'Teñido HT', description: 'Alta temperatura' });
    expect(mockPatch).toHaveBeenCalledWith('/process-steps/3/', { name: 'Teñido HT', description: 'Alta temperatura' });
    await procesosApi.eliminar(3);
    expect(mockDelete).toHaveBeenCalledWith('/process-steps/3/');
  });
});
