import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Pagina } from '../types/lotes';
import { getApiErrorMessage } from '../lib/apiError';

/** Estrategia de obtención: trae el bloque `bloque` (base 1) de `tamanoBloque` filas. */
export type ObtenerBloque<T> = (bloque: number, tamanoBloque: number) => Promise<Pagina<T>>;

interface OpcionesPaginacionIncremental<T> {
  obtenerBloque: ObtenerBloque<T>;
  tamanoPagina?: number;
  paginasPorBloque?: number;
  /** Al cambiar (filtros, búsqueda) se vacía la caché y se vuelve a la página 1. */
  resetKey?: unknown;
  /** Mientras sea `false` no se pide nada (p. ej. un buscador antes de su primera búsqueda). */
  habilitado?: boolean;
}

/**
 * Paginación servida por bloques: una petición trae `paginasPorBloque` páginas
 * de `tamanoPagina` filas (por defecto 4 × 30) y la tabla las muestra de una en
 * una. Al entrar en la última página cargada se precarga el bloque siguiente;
 * saltar a una página lejana pide solo su bloque.
 *
 * Devuelve la misma interfaz que `usePagination` (paginación en memoria), así
 * una tabla cambia de fuente de datos sin reescribir sus controles.
 */
export function usePaginacionIncremental<T>({
  obtenerBloque,
  tamanoPagina = 30,
  paginasPorBloque = 4,
  resetKey,
  habilitado = true,
}: OpcionesPaginacionIncremental<T>) {
  const tamanoBloque = tamanoPagina * paginasPorBloque;
  const [bloques, setBloques] = useState<Record<number, T[]>>({});
  const [count, setCount] = useState<number | null>(null);
  const [pagina, setPagina] = useState(1);
  const [error, setError] = useState<string | null>(null);

  // La estrategia cambia de identidad en cada render del componente dueño; se
  // lee desde una ref para no reiniciar la caché por eso.
  const obtenerRef = useRef(obtenerBloque);
  obtenerRef.current = obtenerBloque;
  // Bloques pedidos y generación de la caché: una respuesta de una generación
  // anterior (llegó después de cambiar los filtros) se descarta.
  const pedidosRef = useRef(new Set<number>());
  const generacionRef = useRef(0);

  const cargarBloque = useCallback(
    (bloque: number) => {
      if (pedidosRef.current.has(bloque)) return;
      pedidosRef.current.add(bloque);
      const generacion = generacionRef.current;
      obtenerRef
        .current(bloque, tamanoBloque)
        .then((respuesta) => {
          if (generacion !== generacionRef.current) return;
          setBloques((previos) => ({ ...previos, [bloque]: respuesta.results }));
          setCount(respuesta.count);
          setError(null);
        })
        .catch((err) => {
          if (generacion !== generacionRef.current) return;
          pedidosRef.current.delete(bloque);
          setError(getApiErrorMessage(err, 'No se pudieron cargar los datos.'));
        });
    },
    [tamanoBloque],
  );

  const vaciarCache = useCallback(() => {
    generacionRef.current += 1;
    pedidosRef.current = new Set();
    setBloques({});
    setError(null);
  }, []);

  const reiniciar = useCallback(() => {
    vaciarCache();
    setCount(null);
    setPagina(1);
  }, [vaciarCache]);

  useEffect(() => {
    reiniciar();
  }, [resetKey, reiniciar]);

  const totalPages = count === null ? 1 : Math.max(1, Math.ceil(count / tamanoPagina));
  const currentPage = Math.min(Math.max(1, pagina), totalPages);
  const bloqueActual = Math.ceil(currentPage / paginasPorBloque);
  const esUltimaPaginaDelBloque = currentPage % paginasPorBloque === 0;
  const hayBloqueSiguiente = count !== null && bloqueActual * tamanoBloque < count;

  // Carga el bloque visible (inicial o salto) y precarga el siguiente en el borde.
  useEffect(() => {
    if (!habilitado) return;
    cargarBloque(bloqueActual);
    if (esUltimaPaginaDelBloque && hayBloqueSiguiente) cargarBloque(bloqueActual + 1);
  }, [habilitado, bloqueActual, esUltimaPaginaDelBloque, hayBloqueSiguiente, cargarBloque, bloques]);

  const paginatedItems = useMemo(() => {
    const filas = bloques[bloqueActual];
    if (!filas) return [];
    const inicio = ((currentPage - 1) % paginasPorBloque) * tamanoPagina;
    return filas.slice(inicio, inicio + tamanoPagina);
  }, [bloques, bloqueActual, currentPage, paginasPorBloque, tamanoPagina]);

  const setCurrentPage = useCallback(
    (siguiente: number | ((previa: number) => number)) => {
      setPagina((previa) => {
        const valor = typeof siguiente === 'function' ? siguiente(previa) : siguiente;
        return Math.min(Math.max(1, valor), totalPages);
      });
    },
    [totalPages],
  );

  // Tras una acción (rechazar, reetiquetar) se vuelve a pedir la página visible;
  // el total se conserva para que la página no se recorte mientras llega.
  const recargar = vaciarCache;

  return {
    currentPage,
    setCurrentPage,
    totalPages,
    paginatedItems,
    count: count ?? 0,
    cargando: habilitado && bloques[bloqueActual] === undefined && error === null,
    error,
    recargar,
  };
}
