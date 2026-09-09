import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePagination } from './usePagination';

// Primer test directo del hook (antes solo se ejercitaba indirectamente vía
// consumidores). Cubre el clamp interno y el resetKey, que son la razón por
// la que cada consumidor duplicaba un wrapper externo de reset+clamp.

describe('usePagination', () => {
  it('dado modo interno cuando pagina entonces retorna la porcion correcta', () => {
    const items = Array.from({ length: 25 }, (_, i) => i);
    const { result } = renderHook(() => usePagination(items, 10));

    expect(result.current.currentPage).toBe(1);
    expect(result.current.totalPages).toBe(3);
    expect(result.current.paginatedItems).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);

    act(() => result.current.setCurrentPage(2));
    expect(result.current.currentPage).toBe(2);
  });

  it('dado lista vacia cuando calcula totalPages entonces retorna minimo 1', () => {
    const { result } = renderHook(() => usePagination([], 10));
    expect(result.current.totalPages).toBe(1);
    expect(result.current.paginatedItems).toEqual([]);
  });

  it('dado modo controlado cuando cambia la pagina entonces usa page/onPageChange externos', () => {
    let externalPage = 1;
    const onPageChange = (p: number) => { externalPage = p; };
    const items = Array.from({ length: 15 }, (_, i) => i);

    const { result, rerender } = renderHook(
      ({ page }) => usePagination(items, 10, { page, onPageChange }),
      { initialProps: { page: externalPage } },
    );

    act(() => result.current.setCurrentPage(2));
    expect(externalPage).toBe(2);

    rerender({ page: externalPage });
    expect(result.current.currentPage).toBe(2);
    expect(result.current.paginatedItems).toEqual([10, 11, 12, 13, 14]);
  });

  it('dado currentPage fuera de rango cuando los items encogen entonces lo acota a totalPages', () => {
    const { result, rerender } = renderHook(
      ({ items }) => usePagination(items, 10),
      { initialProps: { items: Array.from({ length: 25 }, (_, i) => i) } },
    );

    act(() => result.current.setCurrentPage(3)); // página 3 de 3
    expect(result.current.currentPage).toBe(3);

    rerender({ items: Array.from({ length: 5 }, (_, i) => i) }); // ahora solo 1 página
    expect(result.current.totalPages).toBe(1);
    expect(result.current.currentPage).toBe(1);
    expect(result.current.paginatedItems).toEqual([0, 1, 2, 3, 4]);
  });

  it('dado resetKey cambiando cuando rerenderiza entonces vuelve a la pagina 1', () => {
    const items = Array.from({ length: 25 }, (_, i) => i);
    const { result, rerender } = renderHook(
      ({ resetKey }) => usePagination(items, 10, { resetKey }),
      { initialProps: { resetKey: 'a' } },
    );

    act(() => result.current.setCurrentPage(2));
    expect(result.current.currentPage).toBe(2);

    rerender({ resetKey: 'b' });
    expect(result.current.currentPage).toBe(1);
  });

  it('dado resetKey sin cambiar cuando rerenderiza entonces no toca la pagina actual', () => {
    const items = Array.from({ length: 25 }, (_, i) => i);
    const { result, rerender } = renderHook(
      ({ resetKey }) => usePagination(items, 10, { resetKey }),
      { initialProps: { resetKey: 'a' } },
    );

    act(() => result.current.setCurrentPage(2));
    rerender({ resetKey: 'a' });
    expect(result.current.currentPage).toBe(2);
  });

  it('dado setCurrentPage con updater funcional cuando avanza entonces lo acota entre 1 y totalPages', () => {
    const items = Array.from({ length: 15 }, (_, i) => i);
    const { result } = renderHook(() => usePagination(items, 10));

    act(() => result.current.setCurrentPage((p) => p + 1));
    expect(result.current.currentPage).toBe(2);

    act(() => result.current.setCurrentPage((p) => p + 1)); // intenta ir a 3, totalPages=2
    expect(result.current.currentPage).toBe(2);

    act(() => result.current.setCurrentPage((p) => p - 5)); // intenta ir a negativo
    expect(result.current.currentPage).toBe(1);
  });
});
