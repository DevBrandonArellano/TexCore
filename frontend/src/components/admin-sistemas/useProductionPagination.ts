import { usePagination } from '../../hooks/usePagination';
import type { OrdenProduccion } from '../../lib/types';

const ITEMS_PER_PAGE = 20;

export function useProductionPagination(sedeOrdenes: OrdenProduccion[], selectedSedeId: string) {
  // Resetea a página 1 cuando cambia la sede o el tamaño de la lista; el hook
  // clampa internamente si currentPage queda fuera de rango.
  const { currentPage, setCurrentPage, totalPages, paginatedItems: paginatedSedeOrdenes } = usePagination(sedeOrdenes, ITEMS_PER_PAGE, {
    resetKey: `${selectedSedeId}:${sedeOrdenes.length}`,
  });

  return { currentPage, setCurrentPage, totalPages, paginatedSedeOrdenes };
}
