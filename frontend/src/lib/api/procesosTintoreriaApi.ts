import apiClient from '../axios';
import type { ProcesoTintoreria } from '../types';

export type DatosNuevoProceso = Pick<ProcesoTintoreria, 'codigo' | 'nombre' | 'tipo'> & { descripcion?: string };
/** El código y la sede no se editan: las recetas citan el proceso por su código. */
export type CambiosProceso = Partial<Pick<ProcesoTintoreria, 'nombre' | 'tipo' | 'descripcion' | 'activo'>>;

const lista = (data: ProcesoTintoreria[] | { results: ProcesoTintoreria[] }) =>
  (Array.isArray(data) ? data : data.results);

/**
 * Repository del catálogo de procesos de tintorería de la sede (DESCRUDE, LAVADO
 * REDUCTIVO...) y de los procesos que ejecuta cada máquina. Distinto del catálogo
 * global de procesos de producción (`procesosApi`, `/process-steps/`).
 */
export const procesosTintoreriaApi = {
  async listar({ soloActivos = false }: { soloActivos?: boolean } = {}): Promise<ProcesoTintoreria[]> {
    const res = await apiClient.get<ProcesoTintoreria[] | { results: ProcesoTintoreria[] }>(
      '/procesos-tintoreria/', { params: soloActivos ? { activo: 'true' } : {} },
    );
    return lista(res.data);
  },

  async crear(datos: DatosNuevoProceso): Promise<ProcesoTintoreria> {
    const res = await apiClient.post<ProcesoTintoreria>('/procesos-tintoreria/', datos);
    return res.data;
  },

  async actualizar(id: number, cambios: CambiosProceso): Promise<ProcesoTintoreria> {
    const res = await apiClient.patch<ProcesoTintoreria>(`/procesos-tintoreria/${id}/`, cambios);
    return res.data;
  },

  /** Reemplaza el conjunto completo de procesos que ejecuta la máquina. */
  async asignarAMaquina(maquinaId: number, procesoIds: number[]): Promise<ProcesoTintoreria[]> {
    const res = await apiClient.put<ProcesoTintoreria[]>(`/maquinas/${maquinaId}/procesos/`, { procesos: procesoIds });
    return res.data;
  },
};
