import { describe, it, expect, vi, beforeEach } from 'vitest';
import { inventarioApi } from './inventarioApi';

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock('../axios', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

const RECEPCION = {
  proveedor: 3, producto: 4, lote_proveedor: 'LP-1', cantidad_kg: '100.000', costo_unitario: '2.500',
  bodega_recepcion: 5, fecha_recepcion: '2026-10-01',
};

describe('inventarioApi', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockGet.mockResolvedValue({ data: { ok: true } });
    mockPost.mockResolvedValue({ data: { id: 9 } });
  });

  it('listarMateriaPrima dado bloque y filtros cuando consulta entonces envía página, tamaño y filtros', async () => {
    await inventarioApi.listarMateriaPrima(2, 120, { proveedor: 3, disponibles: true });
    expect(mockGet).toHaveBeenCalledWith('/materia-prima/', {
      params: { proveedor: 3, disponibles: 'true', page: 2, page_size: 120 },
    });
  });

  it('listarMateriaPrima dado disponibles en falso cuando consulta entonces no envía el filtro', async () => {
    await inventarioApi.listarMateriaPrima(1, 30, { disponibles: false });
    expect(mockGet.mock.calls[0][1].params).toEqual({ page: 1, page_size: 30 });
  });

  it('registrarEntradaMateriaPrima dado datos sin certificado cuando envía entonces usa JSON', async () => {
    await expect(inventarioApi.registrarEntradaMateriaPrima({ ...RECEPCION, pais: 'Perú' }))
      .resolves.toEqual({ id: 9 });
    expect(mockPost).toHaveBeenCalledWith('/materia-prima/registrar-entrada/', { ...RECEPCION, pais: 'Perú' });
  });

  it('registrarEntradaMateriaPrima dado certificado cuando envía entonces usa multipart con el archivo', async () => {
    const archivo = new File(['pdf'], 'cert.pdf', { type: 'application/pdf' });
    await inventarioApi.registrarEntradaMateriaPrima({ ...RECEPCION, certificado_calidad: archivo });
    const [url, cuerpo] = mockPost.mock.calls[0];
    expect(url).toBe('/materia-prima/registrar-entrada/');
    expect(cuerpo).toBeInstanceOf(FormData);
    expect((cuerpo as FormData).get('certificado_calidad')).toBe(archivo);
    expect((cuerpo as FormData).get('lote_proveedor')).toBe('LP-1');
  });

  it('registrarEntradaMateriaPrima dado certificado y campos opcionales vacíos cuando envía entonces los omite', async () => {
    const archivo = new File(['pdf'], 'cert.pdf', { type: 'application/pdf' });
    await inventarioApi.registrarEntradaMateriaPrima({ ...RECEPCION, pais: undefined, certificado_calidad: archivo });
    const cuerpo = mockPost.mock.calls[0][1] as FormData;
    expect(cuerpo.has('pais')).toBe(false);
    expect(cuerpo.get('cantidad_kg')).toBe('100.000');
  });

  it('stockAFecha dado producto, fecha y bodega cuando consulta entonces usa retro-kardex', async () => {
    await inventarioApi.stockAFecha({ producto_id: 4, fecha_corte: '2026-09-30', bodega_id: 5 });
    expect(mockGet).toHaveBeenCalledWith('/inventory/retro-kardex/', {
      params: { producto_id: 4, fecha_corte: '2026-09-30', bodega_id: 5 },
    });
  });
});
