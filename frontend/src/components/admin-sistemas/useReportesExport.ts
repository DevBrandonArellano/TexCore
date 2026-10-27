import { useState } from 'react';
import { toast } from 'sonner';
import { downloadBlob } from '../../lib/downloadBlob';
import { obtenerReporte, ErrorReporteAsync } from '../../lib/reporteAsync';
import { iniciarAvisoReporte } from '../../lib/avisoReporte';

import { estadoHttp } from '../../lib/apiError';

const REPORTES_QUE_REQUIEREN_BODEGA = [
  'kardex', 'stock-actual', 'stock-cero', 'stock-bajo', 'valorizacion', 'aging', 'rotacion', 'resumen-movimientos',
];

export function useReportesExport(rkBodega: string) {
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const handleExport = async (reportType: string, params: Record<string, string | number | undefined> = {}) => {
    if (REPORTES_QUE_REQUIEREN_BODEGA.includes(reportType) && !rkBodega) {
      toast.error('Debe seleccionar una bodega para este reporte.');
      return;
    }

    setLoading(prev => ({ ...prev, [reportType]: true }));
    // Aviso inmediato: el usuario sabe que el clic se registró aunque el reporte tarde.
    const aviso = iniciarAvisoReporte();
    try {
      const needsBodega = REPORTES_QUE_REQUIEREN_BODEGA.includes(reportType);
      const queryParams = { ...params, ...(needsBodega && { bodega_id: rkBodega }) };
      const endpoint = `/reporting/export/${reportType}`;

      // Reporte pesado: se genera en la cola (Celery) y se descarga al terminar.
      const resp = await obtenerReporte(endpoint, queryParams, { alAvanzar: aviso.avance });

      const disposition = resp.headers['content-disposition'];
      let filename = `${reportType}_report.xlsx`;
      if (disposition) {
        const match = disposition.match(/filename=([^;]+)/);
        if (match?.[1]) filename = match[1].trim().replace(/"/g, '');
      }
      downloadBlob(resp.data, filename);
      if (resp.headers['x-report-empty'] === 'true') {
        aviso.advertencia('El reporte no tiene datos para los filtros seleccionados.');
      } else {
        aviso.exito('Reporte generado exitosamente.');
      }
    } catch (e) {
      if (estadoHttp(e) === 404) {
        aviso.error('No se encontraron datos para los filtros seleccionados.');
      } else if (estadoHttp(e) === 403) {
        aviso.error('No tiene permisos para acceder a este reporte o bodega.');
      } else if (e instanceof ErrorReporteAsync) {
        aviso.error(e.message);
      } else {
        aviso.error('Error al generar el reporte. Intente de nuevo.');
      }
    } finally {
      setLoading(prev => ({ ...prev, [reportType]: false }));
    }
  };

  return { loading, handleExport };
}
