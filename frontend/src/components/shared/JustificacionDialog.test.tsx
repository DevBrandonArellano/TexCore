import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JustificacionDialog } from './JustificacionDialog';

function montar(onConfirmar = vi.fn().mockResolvedValue(true), open = true) {
  const onClose = vi.fn();
  const props = {
    titulo: 'Eliminar orden OP-1',
    descripcion: 'La acción no se puede deshacer.',
    textoConfirmar: 'Eliminar',
    onConfirmar,
    onClose,
  };
  const utils = render(<JustificacionDialog open={open} {...props} />);
  return { onConfirmar, onClose, props, ...utils };
}

const campo = () => screen.getByLabelText('Justificación');
const confirmar = () => screen.getByRole('button', { name: 'Eliminar' });

describe('JustificacionDialog', () => {
  it('dado cerrado cuando renderiza entonces no muestra el diálogo', () => {
    montar(undefined, false);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  // BVA sobre la longitud mínima (10): 9 inválido, 10 válido.
  it('dado 9 caracteres cuando escribe entonces no permite confirmar', async () => {
    montar();
    await userEvent.type(campo(), '123456789');
    expect(confirmar()).toBeDisabled();
  });

  it('dado 10 caracteres cuando escribe entonces permite confirmar', async () => {
    montar();
    await userEvent.type(campo(), '1234567890');
    expect(confirmar()).toBeEnabled();
  });

  // EP: espacios no cuentan como justificación.
  it('dado solo espacios cuando escribe entonces no permite confirmar', async () => {
    montar();
    await userEvent.type(campo(), '              ');
    expect(confirmar()).toBeDisabled();
  });

  it('dado justificación válida y éxito cuando confirma entonces envía el texto recortado y cierra', async () => {
    const { onConfirmar, onClose } = montar();
    await userEvent.type(campo(), '  Orden duplicada  ');
    await userEvent.click(confirmar());
    expect(onConfirmar).toHaveBeenCalledWith('Orden duplicada');
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('dado fallo al confirmar cuando confirma entonces no cierra y rehabilita el botón', async () => {
    const { onClose } = montar(vi.fn().mockResolvedValue(false));
    await userEvent.type(campo(), 'Orden duplicada');
    await userEvent.click(confirmar());
    await waitFor(() => expect(confirmar()).toBeEnabled());
    expect(onClose).not.toHaveBeenCalled();
  });

  it('dado un texto escrito cuando cierra con Escape entonces llama a onClose y al reabrir el campo está vacío', async () => {
    const { onClose, rerender, props } = montar();
    await userEvent.type(campo(), 'Borrador de causa');
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
    rerender(<JustificacionDialog open={false} {...props} />);
    rerender(<JustificacionDialog open {...props} />);
    expect(campo()).toHaveValue('');
  });

  it('dado un texto escrito cuando cancela y reabre entonces el campo vuelve vacío', async () => {
    const { onClose, rerender, props } = montar();
    await userEvent.type(campo(), 'Borrador de causa');
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onClose).toHaveBeenCalled();
    rerender(<JustificacionDialog open={false} {...props} />);
    rerender(<JustificacionDialog open {...props} />);
    expect(campo()).toHaveValue('');
  });
});
