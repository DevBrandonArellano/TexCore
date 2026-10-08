/**
 * ISTQB — Nivel: Componente (hook)
 * Técnica : partición de equivalencia (con y sin selección) y transición de estados
 *           (respuesta tardía de una selección anterior).
 * Cubre   : useStockDeProductoEnBodega — lotes de un producto en una bodega pedidos al
 *           servidor en vez de filtrar en memoria el stock de todas las bodegas.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

const listarStockMock = vi.fn();
vi.mock('../../lib/api/inventarioApi', () => ({
  inventarioApi: {
    listarStock: (...args: unknown[]) => listarStockMock(...args),
  },
}));

import { useStockDeProductoEnBodega } from './useStockDeProductoEnBodega';

const fila = (id: number, cantidad: string) => ({
  id, producto: 'Hilo', producto_id: 1, bodega: 'Central', bodega_id: 2,
  lote: `L-${id}`, lote_id: id, lote_codigo: `L-${id}`, cantidad,
});
const pagina = (results: unknown[]) => ({ count: results.length, next: null, previous: null, results });

describe('useStockDeProductoEnBodega', () => {
  beforeEach(() => {
    listarStockMock.mockReset();
  });

  it('dado producto o bodega sin elegir cuando monta entonces no consulta y devuelve vacio', () => {
    const { result } = renderHook(() => useStockDeProductoEnBodega('1', ''));
    expect(listarStockMock).not.toHaveBeenCalled();
    expect(result.current.lotes).toEqual([]);
  });

  it('dado producto y bodega cuando monta entonces pide sus lotes en una pagina de 500', async () => {
    listarStockMock.mockResolvedValue(pagina([fila(1, '10.000')]));
    const { result } = renderHook(() => useStockDeProductoEnBodega('1', '2'));

    await waitFor(() => expect(result.current.lotes).toHaveLength(1));
    expect(listarStockMock).toHaveBeenCalledWith(1, 500, { producto_id: '1', bodega_id: '2' });
    expect(result.current.cargando).toBe(false);
  });

  it('dado fila solo comprometida (cantidad 0) cuando llega entonces no la ofrece como lote', async () => {
    listarStockMock.mockResolvedValue(pagina([fila(1, '0.000'), fila(2, '5.000')]));
    const { result } = renderHook(() => useStockDeProductoEnBodega('1', '2'));

    await waitFor(() => expect(result.current.lotes.map(l => l.id)).toEqual([2]));
  });

  it('dado error del servidor cuando consulta entonces devuelve vacio', async () => {
    listarStockMock.mockRejectedValue(new Error('caido'));
    const { result } = renderHook(() => useStockDeProductoEnBodega('1', '2'));

    await waitFor(() => expect(result.current.cargando).toBe(false));
    expect(result.current.lotes).toEqual([]);
  });

  it('dado cambio de bodega cuando la respuesta anterior llega tarde entonces se descarta', async () => {
    let resolverVieja: (v: unknown) => void = () => {};
    listarStockMock
      .mockReturnValueOnce(new Promise(r => { resolverVieja = r; }))
      .mockResolvedValueOnce(pagina([fila(9, '3.000')]));
    const { result, rerender } = renderHook(({ bodega }) => useStockDeProductoEnBodega('1', bodega), {
      initialProps: { bodega: '2' },
    });

    rerender({ bodega: '3' });
    await waitFor(() => expect(result.current.lotes.map(l => l.id)).toEqual([9]));
    resolverVieja(pagina([fila(1, '10.000')]));
    await Promise.resolve();
    expect(result.current.lotes.map(l => l.id)).toEqual([9]);
  });
});
