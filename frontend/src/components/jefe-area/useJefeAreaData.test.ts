/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): profile nulo / respuestas planas (array) / respuestas paginadas
 *   ({results}) / fallo del OEE de una maquina / error de red al cargar el dashboard.
 * - Análisis de valores límite (BVA): productos sin stock minimo.
 * - Caja blanca (CB): ramas de error — error de red al cargar el dashboard; el panel se cierra
 *   antes de cada respuesta (no actualiza el estado ni avisa).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useJefeAreaData } from './useJefeAreaData';
import { parcial } from '../../testing/parcial';

// Se prueban ambas formas de respuesta DRF (paginada y plana) que normaliza toArray.

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: unknown[]) => toastErrorMock(...args) },
}));

const PROFILE = parcial<NonNullable<Parameters<typeof useJefeAreaData>[0]>>({ role: 'jefe_area', user: parcial({ id: 1, username: 'jefe1' }) });

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

  /** El GET de `url` queda pendiente hasta llamar al resolvedor devuelto. */
  function retenerUrl(url: string, respuesta: () => Promise<unknown>) {
    let soltar: () => void = () => {};
    const pendiente = new Promise<void>((r) => { soltar = r; });
    mockRespuestasPlanas();
    const base = mockGet.getMockImplementation()!;
    mockGet.mockImplementation((u: string) => (u.includes(url) ? pendiente.then(respuesta) : base(u)));
    return () => soltar();
  }

  it('dado el panel cerrado antes de las respuestas cuando llegan entonces no actualiza el estado', async () => {
    const soltar = retenerUrl('/kpi-area/', () => Promise.resolve({ data: KPI }));
    const { result, unmount } = renderHook(() => useJefeAreaData(PROFILE));
    unmount();
    soltar();
    await new Promise((r) => setTimeout(r, 0));
    expect(result.current.kpis).toBeNull();
    expect(mockGet.mock.calls.some(([u]) => String(u).includes('/oee/'))).toBe(false);
  });

  it('dado el panel cerrado antes de un error cuando falla entonces no avisa', async () => {
    const soltar = retenerUrl('/kpi-area/', () => Promise.reject(new Error('red')));
    const { unmount } = renderHook(() => useJefeAreaData(PROFILE));
    unmount();
    soltar();
    await new Promise((r) => setTimeout(r, 0));
    expect(toastErrorMock).not.toHaveBeenCalled();
  });
});

