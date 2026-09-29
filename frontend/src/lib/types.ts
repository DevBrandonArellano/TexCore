// Módulo 1: Usuarios y Perfiles
export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  area: number | null;
  sede: number | null;
  groups: number[];
  permissions: string[];
  bodegas_asignadas: number[];
}

export interface Profile {
  id: number;
  userId: number;
  groups: number[];
}

// Módulo 2: Catálogos y Bodegas
export interface Proveedor {
  id: number;
  nombre: string;
  sede?: number | null;
}

export interface Producto {
  id: number;
  codigo: string;
  descripcion: string;
  tipo: 'hilo' | 'tela' | 'subproducto' | 'quimico' | 'insumo' | 'materia_prima' | 'colorante' | 'producto_intermedio' | 'merma';
  unidad_medida: 'kg' | 'gr' | 'lb' | 'l' | 'ml' | 'gl' | 'metros' | 'yardas' | 'unidades';
  stock_minimo: number;
  presentacion?: string;
  pais_origen?: string;
  calidad?: string;
  precio_base: number;
  sede?: number | null;
}

export interface Quimico {
  id: number;
  codigo: string;
  descripcion: string;
  tipo: 'quimico';
  unidad_medida: string;
  stock_minimo?: number;
  presentacion?: string;
  pais_origen?: string;
  calidad?: string;
  precio_base: number;
}

export interface Bodega {
  id: number;
  nombre: string;
  sede: number;
  usuarios_asignados?: number[];
}

export interface Maquina {
  id: number;
  nombre: string;
  capacidad_maxima: number;
  eficiencia_ideal: number;
  estado: 'operativa' | 'mantenimiento' | 'inactiva';
  area: number | null;
  area_nombre?: string;
  operarios?: number[];
  operarios_nombres?: string[];
}

export interface LineaProduccion {
  id: number;
  nombre: string;
  descripcion?: string | null;
  estado: 'activa' | 'inactiva';
  area: number;
  area_nombre?: string;
  maquinas: number[];
  maquinas_detail?: { id: number; nombre: string; estado: string; compartida: boolean }[];
  fecha_creacion?: string;
  fecha_modificacion?: string;
}

export interface OeeResultado {
  disponibilidad: number;
  rendimiento: number;
  calidad: number;
  oee: number;
  downtime_min: number;
}

export interface KPIArea {
  area: string;
  total_produccion_kg: number;
  total_merma_kg?: number;
  rendimiento_yield: number;
  first_pass_yield?: number;
  distribucion_calidad?: {
    primera: number;
    segunda: number;
    saldo: number;
  };
  tiempo_promedio_lote_min: number;
  oee?: OeeResultado;
}

// Reason codes = Seis Grandes Pérdidas (OEE for Operators — Productivity Press)
export type CategoriaParoMaquina =
  | 'AVERIA' | 'SETUP' | 'MICROPARO' | 'VELOCIDAD_REDUCIDA'
  | 'RECHAZO_ARRANQUE' | 'DEFECTO_PROCESO' | 'FALTA_MATERIAL'
  | 'MANTENIMIENTO_PLANIFICADO' | 'OTRO';

export interface ParoMaquina {
  id: number;
  maquina: number;
  maquina_nombre?: string;
  inicio: string;
  fin?: string | null;
  categoria: CategoriaParoMaquina;
  categoria_display?: string;
  planificado: boolean;
  descripcion?: string;
  turno?: string;
  usuario?: number | null;
  duracion_minutos?: number | null;
}

// Módulo 3: Producción
export interface OrdenProduccion {
  id: number;
  codigo: string;
  producto: number;
  formula_color: number;
  peso_neto_requerido: number;
  peso_producido?: number;
  estado: 'pendiente' | 'en_proceso' | 'finalizada';
  pedido_venta?: number | null;
  detalle_pedido?: number | null;
  fecha_creacion: string;
  fecha_modificacion: string;
  sede: number;
  area?: number | null;
  area_nombre?: string;
  producto_nombre?: string;
  formula_color_nombre?: string;
  sede_nombre?: string;
  bodega?: number | null;
  bodega_nombre?: string;
  bodega_quimicos?: number | null;
  bodega_quimicos_nombre?: string;
  inventario_descontado: boolean;
  fecha_inicio_planificada?: string;
  fecha_fin_planificada?: string;
  maquina_asignada?: number | null;
  maquina_asignada_nombre?: string;
  operario_asignado?: number | null;
  operario_asignado_nombre?: string;
  observaciones?: string;
  prioridad: 'baja' | 'normal' | 'alta' | 'urgente';
  justificacion?: string;
  // Fase 3 del spec 2026-09-24 (D3): litros_bano es el dato canónico que fija el
  // ingeniero tintorero; relacion_bano se deriva (litros / peso) y nunca se escribe.
  litros_bano?: string | null;
  relacion_bano?: string | null;
  version_formula?: number | null;
}

/** Vista previa de dosificación de una orden (POST /ordenes-produccion/{id}/calcular-dosificacion/). */
export interface DosificacionOrdenResultado {
  orden_id: number;
  peso: string;
  litros_bano: string;
  relacion_bano: string;
  insumos: {
    producto_id: number;
    producto_descripcion: string;
    tipo_calculo: 'gr_l' | 'pct';
    cantidad_kg: string;
    cantidad_gr: string;
    concentracion_gr_l: string | null;
    porcentaje: string | null;
    orden_adicion: number;
  }[];
}

export interface LoteProduccion {
  id: number;
  orden_produccion: number;
  codigo_lote: string;
  peso_neto_producido: number;
  operario: number;
  maquina: number | null;
  maquina_nombre?: string;
  turno: string;
  hora_inicio: string;
  hora_final: string;
  peso_bruto?: number;
  tara?: number;
  unidades_empaque?: number;
  presentacion?: string;
  operario_nombre?: string;
  peso_merma?: number;
  tipo_merma?: string;
  clasificacion_calidad?: string;
  pedido_venta_reserva?: number | null;
}

export interface DescargaQuimicoOP {
  id: number;
  orden_produccion: number;
  producto: number;
  producto_codigo: string;
  producto_descripcion: string;
  fase?: number | null;
  bodega: number;
  bodega_nombre: string;
  tipo_calculo: 'gr_l' | 'pct';
  cantidad_calculada_kg: number;
  cantidad_real_kg: number | null;
  estado: 'aplicada' | 'revertida';
  fecha_descarga: string;
  descargado_por: number | null;
  descargado_por_nombre?: string;
  justificacion?: string;
}

export interface StockQuimico {
  producto_id: number;
  producto_codigo: string;
  producto_descripcion: string;
  cantidad: number;
  stock_minimo: number;
  alerta: boolean;
  bodega_nombre: string;
}

export type TipoSustrato = 'algodon' | 'poliester' | 'nylon' | 'mixto' | 'otro';

export interface FormulaColor {
  id: number;
  codigo: string;
  nombre_color: string;
  description?: string;
  tipo_sustrato: TipoSustrato;
  tipo_sustrato_display?: string;
  version: number;
  /** Número de la versión oficial vigente (null si la fórmula nunca se aprobó). */
  version_oficial?: number | null;
  estado: 'en_pruebas' | 'aprobada';
  estado_display?: string;
  creado_por?: number | null;
  creado_por_nombre?: string;
  fecha_creacion?: string;
  fecha_modificacion?: string;
  observaciones?: string;
  detalles?: any[];
  fases?: FaseReceta[];
  // Derivación (spec 2026-09-24 §5.7, D8-D9)
  formula_origen?: number | null;
  formula_origen_codigo?: string | null;
  version_origen?: number | null;
  version_origen_numero?: number | null;
  motivo_derivacion?: string;
  es_laboratorio?: boolean;
}

export type TipoProcesoTintoreria = 'pre_tratamiento' | 'colorante' | 'auxiliar' | 'lavado' | 'acabado';

/** Catálogo de procesos de tintorería por sede (GET /procesos-tintoreria/). */
export interface ProcesoTintoreria {
  id: number;
  codigo: string;
  nombre: string;
  tipo: TipoProcesoTintoreria;
  tipo_display?: string;
  descripcion?: string | null;
  activo: boolean;
  sede?: number | null;
}

export interface FaseReceta {
  id: number;
  proceso: number;
  proceso_codigo?: string;
  proceso_nombre?: string;
  ciclo?: number | null;
  orden: number;
  temperatura?: number | null;
  tiempo?: number | null;
  observaciones?: string;
  detalles: DetalleFormula[];
}

export interface DetalleFormula {
  id: number;
  fase: number;
  producto: number;
  producto_descripcion?: string;
  producto_codigo?: string;
  gramos_por_kilo: number;
  tipo_calculo: 'gr_l' | 'pct';
  concentracion_gr_l?: number | null;
  porcentaje?: number | null;
  orden_adicion: number;
  notas?: string;
}

/** Entrada del historial de versiones (GET /formula-colors/{id}/versiones/). */
export interface VersionFormulaResumen {
  id: number;
  numero: number;
  es_oficial: boolean;
  motivo: string;
  /** Notas del ensayo (D7): «sale muy rojizo», «falta igualación». */
  observaciones: string;
  fecha: string;
  creada_por: number | null;
  creada_por_nombre: string | null;
}

type CambiosCampos = Record<string, { a: unknown; b: unknown }>;

export interface SnapshotDetalle {
  producto_id: number | null;
  producto_codigo: string | null;
  producto_descripcion: string | null;
  tipo_calculo: 'gr_l' | 'pct';
  concentracion_gr_l: string | null;
  porcentaje: string | null;
  orden_adicion: number;
}

export interface SnapshotFase {
  orden: number;
  proceso_codigo: string;
  proceso_nombre: string;
  proceso_tipo: TipoProcesoTintoreria;
  ciclo: number | null;
  temperatura: number | null;
  tiempo: number | null;
  detalles: SnapshotDetalle[];
}

/** Diferencias de la versión A a la B (GET /formula-colors/{id}/versiones/{a}/diff/{b}/). */
export interface DiffVersionesFormula {
  formula_id: number;
  a: number;
  b: number;
  cambios: {
    formula: CambiosCampos;
    fases: {
      agregadas: SnapshotFase[];
      eliminadas: SnapshotFase[];
      modificadas: {
        orden: number;
        proceso_codigo: string;
        cambios: CambiosCampos;
        detalles: {
          agregados: SnapshotDetalle[];
          eliminados: SnapshotDetalle[];
          modificados: { producto_id: number; producto_codigo: string | null; cambios: CambiosCampos }[];
        };
      }[];
    };
  };
}

export interface DosificacionInput {
  kg_tela: number;
  relacion_bano: number;
}

export interface ResultadoInsumo {
  producto_id: number;
  producto_descripcion: string;
  tipo_calculo: 'gr_l' | 'pct';
  cantidad_kg: string;
  cantidad_gr: string;
  concentracion_gr_l?: string | null;
  porcentaje?: string | null;
  orden_adicion: number;
  notas: string;
}

export interface ResultadoDosificacion {
  formula_id: number;
  formula_nombre: string;
  formula_version: number;
  kg_tela: string;
  relacion_bano: string;
  volumen_bano_litros: string;
  insumos: ResultadoInsumo[];
}

// Módulo 4: Ventas y Clientes
export interface Cliente {
  id: number;
  ruc_cedula: string;
  nombre_razon_social: string;
  direccion_envio: string;
  nivel_precio: 'mayorista' | 'normal';
  tiene_beneficio: boolean;
  saldo_pendiente: number | string; // Updated type
  limite_credito: number;
  plazo_credito_dias?: number; // New field
  cartera_vencida?: number | string; // New field
   sede?: number | null;
  vendedor_asignado?: number | null;
  pedidos?: PedidoVenta[];
  pagos?: PagoCliente[];
  ultima_compra?: {
    fecha: string;
    id_pedido: number;
    items: {
      producto: string;
      cantidad: number;
      piezas: number;
      peso: number;
    }[];
  } | null;
  is_active: boolean;
}

export interface PagoCliente {
  id: number;
  cliente: number;
  cliente_nombre?: string;
  fecha: string;
  monto: number;
  metodo_pago: 'efectivo' | 'transferencia' | 'cheque' | 'otro';
  comprobante?: string;
  notas?: string;
  sede?: number;
  // P1-002: pago por adelantado — el excedente queda como saldo a favor
  es_anticipo?: boolean;
}

export interface PedidoVenta {
  id: number;
  numero_pedido?: string;
  cliente: number;
  cliente_nombre?: string;
  vendedor_nombre?: string;
  guia_remision: string;
  fecha_pedido: string;
  fecha_creacion?: string;
  fecha_despacho?: string;
  estado: 'pendiente' | 'despachado_parcial' | 'despachado' | 'facturado';
  esta_pagado: boolean;
  // P1-003: abono aplicado vía reconciliación FIFO y su % sobre el total
  monto_pagado?: string;
  porcentaje_pagado?: string;
  sede: number;
  sede_nombre?: string;
  detalles?: DetallePedido[];
  total: number;
  // Opcional: valor de retención aplicado a la factura (si existe)
  valor_retencion?: number;
  // Anulación
  anulado: boolean;
  motivo_anulacion?: string | null;
  anulado_por?: number | null;
  anulado_por_nombre?: string | null;
  fecha_anulacion?: string | null;

}

export interface DetallePedido {
  id: number;
  pedido_venta: number;
  producto: number;
  producto_nombre?: string;
  lote: number | null;
  cantidad: number;
  piezas: number;
  peso: number;
  precio_unitario: number;
  incluye_iva?: boolean;
  cantidad_fabricada?: number;
  estado_fabricacion?: 'pendiente' | 'en_proceso' | 'fabricado';
  saldo_pendiente_fabricacion?: number;
}

export interface Movimiento {
  id: number;
  fecha: string;
  tipo_movimiento: string;
  producto: string;
  codigo_producto?: string;
  descripcion_producto?: string;
  lote: string | null;
  bodega_origen: string | null;
  bodega_destino: string | null;
  proveedor?: string;
  proveedor_nombre?: string;
  pais?: string;
  calidad?: string;
  observaciones?: string;
  cantidad: string;
  entrada?: string;
  salida?: string;
  saldo_resultante?: number;
  editado?: boolean;
  documento_ref: string | null;
  usuario: string;
  estado?: string;
  has_audit?: boolean;
  movimiento_id?: number;
}

// Legacy types (mantener compatibilidad)
export interface Sede {
  id: number;
  nombre: string;
  location: string;
  status: 'activo' | 'inactivo';
  num_areas?: number;
  num_users?: number;
  num_bodegas?: number;
  num_ordenes?: number;
}

export interface Area {
  id: number;
  nombre: string;
  sede: number;
}

// Módulo 5: MRP y Auditoría Global
export interface RequerimientoMaterial {
  id: number;
  producto_requerido: number;
  producto_nombre?: string;
  producto_codigo?: string;
  cantidad_necesaria: number;
  sede: number;
  sede_nombre?: string;
  origen_tipo: 'PEDIDO' | 'OP';
  origen_id: number;
  fecha_requerida?: string;
  fecha_calculo: string;
}

export interface OrdenCompraSugerida {
  id: number;
  producto: number;
  producto_nombre?: string;
  producto_codigo?: string;
  sede: number;
  sede_nombre?: string;
  cantidad_sugerida: number;
  estado: 'PENDIENTE' | 'APROBADA' | 'RECHAZADA';
  fecha_generacion: string;
  observaciones?: string;
}

export interface AuditLog {
  id: number;
  usuario?: number | null;
  usuario_nombre?: string;
  fecha_hora: string;
  ip_address?: string | null;
  object_id?: string | number;
  tabla_afectada: string;
  registro_id?: string;
  accion: 'CREATE' | 'UPDATE' | 'DELETE' | 'RESTORE';
  valor_anterior: unknown;
  valor_nuevo: unknown;
  justificacion?: string | null;
}

// Módulo 6: Manufactura MES (Motor Unificado)
export interface CorridaProduccion {
  id: number;
  codigo: string;
  sede: number;
  sede_nombre?: string;
  area: number;
  area_nombre?: string;
  linea?: number | null;
  linea_nombre?: string;
  maquina_principal?: number | null;
  maquina_principal_nombre?: string;
  modalidad: 'CONTINUA' | 'STOCK' | 'PEDIDO';
  orden_produccion?: number | null;
  orden_produccion_codigo?: string;
  plan_produccion?: number | null;
  plan_produccion_codigo?: string;
  detalle_plan?: number | null;
  pedido_venta?: number | null;
  turno: string;
  fecha_jornada: string;
  hora_inicio: string;
  hora_fin?: string | null;
  estado: 'en_proceso' | 'pausada' | 'finalizada' | 'anulada';
  supervisor?: number | null;
  supervisor_nombre?: string;
  observaciones?: string;
  operaciones_count?: number;
  fecha_creacion: string;
}

export interface ConsumoMaterial {
  id: number;
  operacion: number;
  lote_origen?: number | null;
  lote_origen_codigo?: string;
  producto: number;
  producto_codigo?: string;
  producto_descripcion?: string;
  bodega_origen: number;
  bodega_origen_nombre?: string;
  cantidad_consumida: string | number;
  costo_unitario: string | number;
}

export interface ProduccionSalida {
  id: number;
  operacion: number;
  lote_generado: number;
  lote_generado_codigo?: string;
  producto: number;
  producto_codigo?: string;
  producto_descripcion?: string;
  bodega_destino: number;
  bodega_destino_nombre?: string;
  cantidad_neta: string | number;
  clasificacion_calidad: 'primera' | 'segunda' | 'saldo';
  peso_bruto: string | number;
  tara: string | number;
  unidades_empaque: number;
  cantidad_metros?: string | number | null;
}

export interface MermaDesperdicio {
  id: number;
  operacion: number;
  peso_merma: string | number;
  tipo_merma: string;
  tipo_merma_display?: string;
  es_subproducto_vendible: boolean;
  producto_subproducto?: number | null;
  bodega_subproducto?: number | null;
}

export interface OperacionProduccion {
  id: number;
  corrida: number;
  numero_secuencia: number;
  maquina: number;
  maquina_nombre?: string;
  proceso?: number | null;
  proceso_nombre?: string;
  operario: number;
  operario_nombre?: string;
  hora_inicio: string;
  hora_fin?: string | null;
  estado: 'en_curso' | 'completada' | 'rechazada' | 'revertida';
  observaciones?: string;
  motivo_reversion?: string | null;
  consumos: ConsumoMaterial[];
  salidas: ProduccionSalida[];
  mermas: MermaDesperdicio[];
}

export interface DetallePlanProduccion {
  id: number;
  plan: number;
  producto_objetivo: number;
  producto_objetivo_codigo: string;
  producto_objetivo_descripcion: string;
  producto_objetivo_unidad: string;
  cantidad_planificada: string;
  cantidad_ejecutada: string;
  cantidad_aceptada: string;
  cantidad_segunda: string;
  saldo_pendiente: string;
  desviacion_porcentaje: string;
  cumplimiento_porcentaje: string;
  estado: 'pendiente' | 'en_proceso' | 'completado' | 'sobreproducido';
}

export interface PlanProduccion {
  id: number;
  codigo: string;
  sede: number;
  sede_nombre?: string;
  fecha_inicio: string;
  fecha_fin: string;
  estado: 'borrador' | 'aprobado' | 'en_ejecucion' | 'cerrado' | 'cancelado';
  supervisor?: number | null;
  supervisor_nombre?: string;
  observaciones?: string;
  detalles: DetallePlanProduccion[];
  fecha_creacion: string;
  fecha_modificacion: string;
}

export interface NecesidadReposicion {
  sede_id: number;
  sede_nombre: string;
  producto_id: number;
  producto_codigo: string;
  producto_descripcion: string;
  tipo: string;
  unidad_medida: string;
  stock_actual: string | number;
  stock_minimo: string | number;
  deficit: string | number;
}


