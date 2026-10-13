import apiClient from '../axios';
import type { MRPEjecucion, NecesidadReposicion, OrdenCompraSugerida, RequerimientoMaterial } from '../types';
import type { Pagina } from '../../types/lotes';

const BASE = '/inventory/sugerencias-compra/';

/** Alcance de una ejecución: todas las sedes, una sede o la del usuario (cuerpo vacío). */
export type AlcanceMRP = { todas: true } | { sede_id: number } | Record<string, never>;

/** Filtro de sede de las consultas; sin sede, el backend usa la del usuario (o todas si es global). */
const conSede = (sede?: string) => (sede ? { sede } : {});

/**
 * MRP por sede (ADR-012): ejecución, última ejecución por sede, sugerencias de compra,
 * requerimientos por orden y necesidad de producción.
 */
export const mrpApi = {
  async listarSugerencias(pagina: number, tamanoPagina: number, sede?: string): Promise<Pagina<OrdenCompraSugerida>> {
    const res = await apiClient.get<Pagina<OrdenCompraSugerida>>(BASE, {
      params: { page: pagina, page_size: tamanoPagina, ...conSede(sede) },
    });
    return res.data;
  },

  async listarRequerimientos(pagina: number, tamanoPagina: number, sede?: string): Promise<Pagina<RequerimientoMaterial>> {
    const res = await apiClient.get<Pagina<RequerimientoMaterial>>('/inventory/requerimientos-material/', {
      params: { page: pagina, page_size: tamanoPagina, ...conSede(sede) },
    });
    return res.data;
  },

  async ultimaEjecucion(sede?: string): Promise<MRPEjecucion[]> {
    const res = await apiClient.get<MRPEjecucion[]>(`${BASE}ultima-ejecucion/`, { params: conSede(sede) });
    return res.data;
  },

  async necesidadesProduccion(sede?: string): Promise<NecesidadReposicion[]> {
    const res = await apiClient.get<NecesidadReposicion[]>(`${BASE}necesidades-produccion/`, { params: conSede(sede) });
    return res.data;
  },

  /** Ejecuta el MRP. Un fallo del motor responde 500 con las ejecuciones (alguna «fallida»):
   * se devuelven igual, para mostrar el resultado de cada sede. */
  async ejecutar(alcance: AlcanceMRP): Promise<MRPEjecucion[]> {
    try {
      const res = await apiClient.post<{ ejecuciones: MRPEjecucion[] }>(`${BASE}ejecutar-mrp/`, alcance);
      return res.data.ejecuciones;
    } catch (error) {
      const ejecuciones = (error as { response?: { data?: { ejecuciones?: MRPEjecucion[] } } }).response?.data?.ejecuciones;
      if (ejecuciones) return ejecuciones;
      throw error;
    }
  },
};
