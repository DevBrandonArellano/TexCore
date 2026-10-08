import { describe, it, expect, vi, beforeEach } from 'vitest';

const getMock = vi.fn();
const putMock = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...args: unknown[]) => getMock(...args),
    put: (...args: unknown[]) => putMock(...args),
  },
}));

import { configuracionEmpaqueApi } from './configuracionEmpaqueApi';

describe('configuracionEmpaqueApi', () => {
  beforeEach(() => {
    getMock.mockReset().mockResolvedValue({ data: { sede_id: 1 } });
    putMock.mockReset().mockResolvedValue({ data: { sede_id: 1 } });
  });

  it('dado admin de sede sin sede elegida cuando obtiene entonces no envia sede_id', async () => {
    await configuracionEmpaqueApi.obtener();
    expect(getMock).toHaveBeenCalledWith('/configuracion-empaque/', {});
  });

  it('dado sede elegida cuando guarda entonces la envia como parametro', async () => {
    const cambio = { fundas_por_bano: 15, conos_por_funda: 15, justificacion: 'Ajuste anual de empaque' };
    await configuracionEmpaqueApi.guardar(cambio, '4');
    expect(putMock).toHaveBeenCalledWith('/configuracion-empaque/', cambio, { params: { sede_id: '4' } });
  });
});
