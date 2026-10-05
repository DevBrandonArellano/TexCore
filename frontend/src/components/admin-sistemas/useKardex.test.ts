import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useKardex, KARDEX_PAGE_SIZE } from './useKardex';

// RNF-03 · TEX-22: el kárdex pagina en servidor. Con bodega + producto usa
// /inventory/bodegas/{id}/kardex/ (saldo calculado por la base); si no, el
// listado /inventory/movimientos/. El export es el Excel del servidor.

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: any[]) => toastErrorMock(...args) },
}));

const mockHandleExport = vi.fn();
const mockUseReportesExport = vi.fn();
vi.mock('./useReportesExport', () => ({
  useReportesExport: (...args: any[]) => mockUseReportesExport(...args),
}));

const FILA_KARDEX = {
  id: 7, fecha: '2026-01-02T10:00:00Z', tipo_movimiento: 'VENTA',
  tipo_movimiento_display: 'Salida por Venta', documento_ref: 'F-1',
  cantidad: '4.000', entrada: '0.000', salida: '4.000', saldo: '96.000',
  descripcion_producto: 'Hilo Azul', codigo_producto: 'H-1',
  bodega_origen_nombre: 'Central', bodega_destino_nombre: null, usuario: 'ana',
};

const FILA_MOVIMIENTO = {
  id: 3, fecha: '2026-01-01T10:00:00Z', tipo_movimiento: 'COMPRA', cantidad: '10.000',
  producto: 2, producto_nombre: 'Hilo Azul (H-1)', bodega_origen: null, bodega_destino: 1,
  bodega_origen_nombre: null, bodega_destino_nombre: 'Central (Sede)', documento_ref: null,
};

function paginado(results: any[], count = results.length, extra: Record<string, any> = {}) {
  return { data: { count, next: null, previous: null, results, ...extra } };
}

function seleccionar(result: any, { bodega = 'all', producto = 'all', tipo = 'all', desde = '', hasta = '' } = {}) {
  act(() => {
    result.current.setSelectedBodega(bodega);
    result.current.setSelectedProducto(producto);
    result.current.setTipoOperacion(tipo);
    result.current.setFechaInicio(desde);
    result.current.setFechaFin(hasta);
  });
}

describe('useKardex', () => {
  beforeEach(() => {
    mockGet.mockReset();
    toastErrorMock.mockReset();
    mockHandleExport.mockReset();
    mockUseReportesExport.mockReset();
    mockUseReportesExport.mockReturnValue({ loading: {}, handleExport: mockHandleExport });
  });

  it('dado bodega y producto cuando consulta entonces pide el kardex paginado con saldo del servidor', async () => {
    mockGet.mockResolvedValue(paginado([FILA_KARDEX], 1, { saldo_inicial: '100.000' }));
    const { result } = renderHook(() => useKardex());
    seleccionar(result, { bodega: '1', producto: '2', tipo: 'salida', desde: '2026-01-01', hasta: '2026-01-31' });

    await act(async () => { await result.current.handleFetchKardex(); });

    expect(mockGet).toHaveBeenCalledWith('/inventory/bodegas/1/kardex/', {
      params: {
        producto_id: '2', tipo: 'salida', fecha_inicio: '2026-01-01', fecha_fin: '2026-01-31',
        page: 1, page_size: KARDEX_PAGE_SIZE,
      },
    });
  });

  it('dado respuesta del kardex cuando consulta entonces mapea la fila al formato de la tabla', async () => {
    mockGet.mockResolvedValue(paginado([FILA_KARDEX]));
    const { result } = renderHook(() => useKardex());
    seleccionar(result, { bodega: '1', producto: '2' });

    await act(async () => { await result.current.handleFetchKardex(); });

    const fila: any = result.current.paginatedData[0];
    expect(fila.producto).toBe('Hilo Azul');
    expect(fila.bodega_origen).toBe('Central');
    expect(fila.saldo_acumulado).toBe(96);
    expect(fila.esSalida).toBe(true);
    expect(fila.esEntrada).toBe(false);
  });

  it('dado sin producto cuando consulta entonces pide el listado de movimientos paginado sin saldo', async () => {
    mockGet.mockResolvedValue(paginado([FILA_MOVIMIENTO]));
    const { result } = renderHook(() => useKardex());
    seleccionar(result, { bodega: '1', tipo: 'entrada', desde: '2026-01-01', hasta: '2026-01-31' });

    await act(async () => { await result.current.handleFetchKardex(); });

    expect(mockGet).toHaveBeenCalledWith('/inventory/movimientos/', {
      params: {
        bodega_id: '1', tipo: 'entrada', fecha_desde: '2026-01-01', fecha_hasta: '2026-01-31',
        page: 1, page_size: KARDEX_PAGE_SIZE,
      },
    });
    const fila: any = result.current.paginatedData[0];
    expect(fila.producto).toBe('Hilo Azul (H-1)');
    expect(fila.bodega_destino).toBe('Central (Sede)');
    expect(fila.esEntrada).toBe(true); // entra a la bodega consultada
    expect(fila.saldo_acumulado).toBeUndefined();
  });

  it('dado ningun filtro cuando consulta entonces no envia filtros, solo la pagina', async () => {
    mockGet.mockResolvedValue(paginado([]));
    const { result } = renderHook(() => useKardex());

    await act(async () => { await result.current.handleFetchKardex(); });

    expect(mockGet).toHaveBeenCalledWith('/inventory/movimientos/', {
      params: { page: 1, page_size: KARDEX_PAGE_SIZE },
    });
  });

  it('dado count del servidor cuando consulta entonces calcula el total de paginas', async () => {
    mockGet.mockResolvedValue(paginado([FILA_MOVIMIENTO], KARDEX_PAGE_SIZE * 2 + 1));
    const { result } = renderHook(() => useKardex());

    await act(async () => { await result.current.handleFetchKardex(); });

    expect(result.current.totalPages).toBe(3);
    expect(result.current.totalCount).toBe(KARDEX_PAGE_SIZE * 2 + 1);
  });

  it('dado filtros cambiados despues de consultar cuando cambia de pagina entonces usa los filtros consultados', async () => {
    mockGet.mockResolvedValue(paginado([FILA_KARDEX], 100));
    const { result } = renderHook(() => useKardex());
    seleccionar(result, { bodega: '1', producto: '2' });
    await act(async () => { await result.current.handleFetchKardex(); });

    seleccionar(result, { bodega: '9', producto: '9' }); // editado en el formulario, sin consultar
    await act(async () => { await result.current.setCurrentPage(2); });

    expect(mockGet).toHaveBeenLastCalledWith('/inventory/bodegas/1/kardex/', {
      params: { producto_id: '2', page: 2, page_size: KARDEX_PAGE_SIZE },
    });
    expect(result.current.currentPage).toBe(2);
  });

  it('dado sin consulta previa cuando cambia de pagina entonces no pide nada', async () => {
    const { result } = renderHook(() => useKardex());
    await act(async () => { await result.current.setCurrentPage(2); });
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado pagina 3 consultada cuando recarga entonces vuelve a pedir la pagina 3', async () => {
    mockGet.mockResolvedValue(paginado([FILA_KARDEX], 100));
    const { result } = renderHook(() => useKardex());
    await act(async () => { await result.current.handleFetchKardex(); });
    await act(async () => { await result.current.setCurrentPage(3); });

    await act(async () => { await result.current.recargarPagina(); });

    expect(mockGet).toHaveBeenLastCalledWith('/inventory/movimientos/', {
      params: { page: 3, page_size: KARDEX_PAGE_SIZE },
    });
  });

  it('dado un error de la API cuando consulta entonces muestra un toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => useKardex());

    await act(async () => { await result.current.handleFetchKardex(); });
    expect(toastErrorMock).toHaveBeenCalledWith('Error al consultar movimientos.');
  });

  it('dado limpiar filtros cuando se activa entonces resetea filtros, resultados y consulta activa', async () => {
    mockGet.mockResolvedValue(paginado([FILA_MOVIMIENTO], 5));
    const { result } = renderHook(() => useKardex());
    seleccionar(result, { bodega: '1' });
    await act(async () => { await result.current.handleFetchKardex(); });

    act(() => { result.current.handleClearFilters(); });

    expect(result.current.selectedBodega).toBe('all');
    expect(result.current.kardexData).toEqual([]);
    expect(result.current.totalCount).toBe(0);
    mockGet.mockClear();
    await act(async () => { await result.current.setCurrentPage(2); });
    expect(mockGet).not.toHaveBeenCalled();
  });

  // --- Exportación: Excel generado en el servidor (TEX-22 CA-2) ---
  it('dado sin consulta cuando exporta entonces pide consultar primero y no exporta', async () => {
    const { result } = renderHook(() => useKardex());
    await act(async () => { await result.current.exportarExcel(); });
    expect(toastErrorMock).toHaveBeenCalledWith('Consulte el kárdex antes de exportar.');
    expect(mockHandleExport).not.toHaveBeenCalled();
  });

  it('dado consulta sin bodega cuando exporta entonces pide seleccionar una bodega', async () => {
    mockGet.mockResolvedValue(paginado([FILA_MOVIMIENTO]));
    const { result } = renderHook(() => useKardex());
    await act(async () => { await result.current.handleFetchKardex(); });

    await act(async () => { await result.current.exportarExcel(); });

    expect(toastErrorMock).toHaveBeenCalledWith('Seleccione una bodega para exportar el kárdex.');
    expect(mockHandleExport).not.toHaveBeenCalled();
  });

  it('dado consulta con bodega y producto cuando exporta entonces exporta el excel con los filtros consultados', async () => {
    mockGet.mockResolvedValue(paginado([FILA_KARDEX]));
    const { result } = renderHook(() => useKardex());
    seleccionar(result, { bodega: '1', producto: '2', tipo: 'salida', desde: '2026-01-01', hasta: '2026-01-31' });
    await act(async () => { await result.current.handleFetchKardex(); });

    await act(async () => { await result.current.exportarExcel(); });

    expect(mockUseReportesExport).toHaveBeenLastCalledWith('1');
    expect(mockHandleExport).toHaveBeenCalledWith('kardex', {
      producto_id: '2', tipo: 'salida', fecha_inicio: '2026-01-01', fecha_fin: '2026-01-31',
    });
  });

  it('dado consulta de bodega sin producto cuando exporta entonces exporta los movimientos de toda la bodega', async () => {
    mockGet.mockResolvedValue(paginado([FILA_MOVIMIENTO]));
    const { result } = renderHook(() => useKardex());
    seleccionar(result, { bodega: '1' });
    await act(async () => { await result.current.handleFetchKardex(); });

    await act(async () => { await result.current.exportarExcel(); });

    expect(mockHandleExport).toHaveBeenCalledWith('kardex', {});
  });
});
