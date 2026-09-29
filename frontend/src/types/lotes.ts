import type { LoteProduccion } from '../lib/types';

/** Respuesta paginada de DRF (PageNumberPagination). */
export interface Pagina<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type PaginaLotes = Pagina<LoteProduccion>;

/** Filtros del listado `/lotes-produccion/` (LoteProduccionViewSet.get_queryset). */
export interface FiltrosLotes {
  operario?: number;
  orden_produccion?: number;
  sede_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  turno?: string;
  codigo_lote?: string;
  maquina?: number;
  clasificacion_calidad?: string;
  ordering?: string;
}

/** `/lotes-produccion/resumen-hoy/` — calculado con la fecha local del servidor.
 * Los Decimal devueltos fuera de un serializer llegan como número JSON. */
export interface ResumenHoyLotes {
  bultos: number;
  peso_total_kg: number;
  peso_promedio_kg: number;
}

/** `/lotes-produccion/{id}/genealogia/` — resumen del lote. */
export interface FichaLote {
  lote_codigo: string;
  producto: string | null;
  peso_neto: number;
  peso_merma: number;
  tipo_merma: string | null;
  calidad: string;
  operario: string | null;
  maquina: string | null;
  fechas: { inicio: string; final: string };
  orden_produccion: { codigo: string | null; formula_color: string | null };
  quimicos_consumidos: { quimico: string; cantidad_total_op_kg: number; fase: string }[];
}

/** `/inventory/lotes/{codigo}/movimientos/`. */
export interface MovimientosLote {
  lote_codigo: string;
  producto: string;
  historial: {
    id: number;
    fecha: string;
    tipo_movimiento: string;
    bodega_origen: string;
    bodega_destino: string;
    cantidad: number;
    documento_ref: string | null;
    usuario: string;
  }[];
}

/** `/trazabilidad/lote-produccion/` — materias primas, proveedores y costos. */
export interface CadenaMateriasPrimas {
  lote_final: string;
  producto_final: string | null;
  cantidad_producida: number;
  costo_total_materias_primas: number;
  fecha_produccion: string | null;
  clasificacion_calidad: string;
  componentes: {
    materia_prima_lote: string;
    producto: string;
    proveedor: string;
    cantidad_kg: number;
    costo_unitario: number;
    costo_total: number;
    certificado: string | null;
    numero_documento: string;
    fecha_recepcion: string;
    porcentaje_utilizado: number;
  }[];
}
