import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { downloadBlob } from '../../lib/downloadBlob';

const REPORTES_QUE_REQUIEREN_BODEGA = ['kardex', 'stock-actual', 'aging', 'rotacion', 'resumen-movimientos'];

export function useReportesExport(rkBodega: string) {
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const handleExport = async (reportType: string, params: any = {}) => {
    if (REPORTES_QUE_REQUIEREN_BODEGA.includes(reportType) && !rkBodega) {
      toast.error('Debe seleccionar una bodega para este reporte.');
      return;
    }

    setLoading(prev => ({ ...prev, [reportType]: true }));
    try {
      const needsBodega = REPORTES_QUE_REQUIEREN_BODEGA.includes(reportType);
      const queryParams = { ...params, ...(needsBodega && { bodega_id: rkBodega }) };
      const endpoint = `/reporting/export/${reportType}`;

      const resp = await apiClient.get(endpoint, {
        params: queryParams,
        responseType: 'blob',
      });

      const disposition = resp.headers['content-disposition'];
      let filename = `${reportType}_report.xlsx`;
      if (disposition) {
        const match = disposition.match(/filename=([^;]+)/);
        if (match?.[1]) filename = match[1].trim().replace(/\"/g, '');
      }
      downloadBlob(resp.data, filename);
      toast.success('Reporte generado exitosamente.');
    } catch (e: any) {
      if (e.response?.status === 404) {
        toast.error('No se encontraron datos para los filtros seleccionados.');
      } else if (e.response?.status === 403) {
        toast.error('No tiene permisos para acceder a este reporte o bodega.');
      } else {
        toast.error('Error al generar el reporte. Intente de nuevo.');
      }
    } finally {
      setLoading(prev => ({ ...prev, [reportType]: false }));
    }
  };

  return { loading, handleExport };
}
