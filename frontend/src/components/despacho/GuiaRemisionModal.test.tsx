import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GuiaRemisionModal } from './GuiaRemisionModal';

const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { post: (...args: any[]) => mockPost(...args) },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

// jsdom no implementa createObjectURL/window.open — usados tras un envío exitoso.
beforeEach(() => {
  window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
  window.open = vi.fn();
});

async function completarCamposObligatorios() {
  await userEvent.type(screen.getByLabelText('Punto de partida *'), 'Planta Quito');
  const [inicio, fin] = screen.getAllByLabelText(/transporte \*/i);
  fireEventChange(inicio, '2026-08-25T08:00');
  fireEventChange(fin, '2026-08-25T18:00');
}

// userEvent.type no maneja bien inputs datetime-local en jsdom. React sobreescribe
// el setter nativo de `value` para su tracking interno, así que asignar
// `input.value = ...` directo no dispara el onChange controlado — hay que pasar
// por el setter nativo del prototipo antes de despachar el evento 'input'.
function fireEventChange(input: HTMLElement, value: string) {
  const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')!.set!;
  nativeSetter.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

describe('GuiaRemisionModal', () => {
  beforeEach(() => {
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado despachoId null cuando renderiza entonces el dialogo esta cerrado', () => {
    render(<GuiaRemisionModal despachoId={null} onOpenChange={vi.fn()} />);
    expect(screen.queryByText('Generar Guía de Remisión')).not.toBeInTheDocument();
  });

  it('dado despachoId asignado cuando renderiza entonces muestra el formulario', () => {
    render(<GuiaRemisionModal despachoId={5} onOpenChange={vi.fn()} />);
    expect(screen.getByText('Generar Guía de Remisión')).toBeInTheDocument();
    expect(screen.getByLabelText('Transporte propio')).toBeChecked();
  });

  it('dado campos obligatorios vacios cuando genera entonces muestra error y no llama al backend', async () => {
    render(<GuiaRemisionModal despachoId={5} onOpenChange={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /generar guía/i }));

    expect(toastErrorMock).toHaveBeenCalledWith('Completa punto de partida y fechas de transporte.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado transporte de tercero sin nombre cuando genera entonces muestra error', async () => {
    render(<GuiaRemisionModal despachoId={5} onOpenChange={vi.fn()} />);
    await completarCamposObligatorios();
    await userEvent.click(screen.getByLabelText('Transporte propio'));

    await userEvent.click(screen.getByRole('button', { name: /generar guía/i }));

    expect(toastErrorMock).toHaveBeenCalledWith('Indica el nombre del transportista contratado.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado formulario valido con transporte propio cuando genera entonces llama al endpoint correcto', async () => {
    mockPost.mockResolvedValueOnce({ data: new Blob(['%PDF-fake']) });
    const onOpenChange = vi.fn();
    render(<GuiaRemisionModal despachoId={7} onOpenChange={onOpenChange} />);
    await completarCamposObligatorios();

    await userEvent.click(screen.getByRole('button', { name: /generar guía/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/inventory/historial-despachos/7/guia-remision/',
      expect.objectContaining({
        motivo_traslado: 'Venta',
        punto_partida: 'Planta Quito',
        transporte_propio: true,
        transportista_nombre: undefined,
      }),
      { responseType: 'blob' },
    ));
    expect(toastSuccessMock).toHaveBeenCalledWith('Guía de remisión generada.');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('dado transporte de tercero completo cuando genera entonces incluye datos del transportista', async () => {
    mockPost.mockResolvedValueOnce({ data: new Blob(['%PDF-fake']) });
    render(<GuiaRemisionModal despachoId={7} onOpenChange={vi.fn()} />);
    await completarCamposObligatorios();
    await userEvent.click(screen.getByLabelText('Transporte propio'));
    await userEvent.type(screen.getByLabelText('Transportista (razón social) *'), 'Transportes Andinos');
    await userEvent.type(screen.getByLabelText('RUC transportista'), '1790000000099');

    await userEvent.click(screen.getByRole('button', { name: /generar guía/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/inventory/historial-despachos/7/guia-remision/',
      expect.objectContaining({
        transporte_propio: false,
        transportista_nombre: 'Transportes Andinos',
        transportista_ruc: '1790000000099',
      }),
      { responseType: 'blob' },
    ));
  });

  it('dado error del backend cuando genera entonces muestra el mensaje de error', async () => {
    mockPost.mockRejectedValueOnce({ response: { data: { motivo_traslado: 'Requerido.' } } });
    render(<GuiaRemisionModal despachoId={7} onOpenChange={vi.fn()} />);
    await completarCamposObligatorios();

    await userEvent.click(screen.getByRole('button', { name: /generar guía/i }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Requerido.'));
  });
});
