import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { Movimiento } from '../../lib/types';
import { useReportesExport } from './useReportesExport';

/**
 * Kárdex paginado en el servidor (RNF-03 · TEX-22).
 *
 * - Con bodega + producto: /inventory/bodegas/{id}/kardex/ — el saldo lo calcula
 *   la base (SUM + SUM() OVER), así que cada página trae su saldo correcto sin
 *   descargar el historial.
 * - Sin alguno de los dos: listado /inventory/movimientos/ (sin saldo: sumar
 *   productos o bodegas distintas no tiene sentido físico).
 *
 * Antes se pedía /inventory/movimientos/ sin paginar en servidor, se leía solo
 * la primera página (50 filas) y el saldo se acumulaba en el navegador desde 0:
 * con más de 50 movimientos el saldo era incorrecto y el export venía truncado.
 */
export const KARDEX_PAGE_SIZE = 20;

export interface FilaKardex extends Movimiento {
  saldo_acumulado?: number;
  esEntrada: boolean;
  esSalida: boolean;
}

interface Consulta {
  bodega: string;
  producto: string;
  tipo: string;
  fechaInicio: string;
  fechaFin: string;
}

interface Pagina<T> {
  count: number;
  results: T[];
}

interface FilaKardexApi {
  id: number;
  fecha: string;
  tipo_movimiento: string;
  documento_ref: string | null;
  cantidad: string;
  entrada: string;
  salida: string;
  saldo: string;
  descripcion_producto: string;
  bodega_origen_nombre: string | null;
  bodega_destino_nombre: string | null;
  lote_codigo?: string | null;
  usuario: string;
}

interface FilaMovimientoApi {
  id: number;
  fecha: string;
  tipo_movimiento: string;
  cantidad: string;
  bodega_origen: number | null;
  bodega_destino: number | null;
  producto_nombre: string;
  bodega_origen_nombre: string | null;
  bodega_destino_nombre: string | null;
  lote_codigo?: string | null;
  usuario?: string;
  documento_ref: string | null;
}

const esModoKardex = (c: Consulta) => c.bodega !== 'all' && c.producto !== 'all';
const tipoActivo = (tipo: string) => (tipo !== 'all' ? tipo : undefined);

function paramsDeConsulta(c: Consulta, page: number): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  const tipo = tipoActivo(c.tipo);
  if (esModoKardex(c)) {
    params.producto_id = c.producto;
    if (tipo) params.tipo = tipo;
    if (c.fechaInicio) params.fecha_inicio = c.fechaInicio;
    if (c.fechaFin) params.fecha_fin = c.fechaFin;
  } else {
    if (c.bodega !== 'all') params.bodega_id = c.bodega;
    if (c.producto !== 'all') params.producto_id = c.producto;
    if (tipo) params.tipo = tipo;
    if (c.fechaInicio) params.fecha_desde = c.fechaInicio;
    if (c.fechaFin) params.fecha_hasta = c.fechaFin;
  }
  return { ...params, page, page_size: KARDEX_PAGE_SIZE };
}

function desdeKardex(f: FilaKardexApi): FilaKardex {
  return {
    ...f,
    producto: f.descripcion_producto,
    producto_nombre: f.descripcion_producto,
    bodega_origen: f.bodega_origen_nombre,
    bodega_destino: f.bodega_destino_nombre,
    lote: f.lote_codigo ?? null,
    saldo_acumulado: Number(f.saldo),
    esEntrada: Number(f.entrada) > 0,
    esSalida: Number(f.salida) > 0,
  } as FilaKardex;
}

function desdeMovimiento(f: FilaMovimientoApi, bodega: string): FilaKardex {
  const bodegaId = bodega !== 'all' ? Number(bodega) : null;
  return {
    ...f,
    producto: f.producto_nombre,
    producto_nombre: f.producto_nombre,
    bodega_origen: f.bodega_origen_nombre,
    bodega_destino: f.bodega_destino_nombre,
    lote: f.lote_codigo ?? null,
    usuario: f.usuario ?? '',
    esEntrada: bodegaId !== null && f.bodega_destino === bodegaId,
    esSalida: bodegaId !== null && f.bodega_origen === bodegaId,
  } as FilaKardex;
}

export function useKardex() {
  const [selectedBodega, setSelectedBodega] = useState('all');
  const [selectedProducto, setSelectedProducto] = useState('all');
  const [tipoOperacion, setTipoOperacion] = useState('all'); // all, entrada, salida
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [kardexData, setKardexData] = useState<FilaKardex[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  // Filtros del último "Consultar": paginar, recargar y exportar usan estos,
  // no lo que el usuario haya escrito después en el formulario sin consultar.
  const [consulta, setConsulta] = useState<Consulta | null>(null);

  const { loading: exportLoading, handleExport } = useReportesExport(
    consulta && consulta.bodega !== 'all' ? consulta.bodega : '',
  );

  const totalPages = Math.max(1, Math.ceil(totalCount / KARDEX_PAGE_SIZE));

  const cargarPagina = async (c: Consulta, page: number) => {
    setIsLoading(true);
    try {
      if (esModoKardex(c)) {
        const resp = await apiClient.get<Pagina<FilaKardexApi>>(
          `/inventory/bodegas/${c.bodega}/kardex/`, { params: paramsDeConsulta(c, page) });
        setKardexData(resp.data.results.map(desdeKardex));
        setTotalCount(resp.data.count);
      } else {
        const resp = await apiClient.get<Pagina<FilaMovimientoApi>>(
          '/inventory/movimientos/', { params: paramsDeConsulta(c, page) });
        setKardexData(resp.data.results.map((f) => desdeMovimiento(f, c.bodega)));
        setTotalCount(resp.data.count);
      }
      setPage(page);
    } catch {
      toast.error('Error al consultar movimientos.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchKardex = async () => {
    const nueva: Consulta = {
      bodega: selectedBodega, producto: selectedProducto, tipo: tipoOperacion, fechaInicio, fechaFin,
    };
    setConsulta(nueva);
    await cargarPagina(nueva, 1);
  };

  const setCurrentPage = async (page: number) => {
    if (!consulta) return;
    await cargarPagina(consulta, page);
  };

  /** Recarga la página actual (tras editar, eliminar o registrar merma). */
  const recargarPagina = async () => {
    if (!consulta) return;
    await cargarPagina(consulta, currentPage);
  };

  const handleClearFilters = () => {
    setSelectedBodega('all');
    setSelectedProducto('all');
    setTipoOperacion('all');
    setFechaInicio('');
    setFechaFin('');
    setKardexData([]);
    setTotalCount(0);
    setPage(1);
    setConsulta(null);
  };

  /** Excel generado en el servidor con los filtros consultados (TEX-22 CA-2). */
  const exportarExcel = async () => {
    if (!consulta) {
      toast.error('Consulte el kárdex antes de exportar.');
      return;
    }
    if (consulta.bodega === 'all') {
      toast.error('Seleccione una bodega para exportar el kárdex.');
      return;
    }
    const params: Record<string, string> = {};
    const tipo = tipoActivo(consulta.tipo);
    if (consulta.producto !== 'all') params.producto_id = consulta.producto;
    if (tipo) params.tipo = tipo;
    if (consulta.fechaInicio) params.fecha_inicio = consulta.fechaInicio;
    if (consulta.fechaFin) params.fecha_fin = consulta.fechaFin;
    await handleExport('kardex', params);
  };

  return {
    selectedBodega,
    setSelectedBodega,
    selectedProducto,
    setSelectedProducto,
    tipoOperacion,
    setTipoOperacion,
    fechaInicio,
    setFechaInicio,
    fechaFin,
    setFechaFin,
    kardexData,
    isLoading,
    currentPage,
    setCurrentPage,
    totalPages,
    totalCount,
    paginatedData: kardexData,
    mostrarSaldo: consulta !== null && esModoKardex(consulta),
    handleFetchKardex,
    recargarPagina,
    handleClearFilters,
    exportarExcel,
    exportando: !!exportLoading['kardex'],
  };
}
