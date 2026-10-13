import React from 'react';
import { CalendarClock, Factory, ShoppingCart } from 'lucide-react';
import { KpiCard } from './KpiCard';
import type { KpiEjecutivo } from './types';
import { fechaUltimaEjecucion } from './utils';

/**
 * KPI del MRP (ADR-012): sugerencias de compra vigentes (informativas), productos a
 * producir para el Plan Maestro y la fecha de la última ejecución. Lo usan el Resumen y
 * la pestaña MRP del panel ejecutivo.
 */
export function KpisMRP({ mrp, conSubtitulos = false }: { mrp?: KpiEjecutivo['mrp']; conSubtitulos?: boolean }) {
  return (
    <>
      <KpiCard
        titulo="Sugerencias de compra"
        valor={mrp?.sugerencias_compra ?? '—'}
        icon={<ShoppingCart className="w-4 h-4" />}
        subtitulo={conSubtitulos ? 'Material por comprar (informativo)' : undefined}
        alerta={(mrp?.sugerencias_compra ?? 0) > 0}
        alertaTexto="Hay material por reponer"
      />
      <KpiCard
        titulo="Productos a producir"
        valor={mrp?.productos_a_producir ?? '—'}
        icon={<Factory className="w-4 h-4" />}
        subtitulo={conSubtitulos ? 'Para el Plan Maestro (MTS)' : undefined}
      />
      <KpiCard
        titulo="Última ejecución MRP"
        valor={mrp ? fechaUltimaEjecucion(mrp.ultima_ejecucion) : '—'}
        icon={<CalendarClock className="w-4 h-4" />}
        subtitulo={conSubtitulos ? 'Más reciente de las sedes' : undefined}
      />
    </>
  );
}
