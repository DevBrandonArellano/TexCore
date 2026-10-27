import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import { obtenerReporte, ErrorReporteAsync } from '../../lib/reporteAsync';
import { iniciarAvisoReporte } from '../../lib/avisoReporte';

const descargarBlob = (blob: Blob, nombre: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

export function useExportesGerenciales(filtroSedeId: string) {
  const [reportFechas, setReportFechas] = useState({
    inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    fin: new Date().toISOString().split('T')[0],
  });
  const [descargando, setDescargando] = useState<string | null>(null);

  const exportar = useCallback(async (ruta: string, params: Record<string, string>, nombre: string) => {
    if (params.fecha_inicio && params.fecha_fin && params.fecha_inicio > params.fecha_fin) {
      toast.error('La fecha de inicio no puede ser posterior a la fecha de fin');
      return;
    }
    if (descargando) return;
    setDescargando(ruta);
    // Aviso inmediato: el usuario sabe que el clic se registró aunque el reporte tarde.
    const aviso = iniciarAvisoReporte();
    try {
      // Reporte pesado: se genera en la cola (Celery) y se descarga al terminar.
      const res = await obtenerReporte(`/reporting/${ruta}`, { ...params, format: 'xlsx' }, { alAvanzar: aviso.avance });
      descargarBlob(res.data as Blob, nombre);
      aviso.exito('Reporte descargado');
    } catch (e) {
      aviso.error(e instanceof ErrorReporteAsync ? e.message : 'Error al descargar el reporte');
    } finally {
      setDescargando(null);
    }
  }, [descargando]);

  const exportVentas = useCallback(() => exportar(
    'gerencial/ventas',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...((filtroSedeId && filtroSedeId !== 'todas') && { sede_id: filtroSedeId }) },
    `ventas_gerencial_${reportFechas.inicio}.xlsx`
  ), [exportar, reportFechas, filtroSedeId]);

  const exportTopClientes = useCallback(() => exportar(
    'gerencial/top-clientes',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...((filtroSedeId && filtroSedeId !== 'todas') && { sede_id: filtroSedeId }) },
    `top_clientes_${reportFechas.inicio}.xlsx`
  ), [exportar, reportFechas, filtroSedeId]);

  const exportDeudores = useCallback(() => exportar(
    'gerencial/deudores',
    { ...((filtroSedeId && filtroSedeId !== 'todas') && { sede_id: filtroSedeId }) },
    'clientes_deudores.xlsx'
  ), [exportar, filtroSedeId]);

  const exportOrdenes = useCallback(() => exportar(
    'produccion/ordenes',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...((filtroSedeId && filtroSedeId !== 'todas') && { sede_id: filtroSedeId }) },
    `ordenes_produccion_${reportFechas.inicio}.xlsx`
  ), [exportar, reportFechas, filtroSedeId]);

  const exportLotes = useCallback(() => exportar(
    'produccion/lotes',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...((filtroSedeId && filtroSedeId !== 'todas') && { sede_id: filtroSedeId }) },
    `lotes_produccion_${reportFechas.inicio}.xlsx`
  ), [exportar, reportFechas, filtroSedeId]);

  const exportTendencia = useCallback(() => exportar(
    'produccion/tendencia',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...((filtroSedeId && filtroSedeId !== 'todas') && { sede_id: filtroSedeId }) },
    `tendencia_produccion_${reportFechas.inicio}.xlsx`
  ), [exportar, reportFechas, filtroSedeId]);

  return {
    reportFechas,
    setReportFechas,
    descargando,
    exportVentas,
    exportTopClientes,
    exportDeudores,
    exportOrdenes,
    exportLotes,
    exportTendencia,
  };
}
