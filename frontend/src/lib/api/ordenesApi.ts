import apiClient from '../axios';
import type { DosificacionOrdenResultado, OrdenProduccion, ProcesoTintoreria } from '../types';
import type { TransformacionProducto } from '../../types/produccion';

/** Campos que el Jefe de Área completa en una orden (`completar_detalles`). */
export interface DetallesOrden {
  maquina_asignada?: number;
  operario_asignado?: number;
  producto_entrada?: number;
  producto_salida?: number;
  bodega_entrada?: number;
  bodega_salida?: number;
  bodega_quimicos?: number;
  formula_color?: number;
  /** Pasa la orden a en_proceso en la misma operación. */
  iniciar?: boolean;
}

/**
 * Repository de órdenes de producción: acciones del Jefe de Área y vistas
 * previas del Jefe de Planta. Los componentes no arman URLs.
 */
export const ordenesApi = {
  async completarDetalles(ordenId: number, detalles: DetallesOrden): Promise<OrdenProduccion> {
    const res = await apiClient.patch<OrdenProduccion>(`/ordenes-produccion/${ordenId}/completar_detalles/`, detalles);
    return res.data;
  },

  async calcularDosificacion(ordenId: number, litrosBano: number): Promise<DosificacionOrdenResultado> {
    const res = await apiClient.post<DosificacionOrdenResultado>(
      `/ordenes-produccion/${ordenId}/calcular-dosificacion/`, { litros_bano: litrosBano },
    );
    return res.data;
  },

  async procesosDeMaquina(maquinaId: number): Promise<ProcesoTintoreria[]> {
    const res = await apiClient.get<ProcesoTintoreria[]>(`/maquinas/${maquinaId}/procesos/`);
    return res.data;
  },

  /** Todas las transformaciones de la orden, también en curso y rechazadas (la trazabilidad solo trae completadas). */
  async transformaciones(ordenId: number): Promise<TransformacionProducto[]> {
    const res = await apiClient.get<TransformacionProducto[]>(`/ordenes-produccion/${ordenId}/transformaciones/`);
    return res.data;
  },
};
