/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): cola disponible (202) / no disponible (503) / otro error;
 *   tarea lista / con error / que nunca termina.
 * - Análisis de valores límite (BVA): la tarea queda lista justo en el último intento permitido.
 * - Transición de estados: en_proceso → en_proceso → listo → descarga.
 * - EP de la ruta: reporte pesado (cola) / liviano (síncrono directo).
 * - EP del sondeo: fallo transitorio (502/504/red) tolerado / fallo definitivo (404) / fallos seguidos.
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

  it('test_obtenerReporte_dado_alAvanzar_cuando_la_tarea_avanza_entonces_informa_la_espera_y_la_descarga', async () => {
    mockGet
      .mockResolvedValueOnce(encolado())
      .mockResolvedValueOnce(estado({ estado: 'en_proceso' }))
      .mockResolvedValueOnce(estado({ estado: 'listo' }))
      .mockResolvedValueOnce(archivo);
    const alAvanzar = vi.fn();

    await obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0, alAvanzar });

    expect(alAvanzar.mock.calls.map(([a]) => a.fase)).toEqual(['en_cola', 'en_cola', 'descargando']);
    expect(alAvanzar.mock.calls[0][0].segundos).toBeGreaterThanOrEqual(0);
  });

  it('test_obtenerReporte_dado_modo_sincrono_503_cuando_descarga_entonces_no_informa_espera_en_cola', async () => {
    mockGet.mockRejectedValueOnce({ response: { status: 503 } }).mockResolvedValueOnce(archivo);
    const alAvanzar = vi.fn();

    await obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0, alAvanzar });

    expect(alAvanzar).not.toHaveBeenCalled();
  });

  // Hallazgo 9-nov-2026: un exporte liviano no espera la cola detrás de los pesados.
  it('test_obtenerReporte_dado_reporte_liviano_cuando_exporta_entonces_lo_pide_directo_sin_encolar', async () => {
    mockGet.mockResolvedValueOnce(archivo);
    const alAvanzar = vi.fn();

    const resultado = await obtenerReporte('/reporting/export/stock-bajo', { bodega_id: '1' }, { intervaloMs: 0, alAvanzar });

    expect(mockGet).toHaveBeenCalledTimes(1);
    expect(mockGet).toHaveBeenCalledWith('/reporting/export/stock-bajo', { params: { bodega_id: '1' }, responseType: 'blob' });
    expect(resultado.data).toBe(archivo.data);
    expect(alAvanzar).not.toHaveBeenCalled();
  });

  it.each(['/reporting/export/productos', '/reporting/export/usuarios', '/reporting/export/stock-cero', '/reporting/gerencial/deudores'])(
    'test_obtenerReporte_dado_liviano_%s_cuando_exporta_entonces_no_encola',
    async (ruta) => {
      mockGet.mockResolvedValueOnce(archivo);
      await obtenerReporte(ruta, {}, { intervaloMs: 0 });
      expect(mockGet.mock.calls[0][1].params).not.toHaveProperty('async');
    },
  );

  // Hallazgo 9-nov-2026: un solo fallo transitorio del sondeo abortaba un reporte que sí terminaba.
  it('test_obtenerReporte_dado_un_502_suelto_al_consultar_el_estado_cuando_sigue_entonces_descarga', async () => {
    mockGet
      .mockResolvedValueOnce(encolado())
      .mockRejectedValueOnce({ response: { status: 502 } })
      .mockRejectedValueOnce({ message: 'Network Error' })
      .mockResolvedValueOnce(estado({ estado: 'listo' }))
      .mockResolvedValueOnce(archivo);

    const resultado = await obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0 });

    expect(resultado.data).toBe(archivo.data);
  });

  it('test_obtenerReporte_dado_fallos_transitorios_seguidos_cuando_consulta_entonces_se_rinde_con_ErrorReporteAsync', async () => {
    mockGet
      .mockResolvedValueOnce(encolado())
      .mockRejectedValueOnce({ response: { status: 504 } })
      .mockRejectedValueOnce({ response: { status: 502 } })
      .mockRejectedValueOnce({ response: { status: 503 } });

    await expect(obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0 })).rejects.toBeInstanceOf(ErrorReporteAsync);
    expect(mockGet).toHaveBeenCalledTimes(4);
  });

  it('test_obtenerReporte_dado_404_al_consultar_el_estado_cuando_consulta_entonces_propaga_sin_reintentar', async () => {
    const error = { response: { status: 404 } };
    mockGet.mockResolvedValueOnce(encolado()).mockRejectedValueOnce(error);

    await expect(obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0 })).rejects.toBe(error);
    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  // Hallazgo 9-nov-2026: el 400 con el motivo (fecha mal formada) llegaba como Blob y se perdía.
  it('test_obtenerReporte_dado_400_con_motivo_al_encolar_cuando_encola_entonces_lanza_ErrorReporteAsync_con_ese_motivo', async () => {
    const cuerpo = new Blob([JSON.stringify({ detail: 'fecha_inicio debe tener formato YYYY-MM-DD.' })], { type: 'application/json' });
    mockGet.mockRejectedValueOnce({ response: { status: 400, data: cuerpo } });

    const promesa = obtenerReporte('/reporting/export/kardex', {}, { intervaloMs: 0 });

    await expect(promesa).rejects.toBeInstanceOf(ErrorReporteAsync);
    await expect(promesa).rejects.toThrow('fecha_inicio debe tener formato YYYY-MM-DD.');
  });
});
