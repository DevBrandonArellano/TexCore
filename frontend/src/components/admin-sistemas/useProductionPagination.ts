import { useState, useEffect } from 'react';
import { usePagination } from '../../hooks/usePagination';
import type { OrdenProduccion } from '../../lib/types';

const ITEMS_PER_PAGE = 20;

export function useProductionPagination(sedeOrdenes: OrdenProduccion[], selectedSedeId: string) {
  // Reset a página 1 cuando cambia la sede o el tamaño de la lista, con clamp
  // defensivo por si currentPage queda temporalmente fuera de rango.
  const [rawPage, setRawPage] = useState(1);
  useEffect(() => { setRawPage(1); }, [selectedSedeId, sedeOrdenes.length]);
  const totalPagesRaw = Math.max(1, Math.ceil(sedeOrdenes.length / ITEMS_PER_PAGE));
  const safePage = Math.min(Math.max(1, rawPage), totalPagesRaw);

  const { currentPage, setCurrentPage, totalPages, paginatedItems: paginatedSedeOrdenes } = usePagination(sedeOrdenes, ITEMS_PER_PAGE, {
    page: safePage,
    onPageChange: setRawPage,
  });

  return { currentPage, setCurrentPage, totalPages, paginatedSedeOrdenes };
}
