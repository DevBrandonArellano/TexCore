import { useEffect, useState } from 'react';
import { inventarioApi } from '../../lib/api/inventarioApi';
import type { StockItem } from '../../types/inventario';

/** Tope de PaginacionAcotada: los lotes de un producto en una bodega caben en una página. */
const TAMANO_MAXIMO = 500;

/**
 * Lotes con existencias de un producto en una bodega, pedidos al servidor al elegir
 * ambos. Reemplaza filtrar en memoria el stock completo de todas las bodegas, que con
 * años de operación eran decenas de miles de filas (prueba de carga 2026-10-06).
 */
export function useStockDeProductoEnBodega(productoId: string, bodegaId: string) {
  const clave = productoId && bodegaId ? `${productoId}|${bodegaId}` : null;
  // La respuesta guarda la selección a la que pertenece: mientras no coincida con la
  // actual, se está cargando (y una respuesta tardía de otra selección no se muestra).
  const [respuesta, setRespuesta] = useState<{ clave: string; lotes: StockItem[] } | null>(null);

  useEffect(() => {
    if (!clave) return;
    let vigente = true;
    inventarioApi
      .listarStock(1, TAMANO_MAXIMO, { producto_id: productoId, bodega_id: bodegaId })
      .then((pagina) => pagina.results.filter((fila) => parseFloat(fila.cantidad) > 0))
      .catch((): StockItem[] => [])
      .then((lotes) => {
        if (vigente) setRespuesta({ clave, lotes });
      });
    return () => {
      vigente = false;
    };
  }, [clave, productoId, bodegaId]);

  const vigente = clave !== null && respuesta?.clave === clave;
  return {
    lotes: vigente ? respuesta.lotes : [],
    cargando: clave !== null && !vigente,
  };
}
