import apiClient from '../axios';
import type { Pagina } from '../../types/lotes';

const BASE = '/paros-maquina/';

/** Las 9 categorías de paro (Seis Grandes Pérdidas), tal como las define el backend. */
export type CategoriaParo =
  | 'AVERIA'
  | 'SETUP'
  | 'MICROPARO'
  | 'VELOCIDAD_REDUCIDA'
  | 'RECHAZO_ARRANQUE'
  | 'DEFECTO_PROCESO'
  | 'FALTA_MATERIAL'
  | 'MANTENIMIENTO_PLANIFICADO'
  | 'OTRO';

export interface FiltrosHistorialParos {
  fecha_desde?: string;
  fecha_hasta?: string;
  maquina?: number;
  categoria?: CategoriaParo;
  planificado?: boolean;
}

/** Una fila del resumen: lo detenido de una máquina dentro del rango consultado. */
export interface ResumenMaquinaParos {
  maquina_id: number;
  maquina_nombre: string;
  area_nombre: string | null;
  paros: number;
  horas_total: number;
  horas_planificadas: number;
  paros_en_curso: number;
  ultimo_mantenimiento: string | null;
}

/** Una fila del detalle. `origen: 'estado'` lo abrió el sistema al cambiar el estado de la máquina. */
export interface ParoHistorial {
  id: number;
  maquina: number;
  maquina_nombre: string;
  area_nombre: string | null;
  inicio: string;
  fin: string | null;
  categoria: CategoriaParo;
  categoria_display: string;
  planificado: boolean;
  descripcion: string;
  turno: string;
  usuario_nombre: string | null;
  origen: 'manual' | 'estado';
  en_curso: boolean;
  horas: number | null;
}

export interface TotalesHistorialParos {
  maquinas: number;
  paros: number;
  horas_total: number;
  horas_planificadas: number;
  paros_en_curso: number;
}

export interface HistorialParos {
  rango: { fecha_desde: string; fecha_hasta: string };
  resumen: ResumenMaquinaParos[];
  totales: TotalesHistorialParos;
  detalle: Pagina<ParoHistorial>;
}

/** Solo los filtros con valor llegan al backend: un `undefined` dejaría `?maquina=` y daría 400. */
const limpiar = (filtros: FiltrosHistorialParos): Record<string, string | number | boolean> =>
  Object.fromEntries(Object.entries(filtros).filter(([, valor]) => valor !== undefined && valor !== ''));

/**
 * Historial de mantenimiento y paros de máquina del área (Jefe de Área).
 * Los componentes no arman URLs ni query strings.
 */
export const mantenimientoApi = {
  async historial(filtros: FiltrosHistorialParos, pagina = 1, tamanoPagina = 50): Promise<HistorialParos> {
    const res = await apiClient.get<HistorialParos>(`${BASE}historial/`, {
      params: { ...limpiar(filtros), page: pagina, page_size: tamanoPagina },
    });
    return res.data;
  },

  /** El mismo historial en PDF, con el rango completo (el backend no lo pagina). */
  async imprimirHistorial(filtros: FiltrosHistorialParos): Promise<Blob> {
    const res = await apiClient.post<Blob>(`${BASE}imprimir-historial/`, limpiar(filtros), {
      responseType: 'blob',
    });
    return res.data;
  },
};
