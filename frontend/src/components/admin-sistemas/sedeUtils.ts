import { toast } from 'sonner';
import { AxiosError } from 'axios';
import type { Sede, Area, User, Bodega, OrdenProduccion, PedidoVenta } from '../../lib/types';

export interface Group {
  id: number;
  name: string;
}

/** Helper para mostrar errores de API de forma consistente en gestión */
export function showApiError(error: unknown, action: 'create' | 'update' | 'delete', entity: string) {
  const axiosError = error as AxiosError<Record<string, unknown>>;
  const actionLabel = action === 'create' ? 'crear' : action === 'update' ? 'actualizar' : 'eliminar';
  if (axiosError.response?.status === 400) {
    const data = axiosError.response.data;
    const msg = typeof data === 'object' && data !== null
      ? Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`).join('; ')
      : String(data);
    toast.error('Error de validación', { description: msg });
  } else if (axiosError.response?.status === 403) {
    toast.error(`No tienes permiso para ${actionLabel} ${entity}`);
  } else if (axiosError.response?.status === 401) {
    toast.error('Sesión expirada. Inicia sesión de nuevo.');
  } else {
    const detail = axiosError.response?.data;
    const errMsg = typeof detail === 'object' && detail && 'detail' in detail
      ? String((detail as { detail?: unknown }).detail) : `Error al ${actionLabel} ${entity}`;
    toast.error(errMsg || `Error al ${actionLabel} ${entity}`);
  }
}

interface SedeStatsDeps {
  sedes: Sede[];
  areas: Area[];
  users: User[];
  bodegas: Bodega[];
  ordenes: OrdenProduccion[];
  pedidos: PedidoVenta[];
}

/** Calcula estadísticas por sede: usa los conteos anotados del backend si existen, o cae a los arreglos locales. */
export function getSedeStats(sedeId: string, { sedes, areas, users, bodegas, ordenes, pedidos }: SedeStatsDeps) {
  const sedeObj = sedes.find(s => s.id.toString() === sedeId);

  // Si tenemos los conteos anotados del backend (para todas las sedes)
  if (sedeObj && sedeObj.num_areas !== undefined) {
    return {
      areas: sedeObj.num_areas,
      users: sedeObj.num_users || 0,
      bodegas: sedeObj.num_bodegas || 0,
      ordenes: sedeObj.num_ordenes || 0,
      pedidos: 0 // Este campo no está anotado aún
    };
  }

  // Fallback: Calcular de los arreglos locales (solo funcionará bien para la sede seleccionada)
  const areasCount = areas.filter(a => a.sede?.toString() === sedeId).length;
  const usersCount = users.filter(u => u.sede?.toString() === sedeId).length;
  const bodegasCount = bodegas.filter(b => b.sede?.toString() === sedeId).length;
  const ordenesCount = ordenes.filter(o => o.sede?.toString() === sedeId).length;
  const pedidosCount = pedidos.filter(p => p.sede?.toString() === sedeId).length;

  return { areas: areasCount, users: usersCount, bodegas: bodegasCount, ordenes: ordenesCount, pedidos: pedidosCount };
}
