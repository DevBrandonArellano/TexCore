import apiClient from '../axios';
import type { ConsumoLoteDetalle, GenealogiaResponse } from '../../types/produccion';
import type {
  CadenaMateriasPrimas,
  CostoLote,
  FichaLote,
  FiltrosLotes,
  MovimientosLote,
  PaginaLotes,
  ResumenHoyLotes,
} from '../../types/lotes';

export type DireccionGenealogia = 'atras' | 'adelante';

/**
 * Repository de lotes de producción: único punto de acceso a sus endpoints.
 * Los componentes no arman URLs ni normalizan respuestas.
 */
export const lotesApi = {
  async listar(pagina: number, tamanoPagina: number, filtros: FiltrosLotes = {}): Promise<PaginaLotes> {
    const res = await apiClient.get<PaginaLotes>('/lotes-produccion/', {
      params: { ...filtros, page: pagina, page_size: tamanoPagina },
    });
    return res.data;
  },

  async resumenHoy(): Promise<ResumenHoyLotes> {
    const res = await apiClient.get<ResumenHoyLotes>('/lotes-produccion/resumen-hoy/');
    return res.data;
  },

  async ficha(loteId: number): Promise<FichaLote> {
    const res = await apiClient.get<FichaLote>(`/lotes-produccion/${loteId}/genealogia/`);
    return res.data;
  },

  async genealogia(codigoLote: string, direccion: DireccionGenealogia): Promise<GenealogiaResponse> {
    const res = await apiClient.get<GenealogiaResponse>('/corridas-produccion/trazabilidad-lote/', {
      params: { codigo: codigoLote, direccion },
    });
    return res.data;
  },

  async movimientos(codigoLote: string): Promise<MovimientosLote> {
    const res = await apiClient.get<MovimientosLote>(
      `/inventory/lotes/${encodeURIComponent(codigoLote)}/movimientos/`,
    );
    return res.data;
  },

  async materiasPrimas(loteId: number): Promise<CadenaMateriasPrimas> {
    const res = await apiClient.get<CadenaMateriasPrimas>('/trazabilidad/lote-produccion/', {
      params: { lote_id: loteId },
    });
    return res.data;
  },

  /** Lotes de origen consumidos en la mezcla del lote (pocos por lote: se traen completos). */
  async consumos(loteId: number): Promise<ConsumoLoteDetalle[]> {
    const res = await apiClient.get<{ results: ConsumoLoteDetalle[] } | ConsumoLoteDetalle[]>(
      '/consumo-lote-detalle/', { params: { lote_produccion: loteId, page_size: 500 } },
    );
    return Array.isArray(res.data) ? res.data : res.data.results;
  },

  /** Desglose de costos F0-002 (el servidor lo calcula o recalcula). */
  async costo(loteId: number): Promise<CostoLote> {
    const res = await apiClient.get<CostoLote>(`/lotes-produccion/${loteId}/obtener-costo/`);
    return res.data;
  },
};
