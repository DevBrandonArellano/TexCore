import apiClient from '../axios';

/** Equivalencias de empaque de una sede (TEX-43). Sin configurar, los valores son null. */
export interface ConfiguracionEmpaque {
  sede_id: number;
  sede_nombre: string;
  configurada: boolean;
  fundas_por_bano: number | null;
  conos_por_funda: number | null;
  conos_por_bano: number | null;
}

export interface CambioConfiguracionEmpaque {
  fundas_por_bano: number;
  conos_por_funda: number;
  justificacion: string;
}

/** El Administrador de Sede trabaja sobre la suya (sin sedeId); el de Sistemas indica la sede. */
const paramsSede = (sedeId?: string) => (sedeId ? { params: { sede_id: sedeId } } : {});

/** Repository de las equivalencias de empaque por sede. */
export const configuracionEmpaqueApi = {
  async obtener(sedeId?: string): Promise<ConfiguracionEmpaque> {
    const res = await apiClient.get<ConfiguracionEmpaque>('/configuracion-empaque/', paramsSede(sedeId));
    return res.data;
  },

  async guardar(cambio: CambioConfiguracionEmpaque, sedeId?: string): Promise<ConfiguracionEmpaque> {
    const res = await apiClient.put<ConfiguracionEmpaque>('/configuracion-empaque/', cambio, paramsSede(sedeId));
    return res.data;
  },
};
