/**
 * Traducción de errores de axios a mensajes accionables para el usuario.
 * =====================================================================
 * ISO 25010 — Usabilidad (protección contra errores) + Confiabilidad:
 * el usuario debe entender QUÉ falló y QUÉ hacer, diferenciando entre un
 * error suyo (validación 4xx) y un fallo técnico (5xx / red).
 *
 * El logging estructurado RFC 5424 por status ya lo hace el interceptor de
 * `lib/axios.ts`; este módulo solo resuelve el mensaje visible. Cada llamador
 * agrega el contexto de negocio (orden_id, operación) con su propio logger.
 */
import { AxiosError } from 'axios';

/** Extrae el detalle de validación de un cuerpo DRF `{campo: [msgs]}` o `{detail}`. */
function extraerDetalleValidacion(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null;
  const obj = data as Record<string, unknown>;
  if (typeof obj.detail === 'string') return obj.detail;
  // Algunos endpoints no-DRF devuelven { error: "..." }.
  if (typeof obj.error === 'string') return obj.error;
  const partes = Object.entries(obj)
    .filter(([, v]) => v != null)
    .map(([campo, v]) => `${campo}: ${Array.isArray(v) ? v.join(', ') : String(v)}`);
  return partes.length ? partes.join(' | ') : null;
}

/**
 * Devuelve un mensaje en español apto para `toast.error`, diferenciado por
 * código HTTP. `fallback` se usa solo cuando no se puede clasificar el error.
 */
export function getApiErrorMessage(
  error: unknown,
  fallback = 'Ocurrió un error inesperado. Intenta de nuevo.',
): string {
  const axErr = error as AxiosError<unknown>;
  const status = axErr?.response?.status;

  switch (status) {
    case 400:
      return extraerDetalleValidacion(axErr.response?.data)
        ?? 'Datos inválidos. Revisa los campos e intenta de nuevo.';
    case 401:
      return 'Tu sesión expiró. Vuelve a iniciar sesión.';
    case 403:
      return extraerDetalleValidacion(axErr.response?.data)
        ?? 'No tienes permiso para realizar esta acción.';
    case 404:
      return 'El recurso no existe o ya fue eliminado.';
    case 409:
      return 'El recurso cambió mientras trabajabas. Recarga e intenta de nuevo.';
    case 500:
    case 502:
    case 503:
    case 504:
      return 'Error del servidor. Si persiste, contacta al administrador.';
    default:
      break;
  }

  // Sin respuesta del servidor → problema de red / CORS / servicio caído.
  if (status === undefined && (axErr?.request || axErr?.code === 'ERR_NETWORK')) {
    return 'Sin conexión con el servidor. Verifica tu red e intenta de nuevo.';
  }
  return fallback;
}
