import { useState, useMemo } from 'react';
import { abreviar, toNum } from './utils';
import type { StockItem } from './DrillDownModals';
import type { AlertaStock } from './types';

export function useStockEjecutivo() {
  const [alertas, setAlertas] = useState<AlertaStock[]>([]);
  const [stock, setStock] = useState<StockItem[]>([]);
  const [busquedaAlertas, setBusquedaAlertas] = useState('');
  const [bodegaSeleccionada, setBodegaSeleccionada] = useState<string | null>(null);

  const stockPorBodega = useMemo(() => {
    const map = new Map<string, number>();
    stock.forEach(s => map.set(s.bodega, (map.get(s.bodega) ?? 0) + toNum(s.cantidad)));
    return Array.from(map.entries())
      .map(([name, value]) => ({ name: abreviar(name, 16), fullBodegaName: name, value: Math.round(value * 100) / 100 }))
      .filter(d => d.value > 0).sort((a, b) => b.value - a.value);
  }, [stock]);

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
    stock,
    setStock,
    busquedaAlertas,
    setBusquedaAlertas,
    bodegaSeleccionada,
    setBodegaSeleccionada,
    stockPorBodega,
    alertasFiltradas,
    topAlertas,
  };
}
