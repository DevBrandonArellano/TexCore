import apiClient from '../axios';
import type { ProcesoProduccion } from '../types';

export type DatosProceso = Pick<ProcesoProduccion, 'name' | 'description'>;

/** Repository del catálogo de procesos de producción (global, sin sede). */
export const procesosApi = {
  async listar(): Promise<ProcesoProduccion[]> {
    // El catálogo es corto: se trae completo (tope de la paginación del servidor).
    const res = await apiClient.get<ProcesoProduccion[] | { results: ProcesoProduccion[] }>(
      '/process-steps/', { params: { page_size: 500 } },
    );
    return Array.isArray(res.data) ? res.data : res.data.results;
  },

  async crear(datos: DatosProceso): Promise<ProcesoProduccion> {
    const res = await apiClient.post<ProcesoProduccion>('/process-steps/', datos);
    return res.data;
  },

  async actualizar(id: number, datos: DatosProceso): Promise<ProcesoProduccion> {
    const res = await apiClient.patch<ProcesoProduccion>(`/process-steps/${id}/`, datos);
    return res.data;
  },

  async eliminar(id: number): Promise<void> {
    await apiClient.delete(`/process-steps/${id}/`);
  },
};
