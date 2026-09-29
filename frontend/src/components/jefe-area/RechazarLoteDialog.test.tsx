import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RechazarLoteDialog } from './RechazarLoteDialog';

function montar(onConfirmar = vi.fn().mockResolvedValue(true), codigoLote: string | null = 'L-9') {
  const onClose = vi.fn();
  const utils = render(<RechazarLoteDialog codigoLote={codigoLote} onConfirmar={onConfirmar} onClose={onClose} />);
  return { onConfirmar, onClose, ...utils };
}

describe('RechazarLoteDialog', () => {
  it('dado código nulo cuando renderiza entonces no abre', () => {
    montar(undefined, null);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('dado motivo y rechazo exitoso cuando confirma entonces envía el motivo y cierra', async () => {
    const { onConfirmar, onClose } = montar();
    await userEvent.type(screen.getByLabelText('Motivo del rechazo'), 'Manchas');
    await userEvent.click(screen.getByRole('button', { name: 'Rechazar lote' }));
    expect(onConfirmar).toHaveBeenCalledWith('Manchas');
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('dado rechazo fallido cuando confirma entonces no cierra y rehabilita el botón', async () => {
    const { onClose } = montar(vi.fn().mockResolvedValue(false));
    await userEvent.type(screen.getByLabelText('Motivo del rechazo'), 'Manchas');
    await userEvent.click(screen.getByRole('button', { name: 'Rechazar lote' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Rechazar lote' })).toBeEnabled());
    expect(onClose).not.toHaveBeenCalled();
  });

  it('dado un motivo escrito cuando cierra con Escape y reabre entonces el campo vuelve vacío', async () => {
    const { onClose, rerender, onConfirmar } = montar();
    await userEvent.type(screen.getByLabelText('Motivo del rechazo'), 'Borrador');
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
    rerender(<RechazarLoteDialog codigoLote={null} onConfirmar={onConfirmar} onClose={onClose} />);
    rerender(<RechazarLoteDialog codigoLote="L-9" onConfirmar={onConfirmar} onClose={onClose} />);
    expect(screen.getByLabelText('Motivo del rechazo')).toHaveValue('');
  });
});
