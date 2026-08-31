import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useReportesExport } from './useReportesExport';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const { mockToast } = vi.hoisted(() => ({
  mockToast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));
vi.mock('sonner', () => ({ toast: mockToast }));

const mockDownloadBlob = vi.fn();
vi.mock('../../lib/downloadBlob', () => ({
  downloadBlob: (...args: any[]) => mockDownloadBlob(...args),
}));

describe('useReportesExport', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockDownloadBlob.mockReset();
    mockToast.success.mockReset();
    mockToast.error.mockReset();
    mockToast.warning.mockReset();
  });

  it('dado reporte que requiere bodega sin bodega seleccionada cuando exporta entonces no llama al backend', async () => {
    const { result } = renderHook(() => useReportesExport(''));
    await act(async () => { await result.current.handleExport('kardex'); });
    expect(mockToast.error).toHaveBeenCalledWith('Debe seleccionar una bodega para este reporte.');
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado respuesta con datos reales cuando exporta entonces descarga el archivo y muestra exito', async () => {
    mockGet.mockResolvedValue({ data: new Blob(['x']), headers: {} });
    const { result } = renderHook(() => useReportesExport('1'));
    await act(async () => { await result.current.handleExport('kardex'); });

    expect(mockGet).toHaveBeenCalledWith('/reporting/export/kardex', {
      params: { bodega_id: '1' },
      responseType: 'blob',
    });
    expect(mockDownloadBlob).toHaveBeenCalled();
    expect(mockToast.success).toHaveBeenCalledWith('Reporte generado exitosamente.');
    expect(mockToast.warning).not.toHaveBeenCalled();
  });

  it('dado respuesta con header x-report-empty cuando exporta entonces descarga el archivo pero muestra advertencia en vez de exito', async () => {
    mockGet.mockResolvedValue({ data: new Blob(['x']), headers: { 'x-report-empty': 'true' } });
    const { result } = renderHook(() => useReportesExport('1'));
    await act(async () => { await result.current.handleExport('kardex'); });

    expect(mockDownloadBlob).toHaveBeenCalled();
    expect(mockToast.warning).toHaveBeenCalledWith('El reporte no tiene datos para los filtros seleccionados.');
    expect(mockToast.success).not.toHaveBeenCalled();
  });

  it('dado error 404 cuando exporta entonces muestra mensaje de sin datos', async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } });
    const { result } = renderHook(() => useReportesExport('1'));
    await act(async () => { await result.current.handleExport('kardex'); });
    expect(mockToast.error).toHaveBeenCalledWith('No se encontraron datos para los filtros seleccionados.');
  });

  it('dado error 403 cuando exporta entonces muestra mensaje de permisos', async () => {
    mockGet.mockRejectedValue({ response: { status: 403 } });
    const { result } = renderHook(() => useReportesExport('1'));
    await act(async () => { await result.current.handleExport('kardex'); });
    expect(mockToast.error).toHaveBeenCalledWith('No tiene permisos para acceder a este reporte o bodega.');
  });

  it('dado error generico cuando exporta entonces muestra mensaje generico', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => useReportesExport('1'));
    await act(async () => { await result.current.handleExport('kardex'); });
    expect(mockToast.error).toHaveBeenCalledWith('Error al generar el reporte. Intente de nuevo.');
  });

  it('dado reporte sin requerir bodega cuando exporta sin bodega seleccionada entonces llama al backend', async () => {
    mockGet.mockResolvedValue({ data: new Blob(['x']), headers: {} });
    const { result } = renderHook(() => useReportesExport(''));
    await act(async () => { await result.current.handleExport('productos'); });
    expect(mockGet).toHaveBeenCalledWith('/reporting/export/productos', {
      params: {},
      responseType: 'blob',
    });
  });
});
