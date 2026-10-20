/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): blob sin tipo / blob con otro tipo / un pdf / un pdf abierto.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { abrirPdfEnPestana } from './abrirPdf';

describe('abrirPdfEnPestana', () => {
  let blobsCreados: Blob[];

  beforeEach(() => {
    blobsCreados = [];
    window.URL.createObjectURL = vi.fn((blob: Blob) => {
      blobsCreados.push(blob);
      return 'blob:mock-url';
    });
    window.URL.revokeObjectURL = vi.fn();
    window.open = vi.fn();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('test_abrirPdfEnPestana_dado_blob_sin_tipo_cuando_se_abre_entonces_el_blob_es_application_pdf', () => {
    abrirPdfEnPestana(new Blob(['%PDF-1.7']));

    expect(blobsCreados).toHaveLength(1);
    expect(blobsCreados[0].type).toBe('application/pdf');
  });

  it('test_abrirPdfEnPestana_dado_blob_con_otro_tipo_cuando_se_abre_entonces_fuerza_application_pdf', () => {
    abrirPdfEnPestana(new Blob(['%PDF-1.7'], { type: 'application/octet-stream' }));

    expect(blobsCreados[0].type).toBe('application/pdf');
  });

  it('test_abrirPdfEnPestana_dado_un_pdf_cuando_se_abre_entonces_lo_muestra_en_una_pestana_nueva', () => {
    abrirPdfEnPestana(new Blob(['%PDF-1.7']));

    expect(window.open).toHaveBeenCalledWith('blob:mock-url', '_blank');
  });

  it('test_abrirPdfEnPestana_dado_un_pdf_abierto_cuando_pasa_un_minuto_entonces_libera_la_url', () => {
    abrirPdfEnPestana(new Blob(['%PDF-1.7']));
    expect(window.URL.revokeObjectURL).not.toHaveBeenCalled();

    vi.advanceTimersByTime(60_000);

    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });
});
