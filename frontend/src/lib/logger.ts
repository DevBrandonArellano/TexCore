/**
 * RFC 5424 — Frontend Structured Logger
 * ======================================
 * Implementa los niveles de severidad y el formato de datos estructurados
 * de RFC 5424 (IETF Syslog Protocol) adaptados al entorno browser/Node.
 *
 * En browser NO es posible emitir syslog UDP/TCP directamente.
 * Este módulo:
 *   1. Mapea los 8 niveles de severidad RFC 5424
 *   2. Formatea cada entrada con campos obligatorios del estándar
 *   3. Emite a console con el nivel correcto
 *   4. En producción envía al endpoint /api/logs/ (backend lo re-emite en RFC 5424)
 *
 * Uso:
 *   import { logger } from '@/lib/logger';
 *   logger.info('Dashboard cargado', { entity: 'EjecutivosDashboard', sede_id: '3' });
 *   logger.error('Fallo en exportación', { report: 'ventas', error: 'timeout' });
 */

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

/** Niveles de severidad RFC 5424 §6.2.1 */
export const Severity = {
  EMERGENCY: 0, // emerg  — sistema inutilizable
  ALERT:     1, // alert  — acción inmediata requerida
  CRITICAL:  2, // crit   — condición crítica
  ERROR:     3, // err    — error en operación
  WARNING:   4, // warning
  NOTICE:    5, // notice — condición normal pero significativa
  INFO:      6, // info   — mensaje informativo
  DEBUG:     7, // debug
} as const;

export type SeverityLevel = (typeof Severity)[keyof typeof Severity];

/** Datos estructurados — equivalente al SD-ELEMENT de RFC 5424 */
export type StructuredData = Record<string, string | number | boolean>;

/** Entrada de log normalizada */
export interface LogEntry {
  /** Severidad RFC 5424 */
  severity: SeverityLevel;
  /** MSGID — nombre del módulo/componente que emite el log */
  msgid: string;
  /** Mensaje libre */
  message: string;
  /** Timestamp ISO 8601 UTC con milisegundos */
  timestamp: string;
  /** Datos estructurados (SD-ELEMENT) */
  sd: StructuredData;
}

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const APP_NAME = 'texcore-frontend';
const SD_ID    = 'texcore@32473';       // mismo SD-ID que el backend

// Facility 20 = local4 — reservado para el frontend en el ecosistema TexCore
const FACILITY = 20;

// Nivel mínimo de emisión — ajustable por variable de entorno de Vite
const MIN_SEVERITY: SeverityLevel =
  import.meta.env.DEV ? Severity.DEBUG : Severity.INFO;

// Endpoint de relay — el backend lo convierte a RFC 5424 real y lo reenvía
const LOG_RELAY_URL = '/api/logs/';

// ---------------------------------------------------------------------------
// Utilidades internas
// ---------------------------------------------------------------------------

function _timestamp(): string {
  const now = new Date();
  return now.toISOString().replace(/(\.\d{3})\d*Z/, '$1Z');
}

function _priority(severity: SeverityLevel): number {
  return FACILITY * 8 + severity;
}

/** Formatea como string RFC 5424 para debug local */
function _format(entry: LogEntry): string {
  const pri = _priority(entry.severity);
  const sdParts = Object.entries(entry.sd)
    .map(([k, v]) => `${k}="${String(v).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/]/g, '\\]')}"`)
    .join(' ');
  const sd = sdParts ? `[${SD_ID} ${sdParts}]` : '-';
  return `<${pri}>1 ${entry.timestamp} browser ${APP_NAME} - ${entry.msgid} ${sd} ${entry.message}`;
}

/** Mapea severidad → método de console */
function _consoleMethod(severity: SeverityLevel): 'debug' | 'info' | 'warn' | 'error' {
  if (severity <= Severity.ERROR)   return 'error';
  if (severity === Severity.WARNING) return 'warn';
  if (severity === Severity.INFO)    return 'info';
  return 'debug';
}

/** Envía la entrada al relay del backend (fire-and-forget) */
function _relay(entry: LogEntry): void {
  if (import.meta.env.DEV) return; // no relay en desarrollo
  try {
    navigator.sendBeacon(
      LOG_RELAY_URL,
      new Blob([JSON.stringify(entry)], { type: 'application/json' }),
    );
  } catch {
    // sendBeacon puede no estar disponible en SSR/tests — ignorar
  }
}

// ---------------------------------------------------------------------------
// Logger principal
// ---------------------------------------------------------------------------

class RFC5424Logger {
  private readonly _msgid: string;

  constructor(module: string) {
    // MSGID: máx 32 chars, puntos → guiones (igual que el backend)
    this._msgid = module.replace(/\./g, '-').slice(0, 32);
  }

  private _emit(severity: SeverityLevel, message: string, sd: StructuredData = {}): void {
    if (severity > MIN_SEVERITY) return; // filtrar por nivel mínimo (0=más urgente)

    const entry: LogEntry = {
      severity,
      msgid: this._msgid,
      message,
      timestamp: _timestamp(),
      sd,
    };

    // Emitir a console con formato RFC 5424 legible
    console[_consoleMethod(severity)](_format(entry));

    // Relay al backend solo para WARNING y superior
    if (severity <= Severity.WARNING) {
      _relay(entry);
    }
  }

  /** Nivel 0 — Sistema inutilizable */
  emergency(message: string, sd?: StructuredData): void {
    this._emit(Severity.EMERGENCY, message, sd);
  }

  /** Nivel 1 — Acción inmediata requerida */
  alert(message: string, sd?: StructuredData): void {
    this._emit(Severity.ALERT, message, sd);
  }

  /** Nivel 2 — Condición crítica */
  critical(message: string, sd?: StructuredData): void {
    this._emit(Severity.CRITICAL, message, sd);
  }

  /** Nivel 3 — Error en operación */
  error(message: string, sd?: StructuredData): void {
    this._emit(Severity.ERROR, message, sd);
  }

  /** Nivel 4 — Advertencia */
  warning(message: string, sd?: StructuredData): void {
    this._emit(Severity.WARNING, message, sd);
  }

  /** Nivel 5 — Condición normal pero significativa */
  notice(message: string, sd?: StructuredData): void {
    this._emit(Severity.NOTICE, message, sd);
  }

  /** Nivel 6 — Informativo */
  info(message: string, sd?: StructuredData): void {
    this._emit(Severity.INFO, message, sd);
  }

  /** Nivel 7 — Debug */
  debug(message: string, sd?: StructuredData): void {
    this._emit(Severity.DEBUG, message, sd);
  }
}

// ---------------------------------------------------------------------------
// Fábrica — crea un logger con el módulo como MSGID
// ---------------------------------------------------------------------------

/**
 * Crea un logger RFC 5424 para el módulo dado.
 *
 * @example
 * const logger = createLogger('EjecutivosDashboard');
 * logger.info('KPIs cargados', { sede_id: '3', tabs: '4' });
 * // Emite: <166>1 2026-04-13T14:23:01.543Z browser texcore-frontend - EjecutivosDashboard [texcore@32473 sede_id="3" tabs="4"] KPIs cargados
 */
export function createLogger(module: string): RFC5424Logger {
  return new RFC5424Logger(module);
}

/** Logger de aplicación global — para uso en lib/axios, ErrorBoundary, etc. */
export const logger = createLogger(APP_NAME);
