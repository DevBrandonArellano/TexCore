import { useState, useMemo } from 'react';
import { abreviar, toNum } from './utils';
import type { StockResumen } from '../../types/inventario';
import type { BodegaElegida } from './DrillDownModals';
import type { AlertaStock } from './types';

export function useStockEjecutivo() {
  const [alertas, setAlertas] = useState<AlertaStock[]>([]);
  // Totales calculados en el servidor (/inventory/stock/resumen/): el stock por lote de
  // varios años de operación no cabe en el navegador (prueba de carga 2026-10-06).
  const [resumenStock, setResumenStock] = useState<StockResumen | null>(null);
  const [busquedaAlertas, setBusquedaAlertas] = useState('');
  const [bodegaSeleccionada, setBodegaSeleccionada] = useState<BodegaElegida | null>(null);

  const stockPorBodega = useMemo(() =>
    (resumenStock?.por_bodega ?? [])
      .map(b => ({
        name: abreviar(b.bodega, 16),
        fullBodegaName: b.bodega,
        bodegaId: b.bodega_id,
        value: Math.round(toNum(b.cantidad) * 100) / 100,
      }))
      .filter(d => d.value > 0).sort((a, b) => b.value - a.value),
    [resumenStock]);

  const alertasFiltradas = useMemo(() => {
    if (!busquedaAlertas.trim()) return alertas;
    const q = busquedaAlertas.trim().toLowerCase();
    return alertas.filter(a =>
      a.producto_codigo?.toLowerCase().includes(q) || a.producto?.toLowerCase().includes(q)
    );
  }, [alertas, busquedaAlertas]);

  const topAlertas = useMemo(() =>
    [...alertasFiltradas]
      .sort((a, b) => (b.faltante ?? 0) - (a.faltante ?? 0)).slice(0, 8)
      .map(a => ({ name: a.producto_codigo || abreviar(a.producto, 15), faltante: a.faltante ?? 0 })),
    [alertasFiltradas]);

  return {
    alertas,
    setAlertas,
    resumenStock,
    setResumenStock,
    busquedaAlertas,
    setBusquedaAlertas,
    bodegaSeleccionada,
    setBodegaSeleccionada,
    stockPorBodega,
    alertasFiltradas,
    topAlertas,
  };
}
