/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): cola disponible (202) / no disponible (503) / otro error;
 *   tarea lista / con error / que nunca termina.
 * - Análisis de valores límite (BVA): la tarea queda lista justo en el último intento permitido.
 * - Transición de estados: en_proceso → en_proceso → listo → descarga.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { obtenerReporte, ErrorReporteAsync } from './reporteAsync';

const mockGet = vi.fn();
vi.mock('./axios', () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

const encolado = (token = 'tok:1') => ({
  status: 202,
  data: new Blob([JSON.stringify({ token, estado_url: `/api/reporting/tareas/${token}/` })], { type: 'application/json' }),
  headers: {},
});
const estado = (cuerpo: Record<string, unknown>) => ({ status: 200, data: cuerpo, headers: {} });
const archivo = { status: 200, data: new Blob(['PK']), headers: { 'content-disposition': 'attachment; filename="x.xlsx"' } };

describe('obtenerReporte', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('test_obtenerReporte_dado_cola_disponible_cuando_la_tarea_termina_entonces_consulta_el_estado_y_descarga', async () => {
    mockGet
      .mockResolvedValueOnce(encolado())
      .mockResolvedValueOnce(estado({ estado: 'en_proceso' }))
      .mockResolvedValueOnce(estado({ estado: 'listo', nombre: 'x.xlsx', vacio: false }))
      .mockResolvedValueOnce(archivo);

    const resultado = await obtenerReporte('/reporting/gerencial/ventas', { sede_id: '2' }, { intervaloMs: 0 });

    expect(mockGet).toHaveBeenNthCalledWith(1, '/reporting/gerencial/ventas', {
      params: { sede_id: '2', async: 'true' },
      responseType: 'blob',
    });
    expect(mockGet).toHaveBeenNthCalledWith(2, '/reporting/tareas/tok%3A1/');
    expect(mockGet).toHaveBeenNthCalledWith(4, '/reporting/tareas/tok%3A1/descarga/', { responseType: 'blob' });
    expect(resultado.data).toBe(archivo.data);
    expect(resultado.headers['content-disposition']).toContain('x.xlsx');
  });

  it('test_obtenerReporte_dado_cola_no_disponible_503_cuando_encola_entonces_descarga_en_modo_sincrono', async () => {
    mockGet.mockRejectedValueOnce({ response: { status: 503 } }).mockResolvedValueOnce(archivo);

    const resultado = await obtenerReporte('/reporting/export/kardex', { bodega_id: '1' }, { intervaloMs: 0 });

    expect(mockGet).toHaveBeenLastCalledWith('/reporting/export/kardex', {
      params: { bodega_id: '1' },
      responseType: 'blob',
    });
    expect(resultado.data).toBe(archivo.data);
  });

  it('test_obtenerReporte_dado_error_403_al_encolar_cuando_encola_entonces_propaga_el_error_sin_reintentar', async () => {
    const error = { response: { status: 403 } };
    mockGet.mockRejectedValueOnce(error);

    await expect(obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0 })).rejects.toBe(error);
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it('test_obtenerReporte_dado_respuesta_200_al_encolar_cuando_encola_entonces_la_devuelve_como_archivo', async () => {
    mockGet.mockResolvedValueOnce(archivo);

    const resultado = await obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0 });

    expect(resultado.data).toBe(archivo.data);
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it('test_obtenerReporte_dado_tarea_con_error_cuando_consulta_entonces_lanza_ErrorReporteAsync_con_el_detalle', async () => {
    mockGet
      .mockResolvedValueOnce(encolado())
      .mockResolvedValueOnce(estado({ estado: 'error', detail: 'No se pudo generar el reporte.' }));

    const promesa = obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0 });

    await expect(promesa).rejects.toBeInstanceOf(ErrorReporteAsync);
    await expect(promesa).rejects.toThrow('No se pudo generar el reporte.');
  });

  it('test_obtenerReporte_dado_tarea_lista_en_el_ultimo_intento_cuando_consulta_entonces_descarga', async () => {
    mockGet
      .mockResolvedValueOnce(encolado())
      .mockResolvedValueOnce(estado({ estado: 'en_proceso' }))
      .mockResolvedValueOnce(estado({ estado: 'listo' }))
      .mockResolvedValueOnce(archivo);

    const resultado = await obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0, maxIntentos: 2 });

    expect(resultado.data).toBe(archivo.data);
  });

  it('test_obtenerReporte_dado_tarea_que_no_termina_cuando_agota_los_intentos_entonces_lanza_ErrorReporteAsync', async () => {
    mockGet.mockResolvedValueOnce(encolado()).mockResolvedValue(estado({ estado: 'en_proceso' }));

    await expect(
      obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0, maxIntentos: 3 }),
    ).rejects.toBeInstanceOf(ErrorReporteAsync);
    expect(mockGet).toHaveBeenCalledTimes(4); // encolar + 3 consultas
  });

});
