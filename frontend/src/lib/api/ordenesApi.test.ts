import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ordenesApi } from './ordenesApi';

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

describe('ordenesApi', () => {
  beforeEach(() => {
    [mockGet, mockPost, mockPatch].forEach((m) => { m.mockReset(); m.mockResolvedValue({ data: { ok: true } }); });
  });

  it('completarDetalles dado asignación e inicio cuando envía entonces usa la acción del Jefe de Área', async () => {
    await expect(ordenesApi.completarDetalles(10, { maquina_asignada: 1, operario_asignado: 5, iniciar: true }))
      .resolves.toEqual({ ok: true });
    expect(mockPatch).toHaveBeenCalledWith('/ordenes-produccion/10/completar_detalles/', {
      maquina_asignada: 1, operario_asignado: 5, iniciar: true,
    });
  });

  it('calcularDosificacion dado litros cuando consulta entonces envía litros_bano a la orden', async () => {
    await ordenesApi.calcularDosificacion(7, 850);
    expect(mockPost).toHaveBeenCalledWith('/ordenes-produccion/7/calcular-dosificacion/', { litros_bano: 850 });
  });

  it('procesosDeMaquina dado máquina cuando consulta entonces usa su acción procesos', async () => {
    await ordenesApi.procesosDeMaquina(3);
    expect(mockGet).toHaveBeenCalledWith('/maquinas/3/procesos/');
  });

  it('transformaciones dado orden cuando consulta entonces trae todos sus registros', async () => {
    await ordenesApi.transformaciones(10);
    expect(mockGet).toHaveBeenCalledWith('/ordenes-produccion/10/transformaciones/');
  });
});

