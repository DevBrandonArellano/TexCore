export const fmt = (n: number, dec = 2) =>
  n.toLocaleString('es-EC', { minimumFractionDigits: dec, maximumFractionDigits: dec });

export const abreviar = (s: string, max = 20) =>
  s.length <= max ? s : s.slice(0, max - 1) + '…';

export const toNum = (v: unknown): number => {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v) || 0;
  return 0;
};

export const toArray = <T,>(d: unknown): T[] =>
  Array.isArray(d) ? d : ((d as { results?: T[] })?.results ?? []);
