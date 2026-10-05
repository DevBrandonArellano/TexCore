import { describe, it, expect, vi, beforeEach } from 'vitest';
import { procesosTintoreriaApi } from './procesosTintoreriaApi';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockPut = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...a: unknown[]) => mockGet(...a),
    post: (...a: unknown[]) => mockPost(...a),
    patch: (...a: unknown[]) => mockPatch(...a),
    put: (...a: unknown[]) => mockPut(...a),
  },
}));

describe('procesosTintoreriaApi', () => {
  beforeEach(() => {
    [mockGet, mockPost, mockPatch, mockPut].forEach((m) => { m.mockReset(); m.mockResolvedValue({ data: [] }); });
  });

  it('listar dado respuesta paginada o lista cuando consulta entonces devuelve el arreglo', async () => {
    mockGet.mockResolvedValueOnce({ data: { count: 1, results: [{ id: 1, codigo: 'DESCRUDE' }] } });
    await expect(procesosTintoreriaApi.listar()).resolves.toEqual([{ id: 1, codigo: 'DESCRUDE' }]);
    expect(mockGet).toHaveBeenCalledWith('/procesos-tintoreria/', { params: {} });
    mockGet.mockResolvedValueOnce({ data: [{ id: 2, codigo: 'LAVADO' }] });
    await expect(procesosTintoreriaApi.listar()).resolves.toEqual([{ id: 2, codigo: 'LAVADO' }]);
  });

  it('listar dado solo activos cuando consulta entonces filtra por activo', async () => {
    await procesosTintoreriaApi.listar({ soloActivos: true });
    expect(mockGet).toHaveBeenCalledWith('/procesos-tintoreria/', { params: { activo: 'true' } });
  });

  it('crear y actualizar dado un proceso cuando se llaman entonces usan el catálogo de la sede', async () => {
    const datos = { codigo: 'DESCRUDE', nombre: 'Descrude', tipo: 'pre_tratamiento' as const, descripcion: '' };
    await procesosTintoreriaApi.crear(datos);
    expect(mockPost).toHaveBeenCalledWith('/procesos-tintoreria/', datos);
    await procesosTintoreriaApi.actualizar(4, { activo: false });
    expect(mockPatch).toHaveBeenCalledWith('/procesos-tintoreria/4/', { activo: false });
  });

  it('asignarAMaquina dado una lista de procesos cuando se llama entonces reemplaza los de la máquina', async () => {
    mockPut.mockResolvedValueOnce({ data: [{ id: 1, codigo: 'DESCRUDE' }] });
    await expect(procesosTintoreriaApi.asignarAMaquina(9, [1])).resolves.toEqual([{ id: 1, codigo: 'DESCRUDE' }]);
    expect(mockPut).toHaveBeenCalledWith('/maquinas/9/procesos/', { procesos: [1] });
  });
});
