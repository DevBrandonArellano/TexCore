import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { downloadBlob } from '../../lib/downloadBlob';

export function useReportesVendedor(vendedorId: number | undefined) {
  const [reportFechas, setReportFechas] = useState({
    inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    fin: new Date().toISOString().split('T')[0]
  });

  const handleExportVentas = async () => {
    if (!vendedorId) {
      toast.error("No se pudo identificar al vendedor. Cierra sesión e inicia de nuevo.");
      return;
    }
    try {
      const url = `/reporting/vendedores/${vendedorId}/ventas?fecha_inicio=${reportFechas.inicio}&fecha_fin=${reportFechas.fin}&format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      downloadBlob(blob, `ventas_vendedor_${reportFechas.inicio}_${reportFechas.fin}.xlsx`);
      toast.success("Excel descargado correctamente.");
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error("No se encontraron datos para estos parámetros.");
      } else if (error.response?.status === 500) {
        toast.error("Error del servidor al generar el reporte. Revisa los logs.");
      } else if (error.response?.status === 422) {
        toast.error("Parámetros inválidos. Verifica las fechas.");
      } else {
        toast.error("Error al exportar el reporte.");
      }
    }
  };

  const handleExportTopClientes = async () => {
    try {
      const url = `/reporting/vendedores/${vendedorId}/top-clientes?fecha_inicio=${reportFechas.inicio}&fecha_fin=${reportFechas.fin}&format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      downloadBlob(new Blob([response.data]), `top_clientes_${reportFechas.inicio}_${reportFechas.fin}.xlsx`);
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error("No se encontraron clientes para estos parámetros.");
      } else {
        toast.error("Error al exportar el reporte.");
      }
    }
  };

  const handleExportDeudores = async () => {
    try {
      const url = `/reporting/vendedores/${vendedorId}/deudores?format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      downloadBlob(new Blob([response.data]), `clientes_deudores.xlsx`);
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error("No se encontraron deudores en su cartera.");
      } else {
        toast.error("Error al exportar el reporte.");
      }
    }
  };

  return {
    reportFechas, setReportFechas,
    handleExportVentas,
    handleExportTopClientes,
    handleExportDeudores,
  };
}
