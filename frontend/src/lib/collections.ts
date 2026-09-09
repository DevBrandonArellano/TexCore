/**
 * Normaliza la respuesta de un endpoint DRF que puede venir paginada
 * (`{ results: T[] }`) o como array plano (`T[]`), según si el ViewSet
 * tiene paginación activada.
 *
 * Antes de esta utilidad, el patrón
 * `Array.isArray(x.data) ? x.data : (x.data as any).results || []`
 * estaba duplicado literalmente en ~15 sitios (useJefeAreaData,
 * VendedorDashboard, MRPDashboard, useKardex, useSedeSpecificData...),
 * cada uno generando 3 ramas de cobertura sin ejercitar — la mitad de
 * las ramas del proyecto. Centralizarlo aquí colapsa esas ramas en un
 * solo punto probado una vez.
 */
export function toArray<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[];
  const results = (data as { results?: T[] } | null | undefined)?.results;
  return Array.isArray(results) ? results : [];
}
