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

  it('muestra fila del pedido pendiente con botones Editar y Anular', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);

    expect(screen.getByTitle('Editar pedido')).toBeInTheDocument();
    expect(screen.getByTitle('Anular pedido')).toBeInTheDocument();
  });

  it('muestra fila anulada con estilo tachado y botón de historial', async () => {
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

  it('no muestra botones Editar/Anular para pedidos ya anulados', async () => {
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

  it('abre modal de anulación al hacer clic en botón Anular', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);

    await user.click(screen.getByTitle('Anular pedido'));

    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());
  });

  it('muestra contador de caracteres en modal de anulación', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Anular pedido'));
    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());

    expect(screen.getByText(/\/10 caracteres mínimos/)).toBeInTheDocument();
  });

  it('deshabilita botón confirmar con motivo menor a 10 caracteres', async () => {
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

  it('habilita botón confirmar con motivo de 10 o más caracteres', async () => {
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

  it('llama a POST /pedidos-venta/:id/anular/ al confirmar anulación', async () => {
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

  it('muestra toast de error cuando la API responde con error en anulación', async () => {
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

  it('abre modal de edición al hacer clic en botón Editar', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);

    await user.click(screen.getByTitle('Editar pedido'));

    await waitFor(() => expect(screen.getByText(/Editar Pedido #10/i)).toBeInTheDocument());
  });

  it('pre-carga guía de remisión actual en modal de edición', async () => {
    mockApis([PEDIDO_PENDIENTE]);
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await user.click(screen.getByTitle('Editar pedido'));
    await waitFor(() => expect(screen.getByText(/Editar Pedido #10/i)).toBeInTheDocument());

    const input = screen.getByDisplayValue('GR-001');
    expect(input).toBeInTheDocument();
  });

  it('deshabilita Guardar cambios con motivo menor a 10 chars en edición', async () => {
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

  it('llama a PATCH /pedidos-venta/:id/modificar/ al guardar edición', async () => {
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

  it('abre modal de historial con datos de anulación al clic en Clock', async () => {
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
