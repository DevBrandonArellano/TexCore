import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditarPedidoModal } from './EditarPedidoModal';
import type { PedidoVenta } from '../../lib/types';

// Sin test propio hasta ahora.
const mockPatch = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { patch: (...args: any[]) => mockPatch(...args) },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

const PEDIDO: PedidoVenta = {
  id: 7, guia_remision: 'GR-001', fecha_despacho: '2026-01-01',
  valor_retencion: 0, esta_pagado: false,
} as any;

describe('EditarPedidoModal', () => {
  beforeEach(() => {
    mockPatch.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado pedido null cuando renderiza entonces el dialogo no esta abierto', () => {
    const { container } = render(<EditarPedidoModal pedido={null} onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it('dado pedido cargado sin cambios cuando renderiza entonces el boton guardar esta deshabilitado', () => {
    render(<EditarPedidoModal pedido={PEDIDO} onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(screen.getByRole('button', { name: /Guardar cambios/i })).toBeDisabled();
  });

  it('dado un cambio pero motivo menor a 10 caracteres cuando escribe entonces el boton sigue deshabilitado', async () => {
    render(<EditarPedidoModal pedido={PEDIDO} onClose={vi.fn()} onSuccess={vi.fn()} />);
    const guiaInput = screen.getByDisplayValue('GR-001');
    await userEvent.clear(guiaInput);
    await userEvent.type(guiaInput, 'GR-002');
    await userEvent.type(screen.getByPlaceholderText('Describe el motivo de la modificación...'), 'corto');
    expect(screen.getByRole('button', { name: /Guardar cambios/i })).toBeDisabled();
    expect(screen.getByText('5/10 caracteres mínimos')).toBeInTheDocument();
  });

  it('dado un cambio y motivo valido cuando guarda entonces solo envia los campos modificados', async () => {
    mockPatch.mockResolvedValue({});
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(<EditarPedidoModal pedido={PEDIDO} onClose={onClose} onSuccess={onSuccess} />);

    const guiaInput = screen.getByDisplayValue('GR-001');
    await userEvent.clear(guiaInput);
    await userEvent.type(guiaInput, 'GR-002');
    await userEvent.type(screen.getByPlaceholderText('Describe el motivo de la modificación...'), 'Corrección de guía por error de digitación');

    await userEvent.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    expect(mockPatch).toHaveBeenCalledWith('/pedidos-venta/7/modificar/', {
      motivo: 'Corrección de guía por error de digitación',
      guia_remision: 'GR-002',
    });
    expect(toastSuccessMock).toHaveBeenCalled();
    expect(onSuccess).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('dado marcar como pagado cuando cambia entonces incluye esta_pagado en el payload', async () => {
    mockPatch.mockResolvedValue({});
    render(<EditarPedidoModal pedido={PEDIDO} onClose={vi.fn()} onSuccess={vi.fn()} />);

    await userEvent.click(screen.getByLabelText('Marcar como pagado'));
    await userEvent.type(screen.getByPlaceholderText('Describe el motivo de la modificación...'), 'Cliente pagó en efectivo hoy');
    await userEvent.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    expect(mockPatch).toHaveBeenCalledWith('/pedidos-venta/7/modificar/', expect.objectContaining({ esta_pagado: true }));
  });

  it('dado cambio en valor de retencion cuando guarda entonces envia el valor numerico', async () => {
    mockPatch.mockResolvedValue({});
    render(<EditarPedidoModal pedido={PEDIDO} onClose={vi.fn()} onSuccess={vi.fn()} />);

    const retencionInput = screen.getByDisplayValue('0');
    await userEvent.clear(retencionInput);
    await userEvent.type(retencionInput, '15');
    await userEvent.type(screen.getByPlaceholderText('Describe el motivo de la modificación...'), 'Se aplica retención acordada');
    await userEvent.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    expect(mockPatch).toHaveBeenCalledWith('/pedidos-venta/7/modificar/', expect.objectContaining({ valor_retencion: 15 }));
  });

  it('dado fallo del backend cuando guarda entonces muestra el mensaje de error', async () => {
    mockPatch.mockRejectedValue({ response: { data: { error: 'El pedido ya no está pendiente' } } });
    render(<EditarPedidoModal pedido={PEDIDO} onClose={vi.fn()} onSuccess={vi.fn()} />);

    const guiaInput = screen.getByDisplayValue('GR-001');
    await userEvent.clear(guiaInput);
    await userEvent.type(guiaInput, 'GR-003');
    await userEvent.type(screen.getByPlaceholderText('Describe el motivo de la modificación...'), 'Corrección de guía solicitada');
    await userEvent.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    expect(toastErrorMock).toHaveBeenCalledWith('El pedido ya no está pendiente');
  });

  it('dado error sin detalle cuando guarda entonces muestra el mensaje generico', async () => {
    mockPatch.mockRejectedValue(new Error('network error'));
    render(<EditarPedidoModal pedido={PEDIDO} onClose={vi.fn()} onSuccess={vi.fn()} />);

    const guiaInput = screen.getByDisplayValue('GR-001');
    await userEvent.clear(guiaInput);
    await userEvent.type(guiaInput, 'GR-004');
    await userEvent.type(screen.getByPlaceholderText('Describe el motivo de la modificación...'), 'Corrección de guía solicitada');
    await userEvent.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    expect(toastErrorMock).toHaveBeenCalledWith('Error al modificar el pedido');
  });

  it('dado click en cancelar cuando se activa entonces llama onClose', async () => {
    const onClose = vi.fn();
    render(<EditarPedidoModal pedido={PEDIDO} onClose={onClose} onSuccess={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /Cancelar/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
