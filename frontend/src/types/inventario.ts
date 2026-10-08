import type { Pagina } from './lotes';

/** Lote de materia prima recibido (MateriaPrimaLoteSerializer). Los Decimal llegan como texto. */
export interface MateriaPrimaLote {
  id: number;
  producto: number;
  producto_descripcion: string;
  proveedor: number;
  proveedor_nombre: string;
  lote_proveedor: string;
  fecha_recepcion: string;
  cantidad_kg: string;
  costo_unitario: string;
  certificado_calidad: string | null;
  numero_documento_entrada: string;
  bodega_recepcion: number | null;
  bodega_nombre: string | null;
  cantidad_consumida: string;
  cantidad_disponible: number;
  completamente_consumida: boolean;
  sede: number;
  fecha_creacion: string;
}

export type PaginaMateriaPrima = Pagina<MateriaPrimaLote>;

/** Filtros de `/materia-prima/` (MateriaPrimaLoteViewSet.get_queryset). */
export interface FiltrosMateriaPrima {
  proveedor?: number;
  disponibles?: boolean;
}

/** Recepción F0-001 (`/materia-prima/registrar-entrada/`): crea lote de MP + stock + COMPRA. */
export interface RecepcionMateriaPrima {
  proveedor: number;
  producto: number;
  lote_proveedor: string;
  cantidad_kg: string;
  costo_unitario: string;
  bodega_recepcion: number;
  fecha_recepcion: string;
  numero_documento_entrada?: string;
  pais?: string;
  calidad?: string;
  certificado_calidad?: File | null;
}

/** Fila de `/inventory/retro-kardex/`: saldo de una bodega a la fecha de corte. */
export interface StockAFechaFila {
  bodega_id: number;
  bodega: string;
  sede: string | null;
  stock_calculado: string | number;
}

export interface ConsultaStockAFecha {
  producto_id: number;
  /** 'YYYY-MM-DD' (final de ese día) o fecha y hora ISO 8601 (ese instante). */
  fecha_corte: string;
  bodega_id?: number;
}

/** Fila de `/inventory/stock/` (StockBodegaSerializer). Los Decimal llegan como texto. */
export interface StockItem {
  id: number;
  producto: string;
  producto_id: number;
  bodega: string;
  bodega_id: number;
  lote: string | null;
  lote_id: number | null;
  lote_codigo: string | null;
  cantidad: string;
  stock_comprometido?: string;
  stock_disponible?: string;
}

export type PaginaStock = Pagina<StockItem>;

/** Filtros de `/inventory/stock/` y `/inventory/stock/resumen/` (stock_con_existencias). */
export interface FiltrosStock {
  sede_id?: number | string;
  bodega_id?: number | string;
  producto_id?: number | string;
  search?: string;
}

/** `/inventory/stock/resumen/`: totales calculados en la base; los Decimal llegan como número. */
export interface StockResumenBodega {
  bodega_id: number;
  bodega: string;
  cantidad: number | string;
  filas: number;
}

export interface StockResumen {
  total_cantidad: number | string;
  productos: number;
  bodegas: number;
  por_bodega: StockResumenBodega[];
}
