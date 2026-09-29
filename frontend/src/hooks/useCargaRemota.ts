import { useCallback, useEffect, useRef, useState } from 'react';
import { getApiErrorMessage } from '../lib/apiError';

/**
 * Carga un recurso al montarse y cuando cambia `clave`; descarta respuestas de
 * una clave anterior. Para paneles de solo lectura (ficha de lote).
 */
export function useCargaRemota<T>(cargar: () => Promise<T>, clave: unknown) {
  const [datos, setDatos] = useState<T | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cargarRef = useRef(cargar);
  cargarRef.current = cargar;
  const generacionRef = useRef(0);

  const ejecutar = useCallback(() => {
    const generacion = ++generacionRef.current;
    setCargando(true);
    setError(null);
    cargarRef
      .current()
      .then((respuesta) => {
        if (generacion === generacionRef.current) setDatos(respuesta);
      })
      .catch((err) => {
        if (generacion === generacionRef.current) setError(getApiErrorMessage(err, 'No se pudo cargar la información.'));
      })
      .finally(() => {
        if (generacion === generacionRef.current) setCargando(false);
      });
  }, []);

  useEffect(() => {
    ejecutar();
  }, [clave, ejecutar]);

  return { datos, cargando, error, recargar: ejecutar };
}
