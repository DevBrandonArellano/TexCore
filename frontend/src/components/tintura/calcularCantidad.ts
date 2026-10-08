// Spec 2026-09-24 (D3): los litros son el dato canónico que fija el ingeniero
// tintorero contra el peso de la carga; la relación de baño se deriva, no se pide.
// Esta calculadora es una vista previa en vivo sobre la fórmula que se está
// editando (aún sin guardar), por eso sigue en el cliente; la dosificación real
// de una orden de producción ya se calcula en el backend (D4), ver
// /ordenes-produccion/{id}/calcular-dosificacion/.
export function calcularCantidad(
  tipo_calculo: 'gr_l' | 'pct',
  concentracion_gr_l: number | null | undefined,
  porcentaje: number | null | undefined,
  peso: number,
  litros: number
): { kg: number; gr: number } | null {
  if (peso <= 0 || litros <= 0) return null;

  let cantidadKg: number;
  if (tipo_calculo === 'gr_l') {
    cantidadKg = (litros * (concentracion_gr_l ?? 0)) / 1000;
  } else {
    cantidadKg = (peso * (porcentaje ?? 0)) / 100;
  }

  return { kg: cantidadKg, gr: cantidadKg * 1000 };
}
