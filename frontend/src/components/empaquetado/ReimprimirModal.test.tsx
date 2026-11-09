/**
 * ReimprimirModal: reimpresión auditada de la etiqueta vigente de un lote.
 *
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): sin motivo (botón deshabilitado) / con motivo y detalle;
 *   impresión por Zebra / PDF; error del servidor; cancelar; con y sin código de lote.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReimprimirModal } from './ReimprimirModal';

const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({ default: { post: (...a: unknown[]) => mockPost(...a) } }));
const mockPrintLabel = vi.fn();
vi.mock('../../lib/printing', () => ({ printLabel: (...a: unknown[]) => mockPrintLabel(...a) }));
const { mockToast } = vi.hoisted(() => ({ mockToast: { success: vi.fn(), error: vi.fn(), loading: vi.fn() } }));
vi.mock('sonner', () => ({ toast: mockToast }));

global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

const RESPUESTA = { data: { zpl: '^XA^XZ', evento: { tipo_evento: 'REIMPRESION', version: 3, secuencia: 1 } } };

function montar(props: Partial<React.ComponentProps<typeof ReimprimirModal>> = {}) {
  const onOpenChange = vi.fn();
  const onReimpreso = vi.fn();
  render(<ReimprimirModal open loteId={9} codigoLote="L-9" onOpenChange={onOpenChange} onReimpreso={onReimpreso} {...props} />);
  return { onOpenChange, onReimpreso };
}

async function elegirMotivo() {
  await userEvent.click(screen.getByRole('combobox'));
  await userEvent.click(await screen.findByRole('option', { name: 'Etiqueta Perdida' }));
}

describe('ReimprimirModal', () => {
  beforeEach(() => {
    mockPost.mockReset();
    mockPrintLabel.mockReset();
    mockToast.success.mockReset();
    mockToast.error.mockReset();
  });

  it('dado sin motivo cuando se abre entonces el botón de reimprimir está deshabilitado', () => {
    montar();
    expect(screen.getByText(/Lote L-9 —/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Reimprimir/ })).toBeDisabled();
  });

  it('dado motivo y detalle cuando confirma entonces registra, imprime por Zebra, avisa y cierra', async () => {
    mockPost.mockResolvedValueOnce(RESPUESTA);
    mockPrintLabel.mockResolvedValueOnce('zebra');
    const { onOpenChange, onReimpreso } = montar();
    await elegirMotivo();
    await userEvent.type(screen.getByPlaceholderText(/etiqueta rasgada/), 'Se cayó al agua');
    await userEvent.click(screen.getByRole('button', { name: /Reimprimir/ }));

    await waitFor(() => expect(onReimpreso).toHaveBeenCalledWith('^XA^XZ'));
    expect(mockPost).toHaveBeenCalledWith('/lotes-produccion/9/reimprimir/', {
      motivo: 'PERDIDA', detalle_motivo: 'Se cayó al agua', formato: 'ZPL',
    });
    expect(mockPrintLabel).toHaveBeenCalledWith(9, '^XA^XZ', { tipo_evento: 'REIMPRESION', version: 3 });
    expect(mockToast.success).toHaveBeenCalledWith('Etiqueta reimpresa (v3). Enviado a la impresora Zebra.');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('dado error del servidor cuando confirma entonces muestra su mensaje y no cierra', async () => {
    mockPost.mockRejectedValueOnce({ response: { data: { detail: 'El lote no tiene etiqueta vigente.' } } });
    const { onOpenChange } = montar({ codigoLote: undefined });
    await elegirMotivo();
    await userEvent.click(screen.getByRole('button', { name: /Reimprimir/ }));
    await waitFor(() => expect(mockToast.error).toHaveBeenCalledWith('El lote no tiene etiqueta vigente.'));
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it('dado cancelar cuando se pulsa entonces cierra sin reimprimir', async () => {
    const { onOpenChange } = montar();
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado envío en curso cuando se intenta cerrar con Escape entonces no cierra', async () => {
    mockPost.mockReturnValue(new Promise(() => {}));
    const { onOpenChange } = montar();
    await elegirMotivo();
    await userEvent.click(screen.getByRole('button', { name: /Reimprimir/ }));
    await userEvent.keyboard('{Escape}');
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it('dado sin lote cuando confirma entonces no llama al servidor', async () => {
    montar({ loteId: null });
    await elegirMotivo();
    await userEvent.click(screen.getByRole('button', { name: /Reimprimir/ }));
    expect(mockPost).not.toHaveBeenCalled();
  });
});

