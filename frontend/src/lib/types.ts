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
  description: string;
  chemicals: number[];
}

export interface DetalleFormula {
  id: number;
  formula_color: number;
  chemical: number;
  gramos_por_kilo: number;
}

// Módulo 4: Ventas y Clientes
export interface Cliente {
  id: number;
  ruc_cedula: string;
  nombre_razon_social: string;
  direccion_envio: string;
  nivel_precio: 'mayorista' | 'normal';
  tiene_beneficio: boolean;
  saldo_pendiente: number;
  limite_credito: number;
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
}

export interface Movimiento {
  id: number;
  fecha: string;
  tipo_movimiento: string;
  producto: string;
  lote: string | null;
  bodega_origen: string | null;
  bodega_destino: string | null;
  cantidad: string;
  documento_ref: string | null;
  usuario: string;
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
