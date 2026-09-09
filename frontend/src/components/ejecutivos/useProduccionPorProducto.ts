import { useState, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { ProduccionProductoItem, TendenciaDia } from './types';

interface UseProduccionPorProductoParams {
  fechaInicio: string;
  fechaFin: string;
  sedeId: string;
}

/**
 * CU-EJ-08/09: producción por producto (drill-down ejecutivo) + historial diario
 * de un producto seleccionado + impresión del listado en PDF.
 */
export function useProduccionPorProducto({ fechaInicio, fechaFin, sedeId }: UseProduccionPorProductoParams) {
  const [productos, setProductos] = useState<ProduccionProductoItem[]>([]);
  const [cargandoProductos, setCargandoProductos] = useState(false);
  const [productoSeleccionado, setProductoSeleccionado] = useState<ProduccionProductoItem | null>(null);
  const [historialProducto, setHistorialProducto] = useState<TendenciaDia[]>([]);
  const [cargandoHistorial, setCargandoHistorial] = useState(false);
  const [imprimiendo, setImprimiendo] = useState(false);

  const buildParams = useCallback(() => ({
    fecha_inicio: fechaInicio,
    fecha_fin: fechaFin,
    ...((sedeId && sedeId !== 'todas') && { sede_id: sedeId }),
  }), [fechaInicio, fechaFin, sedeId]);

  useEffect(() => {
    let cancelado = false;
    setCargandoProductos(true);
    apiClient.get<ProduccionProductoItem[]>('/produccion/por-producto/', { params: buildParams() })
      .then(res => { if (!cancelado) setProductos(Array.isArray(res.data) ? res.data : []); })
      .catch(() => {
        if (cancelado) return;
        toast.error('Error al cargar la producción por producto');
        setProductos([]);
      })
      .finally(() => { if (!cancelado) setCargandoProductos(false); });
    return () => { cancelado = true; };
  }, [buildParams]);

  const verHistorialProducto = useCallback((item: ProduccionProductoItem) => {
    setProductoSeleccionado(item);
    setCargandoHistorial(true);
    apiClient.get<TendenciaDia[]>('/produccion/historial-producto/', {
      params: { ...buildParams(), producto_id: item.producto_id },
    })
      .then(res => setHistorialProducto(Array.isArray(res.data) ? res.data : []))
      .catch(() => {
        toast.error('Error al cargar el historial del producto');
        setHistorialProducto([]);
      })
      .finally(() => setCargandoHistorial(false));
  }, [buildParams]);

  const cerrarHistorialProducto = useCallback(() => {
    setProductoSeleccionado(null);
    setHistorialProducto([]);
  }, []);

  const imprimirProduccionPorProducto = useCallback(async () => {
    setImprimiendo(true);
    try {
      const response = await apiClient.get('/produccion/por-producto/imprimir/', {
        params: buildParams(),
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      window.open(url, '_blank');
    } catch {
      toast.error('Error al generar el PDF de producción por producto');
    } finally {
      setImprimiendo(false);
    }
  }, [buildParams]);

  return {
    productos,
    cargandoProductos,
    productoSeleccionado,
    historialProducto,
    cargandoHistorial,
    imprimiendo,
    verHistorialProducto,
    cerrarHistorialProducto,
    imprimirProduccionPorProducto,
  };
}
