import { useState, useMemo } from 'react';
import type { ProduccionResumen, TendenciaDia } from './types';

export function useProduccionEjecutivo() {
  const [produccionResumen, setProduccionResumen] = useState<ProduccionResumen | null>(null);
  const [tendencia, setTendencia] = useState<TendenciaDia[]>([]);
  const [rangoTendencia, setRangoTendencia] = useState<number>(30); // 7, 15, 30, 90 días
  const [agrupacionTendencia, setAgrupacionTendencia] = useState<'diario' | 'semanal' | 'mensual'>('diario');

  const datosTendenciaProcesados = useMemo(() => {
    let raw = [...tendencia];
    raw.sort((a, b) => a.fecha.localeCompare(b.fecha));
    let filtered = raw.slice(-rangoTendencia);

    if (agrupacionTendencia === 'semanal') {
      const weeks: Record<string, { start: string; end: string; kg: number }> = {};
      filtered.forEach((item, index) => {
        const weekNum = Math.floor(index / 7) + 1;
        const key = `S${weekNum}`;
        if (!weeks[key]) weeks[key] = { start: item.fecha, end: item.fecha, kg: 0 };
        weeks[key].end = item.fecha;
        weeks[key].kg += item.kg;
      });
      return Object.entries(weeks).map(([name, data]) => ({
        fecha: `${name} (${data.start.slice(8)}-${data.end.slice(8)})`,
        kg: Math.round(data.kg * 100) / 100,
      }));
    }

    if (agrupacionTendencia === 'mensual') {
      const months: Record<string, { label: string; kg: number }> = {};
      filtered.forEach(item => {
        const key = item.fecha.slice(0, 7); // YYYY-MM
        const [y, m] = key.split('-');
        const label = `${['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][Number(m) - 1]} ${y}`;
        if (!months[key]) months[key] = { label, kg: 0 };
        months[key].kg += item.kg;
      });
      return Object.entries(months)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([, d]) => ({ fecha: d.label, kg: Math.round(d.kg * 100) / 100 }));
    }

    return filtered;
  }, [tendencia, rangoTendencia, agrupacionTendencia]);

  return {
    produccionResumen,
    setProduccionResumen,
    tendencia,
    setTendencia,
    rangoTendencia,
    setRangoTendencia,
    agrupacionTendencia,
    setAgrupacionTendencia,
    datosTendenciaProcesados,
  };
}
