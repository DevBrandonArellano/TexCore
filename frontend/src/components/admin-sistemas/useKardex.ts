import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { downloadBlob } from '../../lib/downloadBlob';
import { toArray } from '../../lib/collections';
import { usePagination } from '../../hooks/usePagination';
import type { Bodega, Movimiento } from '../../lib/types';
import { ITEMS_PER_PAGE, calcularSaldoAcumulado } from './inventoryUtils';

export function useKardex(bodegas: Bodega[]) {
  const [selectedBodega, setSelectedBodega] = useState('all');
  const [selectedProducto, setSelectedProducto] = useState('all');
  const [tipoOperacion, setTipoOperacion] = useState('all'); // all, entrada, salida
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [kardexData, setKardexData] = useState<Movimiento[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const { currentPage, setCurrentPage, totalPages, paginatedItems: paginatedData } = usePagination(kardexData, ITEMS_PER_PAGE);

  const handleFetchKardex = async () => {
    setIsLoading(true);
    try {
      const params: any = {};
      if (selectedBodega !== 'all') params.bodega_id = selectedBodega;
      if (selectedProducto !== 'all') params.producto_id = selectedProducto;
      if (tipoOperacion !== 'all') params.tipo = tipoOperacion;
      if (fechaInicio) params.fecha_desde = fechaInicio;
      if (fechaFin) params.fecha_hasta = fechaFin;

      const response = await apiClient.get('/inventory/movimientos/', { params });

      let data: Movimiento[] = toArray<Movimiento>(response.data);

      // Cálculo de Saldo Dinámico si hay Producto + Bodega seleccionado
      if (selectedProducto !== 'all' && selectedBodega !== 'all' && data.length > 0) {
        const selectedBodegaObj = bodegas.find((b) => b.id.toString() === selectedBodega);
        data = calcularSaldoAcumulado(data, selectedBodegaObj?.nombre);
      }

      setKardexData(data);
      setCurrentPage(1);
    } catch (error) {
      toast.error('Error al consultar movimientos.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearFilters = () => {
    setSelectedBodega('all');
    setSelectedProducto('all');
    setTipoOperacion('all');
    setFechaInicio('');
    setFechaFin('');
    setKardexData([]);
    setCurrentPage(1);
  };

  const exportToCSV = () => {
    if (kardexData.length === 0) {
      toast.error("No hay datos para exportar");
      return;
    }

    const headers = ["Fecha", "Producto", "Bodega Origen", "Bodega Destino", "Tipo", "Cantidad", "Referencia"];
    if (selectedProducto !== 'all' && selectedBodega !== 'all') headers.push("Saldo");

    const csvContent = [
      headers.join(","),
      ...kardexData.map(row => [
        new Date(row.fecha).toLocaleString(),
        row.producto,
        row.bodega_origen || "-",
        row.bodega_destino || "-",
        row.tipo_movimiento,
        row.cantidad,
        `"${row.documento_ref || ''}"`,
        (row as any).saldo_acumulado ?? ""
      ].join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    downloadBlob(blob, `kardex_${new Date().toISOString().split('T')[0]}.csv`);
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
    paginatedData,
    handleFetchKardex,
    handleClearFilters,
    exportToCSV,
  };
}
