import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RegistrosTransformacion } from './RegistrosTransformacion';

const mockTransformaciones = vi.fn();
vi.mock('../../lib/api/ordenesApi', () => ({
  ordenesApi: { transformaciones: (...a: unknown[]) => mockTransformaciones(...a) },
}));

describe('RegistrosTransformacion', () => {
  beforeEach(() => mockTransformaciones.mockReset());

  it('dado sin clic cuando monta entonces no consulta', () => {
    render(<RegistrosTransformacion ordenId={1} />);
    expect(mockTransformaciones).not.toHaveBeenCalled();
  });

  it('dado orden sin registros cuando los pide entonces lo indica', async () => {
    mockTransformaciones.mockResolvedValueOnce([]);
    render(<RegistrosTransformacion ordenId={1} />);
    await userEvent.click(screen.getByRole('button', { name: 'Ver todos los registros' }));
    expect(await screen.findByText('La orden no tiene registros de transformación.')).toBeInTheDocument();
  });

  it('dado error del servidor cuando los pide entonces lo muestra y permite reintentar', async () => {
    mockTransformaciones.mockRejectedValueOnce({ response: { status: 404, data: { detail: 'No encontrado.' } } });
    render(<RegistrosTransformacion ordenId={1} />);
    await userEvent.click(screen.getByRole('button', { name: 'Ver todos los registros' }));
    expect(await screen.findByText(/No encontrado|no se encontr/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ver todos los registros' })).toBeInTheDocument();
  });
});
