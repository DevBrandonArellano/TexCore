import { useState, useMemo } from 'react';

interface UsePaginationOptions {
  /** Página controlada externamente (ej. sincronizada con la URL). Si se omite, el hook maneja su propio estado. */
  page?: number;
  onPageChange?: (page: number) => void;
}

export function usePagination<T>(items: T[], itemsPerPage: number, options?: UsePaginationOptions) {
  const [internalPage, setInternalPage] = useState(1);
  const currentPage = options?.page ?? internalPage;
  const setCurrentPage = options?.onPageChange ?? setInternalPage;

  const totalPages = Math.max(1, Math.ceil(items.length / itemsPerPage));

  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return items.slice(start, start + itemsPerPage);
  }, [items, currentPage, itemsPerPage]);

  return { currentPage, setCurrentPage, totalPages, paginatedItems };
}
