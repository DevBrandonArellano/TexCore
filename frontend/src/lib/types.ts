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
}

export interface Producto {
  id: number;
  codigo: string;
  descripcion: string;
  tipo: 'hilo' | 'tela' | 'subproducto' | 'quimico' | 'insumo';
  unidad_medida: 'kg' | 'metros' | 'unidades';
  stock_minimo: number;
  presentacion?: string;
  pais_origen?: string;
  calidad?: string;
  precio_base: number;
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

export interface KPIArea {
  area: string;
  total_produccion_kg: number;
  rendimiento_yield: number;
  tiempo_promedio_lote_min: number;
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
  fecha_creacion: string;
  sede: number;
  area?: number | null;
  area_nombre?: string;
  producto_nombre?: string;
  formula_color_nombre?: string;
  sede_nombre?: string;
  fecha_inicio_planificada?: string;
  fecha_fin_planificada?: string;
  maquina_asignada?: number | null;
  maquina_asignada_nombre?: string;
  operario_asignado?: number | null;
  operario_asignado_nombre?: string;
  observaciones?: string;
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
}

export interface FormulaColor {
  id: number;
  codigo: string;
  nombre_color: string;
  description?: string;
  tipo_sustrato: 'algodon' | 'poliester' | 'nylon' | 'mixto' | 'otro';
  tipo_sustrato_display?: string;
  version: number;
  estado: 'en_pruebas' | 'aprobada';
  estado_display?: string;
  creado_por?: number | null;
  creado_por_nombre?: string;
  fecha_creacion?: string;
  fecha_modificacion?: string;
  observaciones?: string;
  detalles?: any[];
  fases?: FaseReceta[];
}

export interface FaseReceta {
  id: number;
  nombre: 'pre_tratamiento' | 'tintura' | 'lavado' | 'suavizado' | 'auxiliares';
  nombre_display?: string;
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
}

export interface PedidoVenta {
  id: number;
  cliente: number;
  cliente_nombre?: string;
  vendedor_nombre?: string;
  guia_remision: string;
  fecha_pedido: string;
  fecha_despacho?: string;
  estado: 'pendiente' | 'despachado' | 'facturado';
  esta_pagado: boolean;
  sede: number;
  sede_nombre?: string;
  detalles?: DetallePedido[];
  total: number;
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
  usuario: number;
  usuario_nombre?: string;
  fecha_hora: string;
  ip_address: string;
  tabla_afectada: string;
  registro_id: string;
  accion: 'CREATE' | 'UPDATE' | 'DELETE' | 'RESTORE';
  valor_anterior: any;
  valor_nuevo: any;
  justificacion: string;
}

