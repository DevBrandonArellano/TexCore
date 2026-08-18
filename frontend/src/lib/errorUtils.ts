/**
 * Utility to format API errors into user-friendly messages with explanatory notes.
 * Strictly compliant with ISO 27001 (Information Security / Prevent Data Leakage)
 * & ISO 25010 (Usability & Informative Feedback).
 */

export interface FormattedError {
  message: string;
  note?: string;
  fieldErrors?: Record<string, string>;
}

/** Map of backend technical field names to friendly domain labels */
const FIELD_LABELS: Record<string, string> = {
  peso_neto_producido: 'Peso Neto Producido',
  peso_merma: 'Peso de Merma',
  tipo_merma: 'Tipo de Merma',
  unidades_empaque: 'Unidades de Empaque',
  presentacion: 'Presentación',
  maquina: 'Máquina Asignada',
  operario: 'Operario',
  turno: 'Turno',
  hora_inicio: 'Hora de Inicio',
  hora_final: 'Hora Final',
  justificacion: 'Justificación',
  motivo: 'Motivo',
  codigo_lote: 'Código de Lote',
  orden_produccion: 'Orden de Producción',
  monto: 'Monto de Pago',
  cliente: 'Cliente',
  bodega_origen: 'Bodega de Origen',
  bodega_destino: 'Bodega de Destino',
  lote_origen_id: 'Lote de Origen',
  cantidad_kg: 'Cantidad (Kg)',
};

/** Convert snake_case field key to clean title case if not in map */
function getFieldLabel(key: string): string {
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

/** Filter out technical leak terms (SQL, stack traces, URLs, DB tables, ORM details) */
function sanitizeMessage(text: string): string {
  if (!text) return 'Solicitud no procesada.';

  const str = String(text);

  // Check if string contains raw technical database/stacktrace/code leakage
  const leakPatterns = [
    /SQL/i,
    /IntegrityError/i,
    /CheckConstraint/i,
    /ForeignKey/i,
    /dbo\./i,
    /gestion_/i,
    /CK_/i,
    /FK_/i,
    /PK_/i,
    /Traceback/i,
    /AxiosError/i,
    /\/api\//i,
    /http/i,
    /0x[0-9a-fA-F]+/i,
  ];

  const hasLeak = leakPatterns.some((pattern) => pattern.test(str));
  if (hasLeak) {
    return 'La operación no pudo ser procesada por una restricción de datos.';
  }

  return str;
}

export function formatApiError(error: any): FormattedError {
  if (!error) {
    return {
      message: 'Ocurrió un error inesperado.',
      note: 'Nota: Intente nuevamente o consulte al equipo de supervisión.',
    };
  }

  // Network / Offline errors (No tech details exposed)
  if (error.code === 'ERR_NETWORK' || !error.response) {
    return {
      message: 'Sin comunicación con la red central.',
      note: 'Nota: Verifique su conexión de red local en la planta.',
    };
  }

  const status = error.response?.status;
  const data = error.response?.data;

  // 403 Forbidden
  if (status === 403) {
    return {
      message: 'Acceso restringido.',
      note: 'Nota: Su usuario no cuenta con los permisos o rol requeridos para esta acción.',
    };
  }

  // 500+ Internal Server Error (Sanitized - no DB stack traces exposed)
  if (status >= 500) {
    return {
      message: 'No se pudo completar la operación.',
      note: 'Nota: Inconveniente en el servicio central. Si persiste, notifique a soporte con la fecha y hora actual.',
    };
  }

  // Raw HTML string or non-JSON responses from server (e.g. 502/504 gateways)
  if (typeof data === 'string') {
    const cleanStr = sanitizeMessage(data);
    return {
      message: cleanStr.startsWith('<') ? 'Respuesta no válida del servidor.' : cleanStr,
      note: 'Nota: Verifique los datos ingresados e intente de nuevo.',
    };
  }

  let rawErrorMsg = typeof data?.error === 'object' ? data?.error?.message : data?.error;
  let mainMessage = data?.detail || rawErrorMsg || data?.non_field_errors?.[0];
  const fieldErrors: Record<string, string> = {};

  if (data && typeof data === 'object' && !Array.isArray(data)) {
    Object.entries(data).forEach(([key, val]) => {
      if (key !== 'detail' && key !== 'error' && key !== 'non_field_errors') {
        const strVal = Array.isArray(val) ? String(val[0]) : String(val);
        fieldErrors[getFieldLabel(key)] = sanitizeMessage(strVal);
      }
    });
  }

  if (!mainMessage) {
    const fieldKeys = Object.keys(fieldErrors);
    if (fieldKeys.length > 0) {
      const firstKey = fieldKeys[0];
      mainMessage = `${firstKey}: ${fieldErrors[firstKey]}`;
    } else {
      mainMessage = 'Solicitud no procesada.';
    }
  }

  mainMessage = sanitizeMessage(String(mainMessage));

  // Determine user-friendly explanatory note based on business context
  let note = 'Nota: Por favor revise la información ingresada en el formulario.';

  const msgLower = mainMessage.toLowerCase();
  if (msgLower.includes('merma') && (msgLower.includes('mayor') || msgLower.includes('excede') || msgLower.includes('superar'))) {
    note = 'Nota: La merma registrada no puede ser superior a la cantidad requerida en la orden de producción.';
  } else if (msgLower.includes('permiso') || msgLower.includes('área') || msgLower.includes('area')) {
    note = 'Nota: Asegúrese de estar operando dentro del área asignada a su turno.';
  } else if (msgLower.includes('justificacion') || msgLower.includes('motivo') || msgLower.includes('justificación')) {
    note = 'Nota: Ingrese un motivo claro de al menos 10 caracteres para el registro de auditoría.';
  } else if (msgLower.includes('positivo') || msgLower.includes('rango') || msgLower.includes('mayor a 0')) {
    note = 'Nota: Verifique que las cantidades ingresadas sean valores numéricos mayores a cero.';
  }

  return {
    message: mainMessage,
    note,
    fieldErrors: Object.keys(fieldErrors).length > 0 ? fieldErrors : undefined,
  };
}
