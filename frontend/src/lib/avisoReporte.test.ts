/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Transición de estados: generando → (espera larga) → descargando → éxito / advertencia / error,
 *   siempre sobre el mismo toast.
 * - Análisis de valores límite (BVA): 9 s / 10 s de espera para el aviso de reporte grande.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { iniciarAvisoReporte } from './avisoReporte';

const { mockToast } = vi.hoisted(() => ({
  mockToast: { loading: vi.fn(() => 'aviso-1'), success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));
vi.mock('sonner', () => ({ toast: mockToast }));

describe('iniciarAvisoReporte', () => {
  beforeEach(() => {
    Object.values(mockToast).forEach((fn) => fn.mockClear());
  });

  it('test_aviso_dado_clic_en_exportar_cuando_inicia_entonces_muestra_un_toast_de_carga_inmediato', () => {
    iniciarAvisoReporte();
    expect(mockToast.loading).toHaveBeenCalledWith('Generando reporte…', expect.objectContaining({
      description: 'La descarga empezará automáticamente.',
    }));
  });

  it('test_aviso_dado_espera_de_9_segundos_cuando_avanza_entonces_no_cambia_el_mensaje', () => {
    const aviso = iniciarAvisoReporte();
    aviso.avance({ fase: 'en_cola', segundos: 9 });
    expect(mockToast.loading).toHaveBeenCalledTimes(1);
  });

  it('test_aviso_dado_espera_de_10_segundos_cuando_avanza_entonces_avisa_que_es_un_reporte_grande_en_el_mismo_toast', () => {
    const aviso = iniciarAvisoReporte();
    aviso.avance({ fase: 'en_cola', segundos: 10 });
    aviso.avance({ fase: 'en_cola', segundos: 12 }); // no repite el aviso
    expect(mockToast.loading).toHaveBeenCalledTimes(2);
    expect(mockToast.loading).toHaveBeenLastCalledWith('Generando reporte…', {
      id: 'aviso-1',
      description: 'Es un reporte grande, puede tardar un poco más.',
    });
  });

  it('test_aviso_dado_tarea_lista_cuando_descarga_entonces_cambia_a_descargando_en_el_mismo_toast', () => {
    const aviso = iniciarAvisoReporte();
    aviso.avance({ fase: 'descargando', segundos: 3 });
    expect(mockToast.loading).toHaveBeenLastCalledWith('Descargando archivo…', { id: 'aviso-1', description: undefined });
  });

  it('test_aviso_dado_fin_cuando_termina_entonces_reemplaza_el_toast_de_carga', () => {
    const aviso = iniciarAvisoReporte();
    aviso.exito('Reporte descargado');
    aviso.advertencia('Sin datos');
    aviso.error('Falló');
    expect(mockToast.success).toHaveBeenCalledWith('Reporte descargado', { id: 'aviso-1', description: undefined });
    expect(mockToast.warning).toHaveBeenCalledWith('Sin datos', { id: 'aviso-1', description: undefined });
    expect(mockToast.error).toHaveBeenCalledWith('Falló', { id: 'aviso-1', description: undefined });
  });
});
