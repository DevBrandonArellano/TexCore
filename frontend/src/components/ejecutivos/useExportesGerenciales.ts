import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';

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
    try {
      const res = await apiClient.get(`/reporting/${ruta}`, { params: { ...params, format: 'xlsx' }, responseType: 'blob' });
      descargarBlob(res.data as Blob, nombre);
      toast.success('Reporte descargado');
    } catch {
      toast.error('Error al descargar el reporte');
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
