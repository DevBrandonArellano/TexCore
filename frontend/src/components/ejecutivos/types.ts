export interface AlertaStock {
  producto: string;
  producto_codigo: string;
  bodega: string;
  stock_actual: string;
  stock_minimo: string;
  faltante?: number;
}

export interface KpiEjecutivo {
  produccion: {
    ops_pendiente: number;
    ops_en_proceso: number;
    ops_finalizada: number;
    kg_hoy: number;
    kg_semana: number;
    kg_mes: number;
    tiempo_promedio_lote_min: number;
  };
  mrp: {
    /** Sugerencias de compra vigentes (informativas). */
    sugerencias_compra: number;
    /** De la última ejecución completada de cada sede. */
    productos_a_producir: number;
    /** Fecha ISO de la ejecución más reciente, o null si nunca se calculó. */
    ultima_ejecucion: string | null;
  };
  stock: { productos_bajo_minimo: number };
  cartera: {
    cuentas_por_cobrar: number;
    cartera_vencida: number;
    pedidos_pendientes: number;
    pedidos_despachados: number;
  };
}

export interface OpsEstadoItem {
  estado: string;
  value: number;
  fill: string;
}

export interface ProduccionResumen {
  ops_por_estado: OpsEstadoItem[];
  kg_hoy: number;
  kg_semana: number;
  kg_mes: number;
  tiempo_promedio_lote_min: number;
}

export interface TendenciaDia {
  fecha: string;
  kg: number;
}

export interface ProduccionProductoItem {
  producto_id: number;
  producto_codigo: string;
  producto_nombre: string;
  kg_total: number;
  num_lotes: number;
}
