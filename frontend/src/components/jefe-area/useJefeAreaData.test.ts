import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useJefeAreaData } from './useJefeAreaData';

// Se prueban ambas formas de respuesta DRF (paginada y plana) que normaliza toArray.

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: any[]) => toastErrorMock(...args) },
}));

const PROFILE = { role: 'jefe_area', user: { id: 1, username: 'jefe1' } } as any;

const KPI = { area: 'Tintura' };
const MAQUINA = { id: 1, capacidad_maxima: 100, nombre: 'M1' };
// La carga del día la calcula el servidor (fecha local): /maquinas/{id}/eficiencia/.
const EFICIENCIA = { maquina: 'M1', capacidad_maxima: 100, produccion_hoy: 50, eficiencia_porcentaje: 50 };
const PRODUCTO_BAJO_STOCK = { id: 1, tipo: 'hilo', stock_minimo: 5 };

function mockRespuestasPlanas() {
  mockGet.mockImplementation((url: string) => {
    if (url === '/kpi-area/') return Promise.resolve({ data: KPI });
    if (url === '/maquinas/') return Promise.resolve({ data: [MAQUINA] });
    if (url === '/ordenes-produccion/') return Promise.resolve({ data: [] });
    if (url === '/users/') return Promise.resolve({ data: [] });
    if (url === '/productos/') return Promise.resolve({ data: [PRODUCTO_BAJO_STOCK] });
    if (url === '/lineas-produccion/') return Promise.resolve({ data: [] });
    if (url.includes('/oee/')) return Promise.resolve({ data: { oee: 0.8 } });
    if (url.includes('/eficiencia/')) return Promise.resolve({ data: EFICIENCIA });
    return Promise.resolve({ data: [] });
  });
}

function mockRespuestasPaginadas() {
  mockGet.mockImplementation((url: string) => {
    if (url === '/kpi-area/') return Promise.resolve({ data: KPI });
    if (url === '/maquinas/') return Promise.resolve({ data: { results: [MAQUINA] } });
    if (url === '/ordenes-produccion/') return Promise.resolve({ data: { results: [] } });
    if (url === '/users/') return Promise.resolve({ data: { results: [] } });
    if (url === '/productos/') return Promise.resolve({ data: { results: [PRODUCTO_BAJO_STOCK] } });
    if (url === '/lineas-produccion/') return Promise.resolve({ data: { results: [] } });
    if (url.includes('/oee/')) return Promise.resolve({ data: { oee: 0.8 } });
    if (url.includes('/eficiencia/')) return Promise.resolve({ data: EFICIENCIA });
    return Promise.resolve({ data: { results: [] } });
  });
}

describe('useJefeAreaData', () => {
  beforeEach(() => {
    mockGet.mockReset();
    toastErrorMock.mockReset();
  });

  it('dado profile nulo cuando monta entonces no consulta el backend', () => {
    renderHook(() => useJefeAreaData(null));
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado respuestas planas (array) cuando carga entonces normaliza maquinas y toma la carga del servidor', async () => {
    mockRespuestasPlanas();
    const { result } = renderHook(() => useJefeAreaData(PROFILE));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.maquinas).toEqual([MAQUINA]);
    expect(result.current.kpis).toEqual(KPI);
    expect(result.current.alertas).toHaveLength(1);
    expect(result.current.maquinasCarga[1]).toBe(50);
  });

  it('dado respuestas paginadas ({results}) cuando carga entonces normaliza igual que con arrays', async () => {
    mockRespuestasPaginadas();
    const { result } = renderHook(() => useJefeAreaData(PROFILE));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.maquinas).toEqual([MAQUINA]);
    expect(result.current.alertas).toHaveLength(1);
    expect(result.current.maquinasCarga[1]).toBe(50);
  });

  it('dado fallo del OEE de una maquina cuando carga entonces omite esa maquina sin romper el resto', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/kpi-area/') return Promise.resolve({ data: KPI });
      if (url === '/maquinas/') return Promise.resolve({ data: [MAQUINA] });
        if (url === '/productos/') return Promise.resolve({ data: [] });
      if (url.includes('/oee/')) return Promise.reject(new Error('oee no disponible'));
      return Promise.resolve({ data: [] });
    });
    const { result } = renderHook(() => useJefeAreaData(PROFILE));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.maquinasOee).toEqual({});
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it('dado error de red al cargar el dashboard cuando falla Promise.all entonces notifica y deja de cargar', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => useJefeAreaData(PROFILE));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar los datos del panel.');
  });

  it('dado eficiencia mayor al 100% cuando carga entonces la carga se acota a 100', async () => {
    mockRespuestasPlanas();
    const base = mockGet.getMockImplementation()!;
    mockGet.mockImplementation((url: string) =>
      url.includes('/eficiencia/') ? Promise.resolve({ data: { ...EFICIENCIA, eficiencia_porcentaje: 137.4 } }) : base(url));
    const { result } = renderHook(() => useJefeAreaData(PROFILE));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.maquinasCarga[1]).toBe(100);
  });

  it('dado fallo de eficiencia de una maquina cuando carga entonces esa maquina queda sin carga', async () => {
    mockRespuestasPlanas();
    const base = mockGet.getMockImplementation()!;
    mockGet.mockImplementation((url: string) =>
      url.includes('/eficiencia/') ? Promise.reject(new Error('x')) : base(url));
    const { result } = renderHook(() => useJefeAreaData(PROFILE));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.maquinasCarga).toEqual({});
  });

  it('dado carga del panel cuando consulta entonces ya no pide el listado completo de lotes', async () => {
    mockRespuestasPlanas();
    renderHook(() => useJefeAreaData(PROFILE));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/maquinas/1/eficiencia/'));
    expect(mockGet).not.toHaveBeenCalledWith('/lotes-produccion/');
  });

  it('dado productos sin stock minimo cuando carga entonces no los incluye en alertas', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/kpi-area/') return Promise.resolve({ data: KPI });
      if (url === '/maquinas/') return Promise.resolve({ data: [] });
      if (url === '/productos/') return Promise.resolve({
        data: [{ id: 1, tipo: 'hilo', stock_minimo: 0 }, { id: 2, tipo: 'tela', stock_minimo: 5 }],
      });
      return Promise.resolve({ data: [] });
    });
    const { result } = renderHook(() => useJefeAreaData(PROFILE));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.alertas).toHaveLength(0);
  });
});
