import apiClient from '../axios';
import type {
  ConsultaStockAFecha,
  FiltrosMateriaPrima,
  FiltrosStock,
  MateriaPrimaLote,
  PaginaMateriaPrima,
  PaginaStock,
  RecepcionMateriaPrima,
  StockAFechaFila,
  StockResumen,
} from '../../types/inventario';

/** Solo los filtros con valor; la búsqueda viaja sin espacios sobrantes. */
function paramsStock({ search, ...ids }: FiltrosStock) {
  const params: Record<string, string | number> = {};
  Object.entries(ids).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== '') params[clave] = valor;
  });
  if (search?.trim()) params.search = search.trim();
  return params;
}

/** Solo los filtros con valor: `disponibles` viaja como 'true' o no viaja. */
function paramsMateriaPrima({ proveedor, disponibles }: FiltrosMateriaPrima) {
  return {
    ...(proveedor ? { proveedor } : {}),
    ...(disponibles ? { disponibles: 'true' } : {}),
  };
}

/** Con certificado se envía multipart; sin él, JSON. */
function cuerpoRecepcion(datos: RecepcionMateriaPrima): RecepcionMateriaPrima | FormData {
  const { certificado_calidad: certificado, ...campos } = datos;
  if (!certificado) return campos;
  const form = new FormData();
  Object.entries(campos).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null) form.append(clave, String(valor));
  });
  form.append('certificado_calidad', certificado);
  return form;
}

/**
 * Repository de bodega: stock actual (paginado y resumen), materia prima (recepción
 * F0-001 y lotes recibidos) y stock a fecha de corte. Los componentes no arman URLs
 * ni cuerpos.
 */
export const inventarioApi = {
  async listarMateriaPrima(
    pagina: number, tamanoPagina: number, filtros: FiltrosMateriaPrima = {},
  ): Promise<PaginaMateriaPrima> {
    const res = await apiClient.get<PaginaMateriaPrima>('/materia-prima/', {
      params: { ...paramsMateriaPrima(filtros), page: pagina, page_size: tamanoPagina },
    });
    return res.data;
  },

  async registrarEntradaMateriaPrima(datos: RecepcionMateriaPrima): Promise<MateriaPrimaLote> {
    const res = await apiClient.post<MateriaPrimaLote>('/materia-prima/registrar-entrada/', cuerpoRecepcion(datos));
    return res.data;
  },

  /** Stock con existencias, paginado en el servidor (PaginacionAcotada, tope 500). */
  async listarStock(pagina: number, tamanoPagina: number, filtros: FiltrosStock = {}): Promise<PaginaStock> {
    const res = await apiClient.get<PaginaStock>('/inventory/stock/', {
      params: { ...paramsStock(filtros), page: pagina, page_size: tamanoPagina },
    });
    return res.data;
  },

  /** Totales por bodega para gráficos y KPI, sin traer las filas por lote. */
  async resumenStock(filtros: FiltrosStock = {}): Promise<StockResumen> {
    const res = await apiClient.get<StockResumen>('/inventory/stock/resumen/', { params: paramsStock(filtros) });
    return res.data;
  },

  async stockAFecha(consulta: ConsultaStockAFecha): Promise<StockAFechaFila[]> {
    const res = await apiClient.get<StockAFechaFila[]>('/inventory/retro-kardex/', { params: consulta });
    return res.data;
  },
};
