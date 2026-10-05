import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VendedorDashboard } from './VendedorDashboard';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

vi.mock('../../lib/axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: [] })),
    patch: vi.fn(() => Promise.resolve({ data: [] })),
    delete: vi.fn(() => Promise.resolve({ data: [] })),
    put: vi.fn(() => Promise.resolve({ data: [] })),
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: [] })),
      post: vi.fn(() => Promise.resolve({ data: [] })),
      patch: vi.fn(() => Promise.resolve({ data: [] })),
      delete: vi.fn(() => Promise.resolve({ data: [] })),
      put: vi.fn(() => Promise.resolve({ data: [] }))
    }))
  },
}));
import apiClient from '../../lib/axios';

vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: { user: { id: 1 } } }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));
import { toast } from 'sonner';

global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

const PEDIDO_PENDIENTE = {
  id: 10,
  cliente: 1,
  cliente_nombre: 'Cliente Prueba',
  guia_remision: 'GR-001',
  fecha_pedido: '2026-04-01T10:00:00Z',
  estado: 'pendiente',
  esta_pagado: false,
  sede: 1,
  total: 200,
  anulado: false,
  motivo_anulacion: null as string | null,
  anulado_por: null as number | null,
  anulado_por_nombre: null as string | null,
  fecha_anulacion: null as string | null,
  valor_retencion: 0,
};

const PEDIDO_ANULADO = {
  ...PEDIDO_PENDIENTE,
  id: 11,
  guia_remision: 'GR-002',
  anulado: true,
  motivo_anulacion: 'Cliente canceló por error',
  anulado_por: 1,
  anulado_por_nombre: 'Vendedor Test',
  fecha_anulacion: '2026-04-10T15:30:00Z',
};

function mockApis(pedidos = [PEDIDO_PENDIENTE]) {
  (apiClient.get as any).mockImplementation((url: string) => {
    if (url === '/clientes/') return Promise.resolve({ data: [{ id: 1, nombre_razon_social: 'Cliente Prueba', limite_credito: 1000, saldo_pendiente: 0, plazo_credito_dias: 30, ruc_cedula: '1700000001', direccion_envio: 'Calle 1', nivel_precio: 'normal', tiene_beneficio: false, cartera_vencida: 0 }] });
    if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: pedidos });
    if (url.includes('/productos/')) return Promise.resolve({ data: [] });
    return Promise.resolve({ data: [] });
  });
}

const renderComponent = () =>
  render(
    <BrowserRouter>
      <VendedorDashboard />
    </BrowserRouter>
  );

async function navigateToPedidos(user: ReturnType<typeof userEvent.setup>) {
  await waitFor(() => expect(screen.getByText('Directorio de Clientes')).toBeInTheDocument());
  const tabs = screen.getAllByRole('tab');
  const pedidosTab = tabs.find((t) => t.textContent?.includes('Últimas Ventas'));
  if (pedidosTab) await user.click(pedidosTab);
  await waitFor(() => expect(screen.getByText('GR-001')).toBeInTheDocument());
}

describe('VendedorDashboard — Anulación y Modificación de Pedidos', () => {
  beforeEach(() => vi.clearAllMocks());

  // ── Render de tabla ─────────────────────────────────────────────────────────

  it('dado un pedido pendiente cuando lista los pedidos entonces muestra sus botones Editar y Anular', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);

    expect(screen.getByTitle('Editar pedido')).toBeInTheDocument();
    expect(screen.getByTitle('Anular pedido')).toBeInTheDocument();
  });

  it('dado un pedido anulado cuando lista los pedidos entonces lo muestra tachado y con botón de historial', async () => {
    mockApis([PEDIDO_ANULADO]);
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => expect(screen.getByText('Directorio de Clientes')).toBeInTheDocument());
    const tabs = screen.getAllByRole('tab');
    const pedidosTab = tabs.find((t) => t.textContent?.includes('Últimas Ventas'));
    if (pedidosTab) await user.click(pedidosTab);
    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());

    expect(screen.getByTitle('Ver motivo de anulación')).toBeInTheDocument();
  });

  it('dado un pedido anulado cuando lista los pedidos entonces no muestra Editar ni Anular', async () => {
    mockApis([PEDIDO_ANULADO]);
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => expect(screen.getByText('Directorio de Clientes')).toBeInTheDocument());
    const tabs = screen.getAllByRole('tab');
    const pedidosTab = tabs.find((t) => t.textContent?.includes('Últimas Ventas'));
    if (pedidosTab) await user.click(pedidosTab);
    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());

    expect(screen.queryByTitle('Editar pedido')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Anular pedido')).not.toBeInTheDocument();
    expect(screen.getByTitle('Ver motivo de anulación')).toBeInTheDocument();
  });

  // ── AnularPedidoModal ───────────────────────────────────────────────────────

  it('dado un pedido pendiente cuando hace clic en Anular entonces abre el modal de anulación', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);

    await user.click(screen.getByTitle('Anular pedido'));

    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());
  });

  it('dado el modal de anulación cuando escribe el motivo entonces muestra el contador de caracteres', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Anular pedido'));
    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());

    expect(screen.getByText(/\/10 caracteres mínimos/)).toBeInTheDocument();
  });

  it('dado un motivo menor a 10 caracteres cuando revisa el modal de anulación entonces el botón confirmar está deshabilitado', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Anular pedido'));
    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la anulación/);
    await user.type(textarea, 'corto');

    const btn = screen.getByRole('button', { name: /Confirmar anulación/i });
    expect(btn).toBeDisabled();
  });

  it('dado un motivo de 10 o más caracteres cuando revisa el modal de anulación entonces el botón confirmar está habilitado', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Anular pedido'));
    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la anulación/);
    await user.type(textarea, 'motivo valido completo');

    const btn = screen.getByRole('button', { name: /Confirmar anulación/i });
    expect(btn).not.toBeDisabled();
  });

  it('dado un motivo válido cuando confirma la anulación entonces llama a POST /pedidos-venta/:id/anular/', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    (apiClient.post as any).mockResolvedValue({ data: { message: 'Pedido anulado correctamente.' } });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Anular pedido'));
    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la anulación/);
    await user.type(textarea, 'cliente solicita anulacion urgente');
    await user.click(screen.getByRole('button', { name: /Confirmar anulación/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/pedidos-venta/10/anular/',
        { motivo_anulacion: 'cliente solicita anulacion urgente' }
      );
    });
  });

  it('dado un error de la API cuando confirma la anulación entonces muestra toast de error', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    (apiClient.post as any).mockRejectedValue({
      response: { data: { error: 'No tienes permisos para anular pedidos.' } },
    });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Anular pedido'));
    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la anulación/);
    await user.type(textarea, 'motivo de prueba valido para el test');
    await user.click(screen.getByRole('button', { name: /Confirmar anulación/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No tienes permisos para anular pedidos.');
    });
  });

  // ── EditarPedidoModal ───────────────────────────────────────────────────────

  it('dado un pedido pendiente cuando hace clic en Editar entonces abre el modal de edición', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);

    await user.click(screen.getByTitle('Editar pedido'));

    await waitFor(() => expect(screen.getByText(/Editar Pedido #10/i)).toBeInTheDocument());
  });

  it('dado un pedido con guía de remisión cuando abre el modal de edición entonces precarga la guía', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Editar pedido'));
    await waitFor(() => expect(screen.getByText(/Editar Pedido #10/i)).toBeInTheDocument());

    const input = screen.getByDisplayValue('GR-001');
    expect(input).toBeInTheDocument();
  });

  it('dado un motivo menor a 10 caracteres cuando revisa el modal de edición entonces Guardar cambios está deshabilitado', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Editar pedido'));
    await waitFor(() => expect(screen.getByText(/Editar Pedido #10/i)).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la modificación/);
    await user.type(textarea, 'corto');

    expect(screen.getByRole('button', { name: /Guardar cambios/i })).toBeDisabled();
  });

  it('dado cambios y motivo válidos cuando guarda la edición entonces llama a PATCH /pedidos-venta/:id/modificar/', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    (apiClient.patch as any).mockResolvedValue({ data: { message: 'Pedido modificado correctamente.', cambios: ['guia_remision'] } });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Editar pedido'));
    await waitFor(() => expect(screen.getByText(/Editar Pedido #10/i)).toBeInTheDocument());

    const guiaInput = screen.getByDisplayValue('GR-001');
    await user.clear(guiaInput);
    await user.type(guiaInput, 'GR-001-MOD');

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la modificación/);
    await user.type(textarea, 'corrección de guía de remisión solicitada');

    await user.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        '/pedidos-venta/10/modificar/',
        expect.objectContaining({
          guia_remision: 'GR-001-MOD',
          motivo: 'corrección de guía de remisión solicitada',
        })
      );
    });
  });

  // ── HistorialPedidoModal ────────────────────────────────────────────────────

  it('dado un pedido anulado cuando hace clic en el reloj entonces abre el historial con los datos de anulación', async () => {
    mockApis([PEDIDO_ANULADO]);
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => expect(screen.getByText('Directorio de Clientes')).toBeInTheDocument());
    const tabs = screen.getAllByRole('tab');
    const pedidosTab = tabs.find((t) => t.textContent?.includes('Últimas Ventas'));
    if (pedidosTab) await user.click(pedidosTab);
    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());

    await user.click(screen.getByTitle('Ver motivo de anulación'));

    await waitFor(() => {
      expect(screen.getByText(/Detalle de anulación/i)).toBeInTheDocument();
      expect(screen.getByText('Cliente canceló por error')).toBeInTheDocument();
    });
  });
});
