import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useKardex } from './useKardex';
import type { Bodega, Movimiento } from '../../lib/types';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: any[]) => toastErrorMock(...args) },
}));

const mockDownloadBlob = vi.fn();
vi.mock('../../lib/downloadBlob', () => ({
  downloadBlob: (...args: any[]) => mockDownloadBlob(...args),
}));

const BODEGA: Bodega = { id: 1, nombre: 'Central', sede: 1 } as any;

const MOV: Movimiento = {
  id: 1, fecha: '2026-01-01T10:00:00Z', producto: 'Hilo', cantidad: 10,
  bodega_origen: 'Norte', bodega_destino: 'Central', tipo_movimiento: 'entrada',
  documento_ref: 'DOC-1',
} as any;

describe('useKardex', () => {
  beforeEach(() => {
    mockGet.mockReset();
    toastErrorMock.mockReset();
    mockDownloadBlob.mockReset();
  });

  it('dado todos los filtros llenos cuando consulta entonces envia todos los params al backend', async () => {
    mockGet.mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useKardex([BODEGA]));

    act(() => {
      result.current.setSelectedBodega('1');
      result.current.setSelectedProducto('2');
      result.current.setTipoOperacion('entrada');
      result.current.setFechaInicio('2026-01-01');
      result.current.setFechaFin('2026-01-31');
    });

    await act(async () => { await result.current.handleFetchKardex(); });

    expect(mockGet).toHaveBeenCalledWith('/inventory/movimientos/', {
      params: {
        bodega_id: '1', producto_id: '2', tipo: 'entrada',
        fecha_desde: '2026-01-01', fecha_hasta: '2026-01-31',
      },
    });
  });

  it('dado producto y bodega seleccionados con datos cuando consulta entonces calcula el saldo acumulado', async () => {
    mockGet.mockResolvedValue({ data: [MOV] });
    const { result } = renderHook(() => useKardex([BODEGA]));

    act(() => {
      result.current.setSelectedBodega('1');
      result.current.setSelectedProducto('2');
    });
    await act(async () => { await result.current.handleFetchKardex(); });

    expect((result.current.kardexData[0] as any).saldo_acumulado).toBeDefined();
  });

  it('dado error al consultar entonces muestra un toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => useKardex([BODEGA]));

    await act(async () => { await result.current.handleFetchKardex(); });
    expect(toastErrorMock).toHaveBeenCalledWith('Error al consultar movimientos.');
  });

  it('dado limpiar filtros cuando se activa entonces resetea todo el estado', () => {
    const { result } = renderHook(() => useKardex([BODEGA]));
    act(() => { result.current.setSelectedBodega('1'); });
    act(() => { result.current.handleClearFilters(); });
    expect(result.current.selectedBodega).toBe('all');
    expect(result.current.kardexData).toEqual([]);
  });

  it('dado sin datos cuando exporta a csv entonces muestra error y no genera el archivo', () => {
    const { result } = renderHook(() => useKardex([BODEGA]));
    act(() => { result.current.exportToCSV(); });
    expect(toastErrorMock).toHaveBeenCalledWith('No hay datos para exportar');
    expect(mockDownloadBlob).not.toHaveBeenCalled();
  });

  it('dado datos y producto/bodega seleccionados cuando exporta a csv entonces incluye la columna Saldo', async () => {
    mockGet.mockResolvedValue({ data: [MOV] });
    const { result } = renderHook(() => useKardex([BODEGA]));
    act(() => {
      result.current.setSelectedBodega('1');
      result.current.setSelectedProducto('2');
    });
    await act(async () => { await result.current.handleFetchKardex(); });

    act(() => { result.current.exportToCSV(); });
    expect(mockDownloadBlob).toHaveBeenCalled();
    const blob = mockDownloadBlob.mock.calls[0][0] as Blob;
    const text = await blob.text();
    expect(text).toContain('Saldo');
  });

  it('dado movimiento sin bodega origen/destino ni documento_ref cuando exporta a csv entonces usa guiones', async () => {
    const movIncompleto: any = { id: 2, fecha: '2026-01-01T10:00:00Z', producto: 'X', cantidad: 5, tipo_movimiento: 'salida' };
    mockGet.mockResolvedValue({ data: [movIncompleto] });
    const { result } = renderHook(() => useKardex([BODEGA]));
    await act(async () => { await result.current.handleFetchKardex(); });

    act(() => { result.current.exportToCSV(); });
    const blob = mockDownloadBlob.mock.calls[0][0] as Blob;
    const text = await blob.text();
    expect(text).toContain('-,-');
  });
});
