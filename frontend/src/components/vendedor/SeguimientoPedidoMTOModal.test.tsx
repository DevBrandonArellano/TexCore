import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SeguimientoPedidoMTOModal } from './SeguimientoPedidoMTOModal';
import apiClient from '../../lib/axios';

vi.mock('../../lib/axios', () => ({
  default: {
    post: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockPedido: any = {
  id: 42,
  numero_pedido: 'PV-00042',
  cliente_nombre: 'Confecciones del Norte',
  fecha_pedido: '2026-09-17T10:00:00Z',
  estado: 'aprobado',
  anulado: false,
  detalles: [
    {
      id: 101,
      producto: 5,
      producto_nombre: 'Tela Jersey Peinado 30/1',
      peso: 200,
      precio_unitario: 6.5,
      cantidad_fabricada: 120,
      estado_fabricacion: 'en_proceso',
    },
    {
      id: 102,
      producto: 8,
      producto_nombre: 'Rib 1x1 Algodón',
      peso: 50,
      precio_unitario: 7.0,
      cantidad_fabricada: 0,
      estado_fabricacion: 'pendiente',
    },
  ],
};

describe('SeguimientoPedidoMTOModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('dado un pedido cuando abre el modal entonces muestra el encabezado y renglones de detalle', () => {
    render(
      <SeguimientoPedidoMTOModal
        pedido={mockPedido}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText(/Seguimiento de Fabricación MTO — Pedido #PV-00042/i)).toBeInTheDocument();
    expect(screen.getByText('Confecciones del Norte')).toBeInTheDocument();
    expect(screen.getByText('Tela Jersey Peinado 30/1')).toBeInTheDocument();
    expect(screen.getByText('120.00 kg')).toBeInTheDocument();
    expect(screen.getByText('Rib 1x1 Algodón')).toBeInTheDocument();
  });

  it('dado un renglon pendiente cuando presiona Crear OP entonces invoca generar-orden-mto', async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: { id: 88, codigo: 'OP-MTO-0088' },
    });

    render(
      <SeguimientoPedidoMTOModal
        pedido={mockPedido}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    const botonesCrear = screen.getAllByRole('button', { name: /Crear OP/i });
    await userEvent.click(botonesCrear[0]);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/pedidos-venta/42/generar-orden-mto/', {
        detalle_pedido_id: 101,
        prioridad: 'alta',
        peso_solicitado: 200,
      });
    });
  });
});
