import type { Maquina, LineaProduccion } from '../../lib/types';

// UX-1: semáforo de severidad para OEE — 85% es el benchmark de "clase mundial"
// (OEE for Operators — Productivity Press); 60% es un umbral típico de planta
// aceptable/en mejora. Por debajo de 60% se considera crítico.
export function claseSeveridadOee(oee: number): string {
  if (oee >= 0.85) return 'text-green-600';
  if (oee >= 0.60) return 'text-amber-600';
  return 'text-red-600';
}

// Agrupa máquinas por línea (TOC: la carga se calcula por área, no por línea).
// 'compartida' viene del backend (>1 línea activa) — fuente de verdad única.
export function agruparMaquinasPorLinea(lineas: LineaProduccion[], maquinas: Maquina[]) {
  const compartidaIds = new Set<number>(
    lineas.flatMap((l) =>
      (l.maquinas_detail ?? []).filter((d) => d.compartida).map((d) => d.id),
    ),
  );
  const asignadas = new Set<number>();
  const grupos = lineas.map((l) => {
    const ms = maquinas.filter((m) => l.maquinas.includes(m.id));
    ms.forEach((m) => asignadas.add(m.id));
    return { linea: l, maquinas: ms };
  });
  return { grupos, sinLinea: maquinas.filter((m) => !asignadas.has(m.id)), compartidaIds };
}
