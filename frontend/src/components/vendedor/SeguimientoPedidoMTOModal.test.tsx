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

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (...args: any[]) => toastSuccessMock(...args),
    error: (...args: any[]) => toastErrorMock(...args),
  },
}));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
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
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado un pedido nulo cuando renderiza entonces no muestra nada', () => {
    const { container } = render(<SeguimientoPedidoMTOModal pedido={null} isOpen={true} onClose={vi.fn()} />);
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it('dado un pedido sin cliente numero ni guia cuando renderiza entonces usa los valores por defecto', () => {
    render(<SeguimientoPedidoMTOModal
      pedido={{ ...mockPedido, numero_pedido: undefined, cliente_nombre: undefined, guia_remision: undefined }}
      isOpen={true} onClose={vi.fn()}
    />);
    expect(screen.getByText(/Pedido #42/)).toBeInTheDocument();
    expect(screen.getByText('N/D')).toBeInTheDocument();
    expect(screen.getByText('Sin asignar')).toBeInTheDocument();
  });

  it('dado un pedido sin detalles cuando renderiza entonces muestra el mensaje vacio', () => {
    render(<SeguimientoPedidoMTOModal pedido={{ ...mockPedido, detalles: [] }} isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByText('No hay ítems registrados en este pedido.')).toBeInTheDocument();
  });

  it('dado un renglon fabricado cuando renderiza entonces muestra la insignia Fabricado y no ofrece Crear OP', () => {
    render(<SeguimientoPedidoMTOModal
      pedido={{ ...mockPedido, detalles: [{ ...mockPedido.detalles[0], estado_fabricacion: 'fabricado' }] }}
      isOpen={true} onClose={vi.fn()}
    />);
    expect(screen.getAllByText('Fabricado').length).toBeGreaterThan(0);
    expect(screen.getByText('Completado')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Crear OP/i })).not.toBeInTheDocument();
  });

  it('dado un pedido anulado cuando renderiza un renglon pendiente entonces indica pedido anulado', () => {
    render(<SeguimientoPedidoMTOModal
      pedido={{ ...mockPedido, anulado: true, detalles: [mockPedido.detalles[1]] }}
      isOpen={true} onClose={vi.fn()}
    />);
    expect(screen.getByText('Pedido anulado')).toBeInTheDocument();
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
    expect(toastSuccessMock).toHaveBeenCalledWith('Orden de producción MTO OP-MTO-0088 generada exitosamente.');
  });

  it('dado cambio de prioridad cuando presiona Crear OP entonces envia la prioridad elegida', async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: { id: 88, codigo: 'OP-MTO-0088' } });
    render(<SeguimientoPedidoMTOModal pedido={mockPedido} isOpen={true} onClose={vi.fn()} />);

    await userEvent.click(screen.getAllByRole('button', { name: 'Baja' })[0]);
    await userEvent.click(screen.getAllByRole('button', { name: /Crear OP/i })[0]);

    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/pedidos-venta/42/generar-orden-mto/',
      expect.objectContaining({ prioridad: 'baja' })));
  });

  it('dado respuesta sin codigo cuando genera la OP entonces usa cadena vacia en el mensaje', async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: {} });
    render(<SeguimientoPedidoMTOModal pedido={mockPedido} isOpen={true} onClose={vi.fn()} />);

    await userEvent.click(screen.getAllByRole('button', { name: /Crear OP/i })[0]);

    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Orden de producción MTO  generada exitosamente.'));
  });

  it('dado el backend rechaza generar la OP cuando falla entonces muestra el mensaje de error', async () => {
    (apiClient.post as any).mockRejectedValueOnce({ response: { data: { error: 'Stock insuficiente para producir.' } } });
    render(<SeguimientoPedidoMTOModal pedido={mockPedido} isOpen={true} onClose={vi.fn()} />);

    await userEvent.click(screen.getAllByRole('button', { name: /Crear OP/i })[0]);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
  });

  it('dado callback onOrderUpdated cuando genera la OP con exito entonces lo invoca', async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: { id: 88, codigo: 'OP-MTO-0088' } });
    const onOrderUpdated = vi.fn();
    render(<SeguimientoPedidoMTOModal pedido={mockPedido} isOpen={true} onClose={vi.fn()} onOrderUpdated={onOrderUpdated} />);

    await userEvent.click(screen.getAllByRole('button', { name: /Crear OP/i })[0]);

    await waitFor(() => expect(onOrderUpdated).toHaveBeenCalled());
  });
});
