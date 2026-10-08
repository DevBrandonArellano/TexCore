import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { getApiErrorMessage } from '../lib/apiError';

/** Resultado de una carga, marcado con la clave y la recarga a las que responde. */
interface Respuesta<T> {
  clave: unknown;
  recarga: number;
  datos: T | null;
  error: string | null;
}

export interface OpcionesCargaRemota {
  /** Mientras sea `false` no se pide nada (diálogo cerrado, sin selección). */
  habilitado?: boolean;
  /** Texto del error a mostrar; por defecto, el detalle de la API o un mensaje genérico. */
  mensajeDeError?: (err: unknown) => string;
}

/**
 * Carga un recurso al montarse y cuando cambia `clave`; descarta respuestas de
 * una clave anterior.
 *
 * `cargando` se deriva de si la última respuesta corresponde a la clave y la
 * recarga vigentes: el efecto solo actualiza el estado cuando llega la respuesta
 * (sin `setState` síncrono que provoque renders en cascada).
 */
export function useCargaRemota<T>(cargar: () => Promise<T>, clave: unknown, opciones: OpcionesCargaRemota = {}) {
  const { habilitado = true } = opciones;
  const [recarga, setRecarga] = useState(0);
  const [respuesta, setRespuesta] = useState<Respuesta<T> | null>(null);
  // `cargar` y las opciones cambian de identidad en cada render del dueño: se leen
  // desde una ref (actualizada antes de los efectos) para no volver a pedir por eso.
  const vigentesRef = useRef({ cargar, opciones });
  useLayoutEffect(() => {
    vigentesRef.current = { cargar, opciones };
  });

  useEffect(() => {
    if (!habilitado) return;
    let vigente = true;
    const { cargar: cargarVigente, opciones: opcionesVigentes } = vigentesRef.current;
    cargarVigente().then(
      (datos) => {
        if (vigente) setRespuesta({ clave, recarga, datos, error: null });
      },
      (err) => {
        if (!vigente) return;
        const error = opcionesVigentes.mensajeDeError?.(err) ?? getApiErrorMessage(err, 'No se pudo cargar la información.');
        // Un error al recargar conserva los datos ya mostrados de la misma clave.
        setRespuesta((previa) => ({
          clave,
          recarga,
          datos: previa && Object.is(previa.clave, clave) ? previa.datos : null,
          error,
        }));
      },
    );
    return () => {
      vigente = false;
    };
  }, [clave, recarga, habilitado]);

  const recargar = useCallback(() => setRecarga((n) => n + 1), []);
  const mismaClave = respuesta !== null && Object.is(respuesta.clave, clave);
  const alDia = mismaClave && respuesta.recarga === recarga;

  return {
    datos: mismaClave ? respuesta.datos : null,
    cargando: habilitado && !alDia,
    error: alDia ? respuesta.error : null,
    recargar,
  };
}
