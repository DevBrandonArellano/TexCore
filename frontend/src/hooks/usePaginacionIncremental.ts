import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
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

/** Bloques recibidos de una generación de la caché (cambia al filtrar o recargar). */
interface Cache<T> {
  generacion: number;
  bloques: Record<number, T[]>;
  count: number | null;
  error: string | null;
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
  const [cache, setCache] = useState<Cache<T>>({ generacion: 0, bloques: {}, count: null, error: null });
  const [pagina, setPagina] = useState(1);
  const { generacion, bloques, count, error } = cache;

  // Al cambiar los filtros se vacía la caché y se vuelve a la página 1. Se ajusta
  // durante el render (patrón de React para «estado que depende de una prop»), sin
  // un efecto que pinte primero la página con los filtros viejos.
  const [resetKeyVigente, setResetKeyVigente] = useState(resetKey);
  if (!Object.is(resetKeyVigente, resetKey)) {
    setResetKeyVigente(resetKey);
    setCache((previa) => ({ generacion: previa.generacion + 1, bloques: {}, count: null, error: null }));
    setPagina(1);
  }

  // La estrategia cambia de identidad en cada render del componente dueño; se
  // lee desde una ref (actualizada antes de los efectos) para no reiniciar la caché por eso.
  const obtenerRef = useRef(obtenerBloque);
  useLayoutEffect(() => {
    obtenerRef.current = obtenerBloque;
  });
  // Bloques ya pedidos en la generación actual (evita pedir dos veces el mismo).
  const pedidosRef = useRef({ generacion: 0, bloques: new Set<number>() });

  // Una respuesta de otra generación (llegó después de filtrar o recargar) se descarta.
  const cargarBloque = useCallback(
    (bloque: number, generacionPedida: number) => {
      if (pedidosRef.current.generacion !== generacionPedida) {
        pedidosRef.current = { generacion: generacionPedida, bloques: new Set() };
      }
      const pedidos = pedidosRef.current.bloques;
      if (pedidos.has(bloque)) return;
      pedidos.add(bloque);
      obtenerRef
        .current(bloque, tamanoBloque)
        .then((respuesta) => {
          setCache((previa) =>
            previa.generacion !== generacionPedida
              ? previa
              : { ...previa, bloques: { ...previa.bloques, [bloque]: respuesta.results }, count: respuesta.count, error: null },
          );
        })
        .catch((err) => {
          pedidos.delete(bloque);
          setCache((previa) =>
            previa.generacion !== generacionPedida
              ? previa
              : { ...previa, error: getApiErrorMessage(err, 'No se pudieron cargar los datos.') },
          );
        });
    },
    [tamanoBloque],
  );

  const totalPages = count === null ? 1 : Math.max(1, Math.ceil(count / tamanoPagina));
  const currentPage = Math.min(Math.max(1, pagina), totalPages);
  const bloqueActual = Math.ceil(currentPage / paginasPorBloque);
  const esUltimaPaginaDelBloque = currentPage % paginasPorBloque === 0;
  const hayBloqueSiguiente = count !== null && bloqueActual * tamanoBloque < count;

  // Carga el bloque visible (inicial o salto) y precarga el siguiente en el borde.
  useEffect(() => {
    if (!habilitado) return;
    cargarBloque(bloqueActual, generacion);
    if (esUltimaPaginaDelBloque && hayBloqueSiguiente) cargarBloque(bloqueActual + 1, generacion);
  }, [habilitado, bloqueActual, esUltimaPaginaDelBloque, hayBloqueSiguiente, cargarBloque, generacion, bloques]);

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
  const recargar = useCallback(() => {
    setCache((previa) => ({ generacion: previa.generacion + 1, bloques: {}, count: previa.count, error: null }));
  }, []);

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
