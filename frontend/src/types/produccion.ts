// frontend/src/types/produccion.ts

export interface ProductoDetail {
  id: number
  codigo: string
  descripcion: string
  tipo: string
}

export interface BodegaDetail {
  id: number
  nombre: string
}

export interface ComponenteMezclaOP {
  id: number
  producto: number
  producto_detail?: ProductoDetail
  bodega: number
  bodega_detail?: BodegaDetail
  porcentaje: string
  cantidad_kg: string
}

export interface OrdenProduccion {
  id: number
  codigo: string
  estado: 'pendiente' | 'en_proceso' | 'finalizada'
  prioridad: 'baja' | 'normal' | 'alta' | 'urgente'
  producto_entrada: number
  producto_entrada_detail?: ProductoDetail
  producto_salida: number
  producto_salida_detail?: ProductoDetail
  bodega_entrada: number
  bodega_salida: number
  peso_neto_requerido: string
  peso_producido: string
  componentes_mezcla: ComponenteMezclaOP[]
  inventario_descontado: boolean
  formula_color?: number
  bodega_quimicos?: number
  area?: number
  sede?: number
}

export interface ConsumoInput {
  lote_origen_id: number
  cantidad_kg: string
  genera_nuevo_lote: boolean
}

export interface RegistrarLotePayload {
  codigo_lote?: string
  peso_neto_producido: string
  peso_merma: string
  tipo_merma?: 'maquina' | 'material' | 'setup' | 'corte' | 'otro'
  clasificacion_calidad?: 'primera' | 'segunda' | 'saldo'
  maquina?: number
  operario?: number
  turno?: string
  hora_inicio?: string
  hora_final?: string
  unidades_empaque?: number
  presentacion?: string
  consumos?: ConsumoInput[]
  completar_orden?: boolean
}

export interface LoteProduccion {
  id: number
  codigo_lote: string
  orden_produccion: number
  peso_neto_producido: string
  peso_merma: string
  tipo_merma?: string
  clasificacion_calidad: string
  maquina?: number
  operario?: number
  turno: string
  hora_inicio?: string
  hora_final?: string
  consumos_detalle?: ConsumoLoteDetalle[]
}

export interface ConsumoLoteDetalle {
  id: number
  lote_produccion: number
  lote_origen: number
  lote_origen_codigo?: string
  cantidad_consumida: string
  genera_nuevo_lote: boolean
}

export interface MaquinaConMerma {
  id: number
  nombre: string
  estado: 'operativa' | 'mantenimiento' | 'inactiva'
  capacidad_maxima: string
  eficiencia_ideal: string
  producto_merma: number | null
  producto_merma_detail?: ProductoDetail
  bodega_merma: number | null
  bodega_merma_detail?: BodegaDetail
  area?: number
}

// --- Trazabilidad de transformaciones máquina a máquina ---

export interface TransformacionProducto {
  id: number
  orden_produccion: number
  etapa?: number | null
  numero_secuencia: number
  producto_entrada: number
  producto_entrada_detail?: ProductoDetail
  producto_salida: number
  producto_salida_detail?: ProductoDetail
  maquina: number
  maquina_nombre?: string
  operario?: number | null
  operario_nombre?: string
  peso_entrada: string
  peso_salida: string
  merma: string
  cantidad_entrada?: string | null
  cantidad_salida?: string | null
  fecha_inicio: string
  fecha_fin: string
  estado: 'completada' | 'rechazada'
  observaciones?: string
  fecha_creacion?: string
}

export interface RegistrarTransformacionPayload {
  maquina: number
  producto_salida: number
  producto_entrada?: number
  peso_entrada: string
  peso_salida: string
  cantidad_entrada?: string
  cantidad_salida?: string
  fecha_inicio: string
  fecha_fin: string
  estado?: 'completada' | 'rechazada'
  observaciones?: string
}

export interface TrazabilidadPaso {
  numero_secuencia: number
  producto_entrada: { id: number; codigo: string; descripcion: string } | null
  producto_salida: { id: number; codigo: string; descripcion: string } | null
  maquina: string | null
  operario: string | null
  peso_entrada: string
  peso_salida: string
  merma: string
  estado: string
  fecha_inicio: string
  fecha_fin: string
  observaciones?: string
}

export interface Trazabilidad {
  orden_codigo: string
  orden_id: number
  area: string | null
  sede_id: number | null
  producto_inicial: { id: number; codigo: string; descripcion: string } | null
  producto_final: { id: number; codigo: string; descripcion: string } | null
  peso_inicial: string
  peso_final: string
  merma_total: string
  merma_porcentaje: string
  pasos: TrazabilidadPaso[]
  siguiente: Trazabilidad | null
}
