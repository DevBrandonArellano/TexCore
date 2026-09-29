import { describe, it, expect, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { usePaginacionIncremental } from './usePaginacionIncremental';
import type { Pagina } from '../types/lotes';

const TOTAL = 300; // 10 páginas de 30 → 3 bloques de 120 (el último parcial)

/** Backend simulado: filas 1..total, en bloques de `tamano`. */
function backend(total = TOTAL) {
  return vi.fn((bloque: number, tamano: number): Promise<Pagina<number>> => {
    const inicio = (bloque - 1) * tamano;
    const results = Array.from({ length: Math.max(0, Math.min(tamano, total - inicio)) }, (_, i) => inicio + i + 1);
    return Promise.resolve({ count: total, next: null, previous: null, results });
  });
}

function montar(obtenerBloque: ReturnType<typeof backend>, resetKey?: unknown) {
  return renderHook(({ key }) => usePaginacionIncremental<number>({ obtenerBloque, resetKey: key }), {
    initialProps: { key: resetKey },
  });
}

describe('usePaginacionIncremental', () => {
  it('dado montaje cuando carga entonces pide un solo bloque de 4 páginas de 30', async () => {
    const obtener = backend();
    const { result } = montar(obtener);
    await waitFor(() => expect(result.current.paginatedItems).toHaveLength(30));
    expect(obtener).toHaveBeenCalledTimes(1);
    expect(obtener).toHaveBeenCalledWith(1, 120);
    expect(result.current.totalPages).toBe(10);
    expect(result.current.count).toBe(300);
    expect(result.current.paginatedItems[0]).toBe(1);
  });

  it('dado bloque cargado cuando navega dentro de él entonces no vuelve a pedir', async () => {
    const obtener = backend();
    const { result } = montar(obtener);
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.setCurrentPage(3));
    expect(result.current.paginatedItems[0]).toBe(61);
    expect(obtener).toHaveBeenCalledTimes(1);
  });

  it('dado la última página del bloque cuando entra entonces precarga el bloque siguiente', async () => {
    const obtener = backend();
    const { result } = montar(obtener);
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.setCurrentPage(4));
    await waitFor(() => expect(obtener).toHaveBeenCalledWith(2, 120));
    act(() => result.current.setCurrentPage(5));
    expect(result.current.paginatedItems[0]).toBe(121);
    expect(result.current.cargando).toBe(false);
  });

  it('dado salto a una página lejana cuando navega entonces pide solo su bloque', async () => {
    const obtener = backend();
    const { result } = montar(obtener);
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.setCurrentPage(10));
    await waitFor(() => expect(result.current.paginatedItems[0]).toBe(271));
    expect(obtener.mock.calls.map(([b]) => b)).toEqual([1, 3]);
  });

  it('dado el último bloque cuando está en su última página entonces no precarga más allá del total', async () => {
    const obtener = backend(120);
    const { result } = montar(obtener);
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.setCurrentPage(4));
    await waitFor(() => expect(result.current.paginatedItems).toHaveLength(30));
    expect(obtener).toHaveBeenCalledTimes(1);
  });

  it('dado página fuera de rango cuando navega entonces se acota', async () => {
    const obtener = backend();
    const { result } = montar(obtener);
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.setCurrentPage((p) => p - 5));
    expect(result.current.currentPage).toBe(1);
    act(() => result.current.setCurrentPage(99));
    expect(result.current.currentPage).toBe(10);
  });

  it('dado cambio de resetKey cuando rerenderiza entonces vacía la caché y vuelve a la página 1', async () => {
    const obtener = backend();
    const { result, rerender } = montar(obtener, 'a');
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.setCurrentPage(2));
    rerender({ key: 'b' });
    expect(result.current.currentPage).toBe(1);
    await waitFor(() => expect(obtener).toHaveBeenCalledTimes(2));
    expect(obtener).toHaveBeenLastCalledWith(1, 120);
  });

  it('dado respuesta tardía de filtros anteriores cuando llega entonces se descarta', async () => {
    let resolverVieja: (p: Pagina<number>) => void = () => {};
    const obtener = vi
      .fn()
      .mockImplementationOnce(() => new Promise<Pagina<number>>((r) => { resolverVieja = r; }))
      .mockResolvedValue({ count: 1, next: null, previous: null, results: [42] });
    const { result, rerender } = renderHook(({ key }) => usePaginacionIncremental<number>({ obtenerBloque: obtener, resetKey: key }), {
      initialProps: { key: 'viejo' },
    });
    rerender({ key: 'nuevo' });
    await waitFor(() => expect(result.current.paginatedItems).toEqual([42]));
    act(() => resolverVieja({ count: 9, next: null, previous: null, results: [1, 2, 3] }));
    expect(result.current.paginatedItems).toEqual([42]);
    expect(result.current.count).toBe(1);
  });

  it('dado error sin respuesta cuando carga entonces expone el mensaje por defecto y deja de marcar carga', async () => {
    const obtener = vi.fn().mockRejectedValue(new Error('500'));
    const { result } = renderHook(() => usePaginacionIncremental<number>({ obtenerBloque: obtener }));
    await waitFor(() => expect(result.current.error).toBe('No se pudieron cargar los datos.'));
    expect(result.current.cargando).toBe(false);
  });

  it('dado 400 con error de campo cuando carga entonces expone el detalle del servidor', async () => {
    const obtener = vi.fn().mockRejectedValue({ response: { status: 400, data: { fecha_desde: ['Fecha inválida.'] } } });
    const { result } = renderHook(() => usePaginacionIncremental<number>({ obtenerBloque: obtener }));
    await waitFor(() => expect(result.current.error).toBe('fecha_desde: Fecha inválida.'));
  });

  it('dado habilitado en false cuando monta entonces no pide nada ni marca carga', async () => {
    const obtener = backend();
    const { result, rerender } = renderHook(({ on }) => usePaginacionIncremental<number>({ obtenerBloque: obtener, habilitado: on }), {
      initialProps: { on: false },
    });
    expect(result.current.cargando).toBe(false);
    expect(obtener).not.toHaveBeenCalled();
    rerender({ on: true });
    await waitFor(() => expect(obtener).toHaveBeenCalledWith(1, 120));
  });

  it('dado recargar cuando se invoca entonces vuelve a pedir la página visible sin perder el total', async () => {
    const obtener = backend();
    const { result } = montar(obtener);
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.setCurrentPage(6));
    await waitFor(() => expect(result.current.paginatedItems[0]).toBe(151));
    const llamadasAntes = obtener.mock.calls.length;
    act(() => result.current.recargar());
    expect(result.current.currentPage).toBe(6);
    await waitFor(() => expect(result.current.paginatedItems[0]).toBe(151));
    expect(obtener.mock.calls.slice(llamadasAntes).map(([b]) => b)).toEqual([2]);
  });
});
