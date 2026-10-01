import type { LoteProduccion } from '../lib/types';

/** `/areas/{id}/reporte-eficiencia/` — producción del día (fecha local del servidor). Decimal como número o texto. */
export interface ReporteEficienciaArea {
  area_id: number;
  area_nombre: string;
  fecha_reporte: string;
  maquinas: {
    maquina_id: number;
    maquina_nombre: string;
    capacidad_maxima: number | string;
    produccion_total: number | string;
    eficiencia: number | string;
  }[];
  operarios: {
    operario_id: number;
    username: string;
    total_lotes: number;
    produccion_total_kg: number | string;
    promedio_kg_por_lote: number | string;
    horas_trabajadas_aprox: number;
    productividad_kg_hora: number;
  }[];
  produccion_total_area: number | string;
  eficiencia_promedio_area: number | string;
}

/** `/users/{id}/desempeno/` — producción de hoy y últimos 50 lotes del operario. */
export interface DesempenoOperario {
  operario: string;
  produccion_hoy_kg: number | string;
  lotes_hoy: number;
  ultimos_lotes: LoteProduccion[];
}

/** `/users/vendedores/` (solo ejecutivo y admin de sistemas). */
export interface VendedorResumen {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
}
