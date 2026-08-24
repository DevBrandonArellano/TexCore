import { Badge } from '../ui/badge';
import type { OrdenProduccion } from '../../lib/types';

export interface OrdenFormData {
  codigo: string;
  producto_entrada: string;
  bodega_entrada: string;
  producto_salida: string;
  bodega_salida: string;
  formula_color: string;
  peso_neto_requerido: string;
  sede: string;
  area: string;
  bodega_quimicos: string;
  estado: string;
  fecha_inicio_planificada: string;
  fecha_fin_planificada: string;
  maquina_asignada: string;
  observaciones: string;
  prioridad: string;
  justificacion: string;
}

/** Formatea un Date a "YYYY-MM-DDTHH:mm" en hora local para <input datetime-local>. */
export function toLocalDatetimeInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    + `T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function getOrdenVencimientoStatus(orden: Pick<OrdenProduccion, 'estado' | 'fecha_fin_planificada'>) {
  const today = new Date().toISOString().split('T')[0];
  const isOverdue = orden.estado !== 'finalizada' && orden.fecha_fin_planificada && orden.fecha_fin_planificada < today;
  const isToday = orden.estado !== 'finalizada' && orden.fecha_fin_planificada === today;
  return { isOverdue, isToday };
}

export function estadoBadge(estado: string) {
  if (estado === 'pendiente') return <Badge variant="secondary" className="bg-slate-100 text-slate-600 hover:bg-slate-200 border-slate-200">Pendiente</Badge>;
  if (estado === 'en_proceso') return <Badge variant="secondary" className="bg-blue-50 text-blue-600 hover:bg-blue-100 border-blue-200">En Proceso</Badge>;
  if (estado === 'finalizada') return <Badge variant="secondary" className="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border-emerald-200">Finalizada</Badge>;
  return <Badge variant="outline" className="capitalize">{estado.replace('_', ' ')}</Badge>;
}

export function prioridadBadge(prioridad: string) {
  if (prioridad === 'baja') return <Badge variant="secondary" className="bg-slate-100 text-slate-600">Baja</Badge>;
  if (prioridad === 'normal') return <Badge variant="secondary" className="bg-blue-50 text-blue-600">Normal</Badge>;
  if (prioridad === 'alta') return <Badge variant="secondary" className="bg-orange-50 text-orange-600 border-orange-200">Alta</Badge>;
  if (prioridad === 'urgente') return <Badge variant="secondary" className="bg-red-50 text-red-600 border-red-200 font-bold animate-pulse">Urgente</Badge>;
  return null;
}

export function buildOrdenPayload(formData: OrdenFormData) {
  return {
    ...formData,
    producto_entrada: parseInt(formData.producto_entrada),
    bodega_entrada: formData.bodega_entrada ? parseInt(formData.bodega_entrada) : null,
    producto_salida: parseInt(formData.producto_salida),
    bodega_salida: formData.bodega_salida ? parseInt(formData.bodega_salida) : null,
    formula_color: formData.formula_color ? parseInt(formData.formula_color) : null,
    sede: formData.sede ? parseInt(formData.sede) : null,
    area: formData.area ? parseInt(formData.area) : null,
    bodega_quimicos: formData.bodega_quimicos ? parseInt(formData.bodega_quimicos) : null,
    maquina_asignada: (formData.maquina_asignada && formData.maquina_asignada !== '0') ? parseInt(formData.maquina_asignada) : null,
    fecha_inicio_planificada: formData.fecha_inicio_planificada || null,
    fecha_fin_planificada: formData.fecha_fin_planificada || null,
  };
}

export function validateOrdenForm(formData: OrdenFormData, isEditing: boolean): Record<string, string> {
  const newErrors: Record<string, string> = {};
  if (!formData.codigo.trim()) newErrors.codigo = 'El código es requerido';
  if (!formData.area) newErrors.area = 'El área es requerida';
  if (!formData.peso_neto_requerido || parseFloat(formData.peso_neto_requerido) <= 0) newErrors.peso_neto_requerido = 'El peso es requerido y debe ser mayor a 0';

  // Al editar, requiere productos y bodegas
  if (isEditing) {
    if (!formData.producto_entrada) newErrors.producto_entrada = 'El producto de entrada es requerido';
    if (!formData.producto_salida) newErrors.producto_salida = 'El producto de salida es requerido';
  }

  return newErrors;
}

export const EMPTY_ORDEN_FORM_DATA: OrdenFormData = {
  codigo: '',
  producto_entrada: '',
  bodega_entrada: '',
  producto_salida: '',
  bodega_salida: '',
  formula_color: '',
  peso_neto_requerido: '',
  sede: '',
  area: '',
  bodega_quimicos: '',
  estado: 'pendiente',
  fecha_inicio_planificada: '',
  fecha_fin_planificada: '',
  maquina_asignada: '',
  observaciones: '',
  prioridad: 'normal',
  justificacion: '',
};
