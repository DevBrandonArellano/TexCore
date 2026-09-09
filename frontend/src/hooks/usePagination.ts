import { useState, useMemo, useEffect } from 'react';

interface UsePaginationOptions {
  /** Página controlada externamente (ej. sincronizada con la URL). Si se omite, el hook maneja su propio estado. */
  page?: number;
  onPageChange?: (page: number) => void;
  /**
   * Cuando este valor cambia entre renders (ej. un término de búsqueda o un
   * filtro), resetea la página a 1. Comparación por referencia/valor con
   * Object.is, igual que las dependencias de useEffect.
   */
  resetKey?: unknown;
}

export function usePagination<T>(items: T[], itemsPerPage: number, options?: UsePaginationOptions) {
  const [internalPage, setInternalPage] = useState(1);
  const rawPage = options?.page ?? internalPage;
  const setRawPage = options?.onPageChange ?? setInternalPage;

  const totalPages = Math.max(1, Math.ceil(items.length / itemsPerPage));
  // Acota siempre — controlado o interno — para que un cambio de datos/filtro
  // que reduzca totalPages nunca deje currentPage apuntando a una página vacía.
  const currentPage = Math.min(Math.max(1, rawPage), totalPages);

  useEffect(() => {
    if (options?.resetKey !== undefined) {
      setRawPage(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options?.resetKey]);

  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return items.slice(start, start + itemsPerPage);
  }, [items, currentPage, itemsPerPage]);

  const setCurrentPage = (next: number | ((prev: number) => number)) => {
    const value = typeof next === 'function' ? (next as (prev: number) => number)(currentPage) : next;
    setRawPage(Math.min(Math.max(1, value), totalPages));
  };

  return { currentPage, setCurrentPage, totalPages, paginatedItems };
}
