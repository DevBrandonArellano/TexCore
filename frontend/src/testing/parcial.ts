/**
 * Solo para pruebas: un payload incompleto a propósito, tipado como el completo.
 *
 * Las pruebas de los manejadores de Gestión (crear/editar sede, área, producto, ...) solo
 * verifican que el dato llegue a la API; armar el objeto completo no agrega nada. Con
 * `parcial()` el tipo del parámetro se infiere del contexto y queda explícito que faltan
 * campos, en lugar de silenciar el chequeo con `any`.
 */
/** `NoInfer` de TypeScript 5.4 (el proyecto usa 5.2): T se infiere del contexto, no del argumento. */
type SinInferir<T> = [T][T extends unknown ? 0 : never];

export function parcial<T>(datos: Partial<SinInferir<T>>): T {
  return datos as T;
}
