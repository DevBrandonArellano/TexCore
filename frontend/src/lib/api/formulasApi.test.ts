import { describe, it, expect, vi, beforeEach } from 'vitest';
import { formulasApi } from './formulasApi';

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...a: unknown[]) => mockGet(...a),
    post: (...a: unknown[]) => mockPost(...a),
  },
}));

describe('formulasApi', () => {
  beforeEach(() => {
    [mockGet, mockPost].forEach((m) => { m.mockReset(); m.mockResolvedValue({ data: { ok: true } }); });
  });

  it('calcularDosificacion dado peso y litros cuando consulta entonces usa la fórmula guardada', async () => {
    await expect(formulasApi.calcularDosificacion(4, 120, 960)).resolves.toEqual({ ok: true });
    expect(mockPost).toHaveBeenCalledWith('/formula-colors/4/calcular-dosificacion/', { peso: 120, litros: 960 });
  });

  it('derivadas dado fórmula cuando consulta entonces usa su acción derivadas', async () => {
    await formulasApi.derivadas(4);
    expect(mockGet).toHaveBeenCalledWith('/formula-colors/4/derivadas/');
  });

  it('version dado número cuando consulta entonces trae la versión con su receta', async () => {
    await formulasApi.version(4, 2);
    expect(mockGet).toHaveBeenCalledWith('/formula-colors/4/versiones/2/');
  });
});
