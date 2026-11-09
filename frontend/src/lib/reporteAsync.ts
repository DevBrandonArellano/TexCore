/**
 * Exportación asíncrona de reportes pesados (Celery + Redis en el backend).
 *
 * Encola el reporte con `?async=true` (202 + token firmado), consulta
 * `/reporting/tareas/<token>/` hasta que está listo y descarga el archivo de
 * `/reporting/tareas/<token>/descarga/`. Si el entorno no tiene la cola (503),
 * pide el reporte en modo síncrono. Devuelve lo mismo que la descarga síncrona
 * (`data` + `headers`), así los hooks tratan igual ambos caminos.
 *
 * Los reportes livianos (catálogos y fotos del stock sin historial) se piden directo:
 * en la cola esperaban como mínimo 1,5 s y hacían fila detrás de los kardex pesados.
 */
import apiClient from './axios';
import { estadoHttp } from './apiError';

export interface ArchivoReporte {
  data: Blob;
  headers: Record<string, string | undefined>;
}

/** En qué paso va el reporte encolado, para mostrarle el progreso al usuario. */
export interface AvanceReporte {
  fase: 'en_cola' | 'descargando';
  /** Segundos desde que se pidió el reporte. */
  segundos: number;
}

export interface OpcionesReporteAsync {
  /** Pausa entre consultas de estado. */
  intervaloMs?: number;
  /** Consultas antes de rendirse (por defecto ~5 min con 1,5 s). */
  maxIntentos?: number;
  /** Se llama en cada consulta de estado y al empezar la descarga (solo en modo cola). */
  alAvanzar?: (avance: AvanceReporte) => void;
}

/** La tarea terminó con error o no terminó a tiempo. */
export class ErrorReporteAsync extends Error {
  constructor(mensaje: string) {
    super(mensaje);
    this.name = 'ErrorReporteAsync';
  }
}

type Params = Record<string, string | number | undefined>;

/** Reportes sin historial ni rango de fechas: responden en milisegundos en modo síncrono. */
const REPORTES_LIVIANOS = [
  /\/export\/(productos|usuarios|stock-cero|stock-bajo)$/,
  /\/gerencial\/deudores$/,
  /\/vendedores\/\d+\/deudores$/,
];
const esLiviano = (ruta: string) => REPORTES_LIVIANOS.some((patron) => patron.test(ruta));

/** Fallos del sondeo que se superan solos (proxy, red o reinicio del backend). */
const ESTADOS_TRANSITORIOS = new Set([502, 503, 504]);
const esTransitorio = (e: unknown) => {
  const estado = estadoHttp(e);
  return estado === undefined || ESTADOS_TRANSITORIOS.has(estado);
};
/** Fallos transitorios seguidos antes de rendirse (la tarea puede seguir corriendo). */
const MAX_FALLOS_SEGUIDOS = 3;

/** El 400 llega como Blob JSON por el responseType: se lee su motivo para mostrarlo. */
async function motivoDelRechazo(e: unknown): Promise<string | null> {
  const data = (e as { response?: { data?: unknown } })?.response?.data;
  if (!(data instanceof Blob)) return null;
  try {
    const { detail } = JSON.parse(await data.text()) as { detail?: unknown };
    return typeof detail === 'string' && detail ? detail : null;
  } catch {
    return null;
  }
}

const esperar = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

const comoArchivo = (resp: { data: unknown; headers: unknown }): ArchivoReporte => ({
  data: resp.data as Blob,
  headers: (resp.headers ?? {}) as Record<string, string | undefined>,
});

export async function obtenerReporte(
  ruta: string,
  params: Params,
  { intervaloMs = 1500, maxIntentos = 200, alAvanzar }: OpcionesReporteAsync = {},
): Promise<ArchivoReporte> {
  const inicio = Date.now();
  const avanzar = (fase: AvanceReporte['fase']) =>
    alAvanzar?.({ fase, segundos: Math.floor((Date.now() - inicio) / 1000) });
  if (esLiviano(ruta)) return comoArchivo(await apiClient.get(ruta, { params, responseType: 'blob' }));

  let encolado;
  try {
    encolado = await apiClient.get(ruta, { params: { ...params, async: 'true' }, responseType: 'blob' });
  } catch (e) {
    if (estadoHttp(e) === 400) {
      const motivo = await motivoDelRechazo(e);
      if (motivo) throw new ErrorReporteAsync(motivo);
    }
    if (estadoHttp(e) !== 503) throw e;
    return comoArchivo(await apiClient.get(ruta, { params, responseType: 'blob' }));
  }
  if (encolado.status !== 202) return comoArchivo(encolado);

  // Con responseType 'blob' el 202 llega como Blob JSON.
  const { token } = JSON.parse(await (encolado.data as Blob).text()) as { token: string };
  const base = `/reporting/tareas/${encodeURIComponent(token)}/`;

  let fallosSeguidos = 0;
  for (let intento = 0; intento < maxIntentos; intento++) {
    avanzar('en_cola');
    await esperar(intervaloMs);
    let data;
    try {
      ({ data } = await apiClient.get(base));
      fallosSeguidos = 0;
    } catch (e) {
      if (!esTransitorio(e)) throw e;
      if (++fallosSeguidos >= MAX_FALLOS_SEGUIDOS) {
        throw new ErrorReporteAsync('Se perdió la conexión con el servidor mientras se generaba el reporte. Intente de nuevo.');
      }
      continue;
    }
    if (data.estado === 'listo') {
      avanzar('descargando');
      return comoArchivo(await apiClient.get(`${base}descarga/`, { responseType: 'blob' }));
    }
    if (data.estado === 'error') {
      throw new ErrorReporteAsync(data.detail ?? 'No se pudo generar el reporte.');
    }
  }
  throw new ErrorReporteAsync('El reporte tardó demasiado. Intente de nuevo más tarde.');
}
