import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
global.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/fake-blob-url');
global.URL.revokeObjectURL = vi.fn();

const CLIENTE_1 = {
  id: 1,
  nombre_razon_social: 'Cliente Prueba',
  limite_credito: 1000,
  saldo_pendiente: 300,
  plazo_credito_dias: 30,
  ruc_cedula: '1700000001',
  direccion_envio: 'Calle 1',
  nivel_precio: 'normal',
  tiene_beneficio: false,
  cartera_vencida: 0,
  is_active: true,
};

const PRODUCTO_1 = { id: 1, descripcion: 'Tela Algodon Premium', precio_base: 10, tipo: 'tela' };

const PEDIDO_1 = {
  id: 20,
  cliente: 1,
  cliente_nombre: 'Cliente Prueba',
  guia_remision: 'GR-020',
  fecha_pedido: '2026-06-01T10:00:00Z',
  estado: 'pendiente',
  esta_pagado: false,
  sede: 1,
  total: 200,
  anulado: false,
  valor_retencion: 0,
};

function mockApis({ clientes = [CLIENTE_1], pedidos = [PEDIDO_1], productos = [PRODUCTO_1] } = {}) {
  (apiClient.get as any).mockImplementation((url: string) => {
    if (url === '/clientes/') return Promise.resolve({ data: clientes });
    if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: pedidos });
    if (url.includes('/productos/')) return Promise.resolve({ data: productos });
    return Promise.resolve({ data: [] });
  });
}

const renderComponent = () =>
  render(
    <BrowserRouter>
      <VendedorDashboard />
    </BrowserRouter>
  );

async function esperarDirectorio() {
  await waitFor(() => expect(screen.getByText('Directorio de Clientes')).toBeInTheDocument());
}

async function abrirVentaNueva(user: ReturnType<typeof userEvent.setup>) {
  await esperarDirectorio();
  await user.click(screen.getByRole('button', { name: /Venta Nueva/i }));
  await waitFor(() => expect(screen.getByText('Registrar Nueva Venta')).toBeInTheDocument());
}

async function agregarItem(user: ReturnType<typeof userEvent.setup>, dialog: HTMLElement, peso = '10', precio = '10') {
  const dialogComboboxes = Array.from(dialog.querySelectorAll('[role="combobox"]'));
  await user.click(dialogComboboxes[0] as HTMLElement);
  const opcionCliente = await screen.findByRole('option', { name: /Cliente Prueba/ });
  await user.click(opcionCliente);

  const dialogComboboxes2 = Array.from(dialog.querySelectorAll('[role="combobox"]'));
  await user.click(dialogComboboxes2[1] as HTMLElement);
  const opcionProducto = await screen.findByText('Tela Algodon Premium');
  await user.click(opcionProducto);

  const allDialogInputs = dialog.querySelectorAll('input[type="text"]');
  const inputPeso = allDialogInputs[0] as HTMLInputElement;
  const inputPrecio = allDialogInputs[1] as HTMLInputElement;

  await user.clear(inputPeso);
  await user.type(inputPeso, peso);
  await user.clear(inputPrecio);
  await user.type(inputPrecio, precio);

  await user.click(screen.getByRole('button', { name: /Añadir/i }));
}

async function abrirExpedienteCliente(user: ReturnType<typeof userEvent.setup>, clienteDetallado: any) {
  await esperarDirectorio();
  (apiClient.get as any).mockImplementation((url: string) => {
    if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
    if (url === '/clientes/1/') return Promise.resolve({ data: clienteDetallado });
    if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
    if (url.includes('/productos/')) return Promise.resolve({ data: [] });
    return Promise.resolve({ data: [] });
  });
  await user.click(screen.getByText('Cliente Prueba'));
  await waitFor(() => expect(screen.getByText(/Expediente de Cliente/)).toBeInTheDocument());
}

describe('VendedorDashboard — Ventas, Cobranza y Reportes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  // ── Creación de pedido ───────────────────────────────────────────────────────

  it('muestra error si intenta finalizar la venta sin cliente ni items', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);

    await user.click(screen.getByRole('button', { name: /Finalizar y Guardar/i }));

    expect(toast.error).toHaveBeenCalledWith('Por favor selecciona un cliente y añade al menos un producto');
    expect(apiClient.post).not.toHaveBeenCalledWith('/pedidos-venta/', expect.anything());
  });

  it('crea un pedido correctamente y llama a POST /pedidos-venta/ con el payload esperado', async () => {
    (apiClient.post as any).mockResolvedValue({ data: { id: 123 } });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);

    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;
    await agregarItem(user, dialog);

    await waitFor(() => {
      const totalRow = dialog.querySelector('tr.bg-primary\\/5');
      expect(totalRow!.textContent).toContain('115.000');
    });

    await user.click(screen.getByRole('button', { name: /Finalizar y Guardar/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/pedidos-venta/',
        expect.objectContaining({
          cliente: 1,
          valor_retencion: 0,
          detalles: expect.arrayContaining([
            expect.objectContaining({ producto: '1', peso: 10, precio_unitario: 10, incluye_iva: true }),
          ]),
        })
      );
    });
    expect(toast.success).toHaveBeenCalledWith('Pedido creado correctamente');
  });

  it('muestra el mensaje de error del backend cuando falla la creación del pedido', async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: { cliente: 'El cliente excede su límite de crédito.' } },
    });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);

    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;
    await agregarItem(user, dialog);
    await user.click(screen.getByRole('button', { name: /Finalizar y Guardar/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('El cliente excede su límite de crédito.');
    });
  });

  // ── Registro de abonos / pagos ────────────────────────────────────────────────

  it('registra un pago (abono) correctamente y refresca el detalle del cliente', async () => {
    (apiClient.post as any).mockResolvedValue({ data: { id: 55 } });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, { ...CLIENTE_1, pedidos: [], pagos: [] });

    await user.click(screen.getByRole('button', { name: /Abonos/i }));
    await waitFor(() => expect(screen.getByText('Registrar Abono / Pago')).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText('0.00'), '150');
    await user.click(screen.getByRole('button', { name: /Confirmar Abono/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/pagos-cliente/', expect.objectContaining({
        cliente: 1,
        monto: 150,
        metodo_pago: 'transferencia',
        es_anticipo: false,
      }));
    });
    expect(toast.success).toHaveBeenCalledWith('Pago registrado correctamente');
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/clientes/1/'));
  });

  it('registra un anticipo y muestra el toast correspondiente cuando se activa "Es Anticipo"', async () => {
    (apiClient.post as any).mockResolvedValue({ data: { id: 56 } });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, { ...CLIENTE_1, pedidos: [], pagos: [] });

    await user.click(screen.getByRole('button', { name: /Abonos/i }));
    await waitFor(() => expect(screen.getByText('Registrar Abono / Pago')).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText('0.00'), '500');
    await user.click(screen.getByText('Es Anticipo').closest('div')!.parentElement!.querySelector('button[role="switch"]') as HTMLElement);
    await user.click(screen.getByRole('button', { name: /Confirmar Anticipo/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/pagos-cliente/', expect.objectContaining({ es_anticipo: true }));
    });
    expect(toast.success).toHaveBeenCalledWith('Anticipo registrado correctamente');
  });

  it('muestra error si el monto del abono está vacío o es inválido', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, { ...CLIENTE_1, pedidos: [], pagos: [] });

    await user.click(screen.getByRole('button', { name: /Abonos/i }));
    await waitFor(() => expect(screen.getByText('Registrar Abono / Pago')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Confirmar Abono/i }));

    expect(toast.error).toHaveBeenCalledWith('Por favor ingresa un monto válido');
    expect(apiClient.post).not.toHaveBeenCalledWith('/pagos-cliente/', expect.anything());
  });

  it('muestra el mensaje de error del backend cuando el pago excede el saldo permitido', async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: { monto: ['El monto no puede exceder la deuda salvo que sea un anticipo.'] } },
    });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, { ...CLIENTE_1, pedidos: [], pagos: [] });

    await user.click(screen.getByRole('button', { name: /Abonos/i }));
    await waitFor(() => expect(screen.getByText('Registrar Abono / Pago')).toBeInTheDocument());
    await user.type(screen.getByPlaceholderText('0.00'), '99999');
    await user.click(screen.getByRole('button', { name: /Confirmar Abono/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('El monto no puede exceder la deuda salvo que sea un anticipo.');
    });
  });

  // ── Reversión de pagos ──────────────────────────────────────────────────────

  it('abre el modal de reversión y exige una justificación mínima de 5 caracteres', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, {
      ...CLIENTE_1,
      pedidos: [],
      pagos: [{ id: 8, fecha: '2026-06-02T10:00:00Z', metodo_pago: 'efectivo', monto: 50 }],
    });

    await user.click(screen.getByRole('tab', { name: /Abonos \/ Recibos/i }));
    await waitFor(() => expect(screen.getByTitle('Revertir pago')).toBeInTheDocument());
    await user.click(screen.getByTitle('Revertir pago'));

    await waitFor(() => expect(screen.getByText('Revertir Pago')).toBeInTheDocument());
    const confirmBtn = screen.getByRole('button', { name: /Confirmar Reversión/i });
    expect(confirmBtn).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Explica por qué se revierte/i);
    await user.type(textarea, 'err');
    expect(confirmBtn).toBeDisabled();

    await user.type(textarea, 'or de digitación');
    expect(confirmBtn).not.toBeDisabled();
  });

  it('llama a POST /pagos-cliente/:id/revertir/ al confirmar la reversión de un pago', async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, {
      ...CLIENTE_1,
      pedidos: [],
      pagos: [{ id: 8, fecha: '2026-06-02T10:00:00Z', metodo_pago: 'efectivo', monto: 50 }],
    });

    await user.click(screen.getByRole('tab', { name: /Abonos \/ Recibos/i }));
    await waitFor(() => expect(screen.getByTitle('Revertir pago')).toBeInTheDocument());
    await user.click(screen.getByTitle('Revertir pago'));
    await waitFor(() => expect(screen.getByText('Revertir Pago')).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Explica por qué se revierte/i);
    await user.type(textarea, 'pago duplicado por error del cajero');
    await user.click(screen.getByRole('button', { name: /Confirmar Reversión/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/pagos-cliente/8/revertir/', {
        justificacion: 'pago duplicado por error del cajero',
      });
    });
    expect(toast.success).toHaveBeenCalledWith('Pago revertido correctamente. Deuda del cliente restaurada.');
  });

  it('muestra error del backend cuando falla la reversión de un pago', async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: { error: 'El pago ya fue revertido anteriormente.' } },
    });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, {
      ...CLIENTE_1,
      pedidos: [],
      pagos: [{ id: 9, fecha: '2026-06-02T10:00:00Z', metodo_pago: 'efectivo', monto: 50 }],
    });

    await user.click(screen.getByRole('tab', { name: /Abonos \/ Recibos/i }));
    await waitFor(() => expect(screen.getByTitle('Revertir pago')).toBeInTheDocument());
    await user.click(screen.getByTitle('Revertir pago'));
    await waitFor(() => expect(screen.getByText('Revertir Pago')).toBeInTheDocument());
    await user.type(screen.getByPlaceholderText(/Explica por qué se revierte/i), 'justificacion valida');
    await user.click(screen.getByRole('button', { name: /Confirmar Reversión/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('El pago ya fue revertido anteriormente.');
    });
  });

  // ── Impresión de PDF ─────────────────────────────────────────────────────────

  it('descarga el PDF de un pedido al hacer clic en el botón de imprimir', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/') && !url.includes('download_pdf')) return Promise.resolve({ data: [PEDIDO_1] });
      if (url.includes('download_pdf')) return Promise.resolve({ data: new Blob(['pdf']) });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    const tabs = screen.getAllByRole('tab');
    const pedidosTab = tabs.find((t) => t.textContent?.includes('Últimas Ventas'));
    await user.click(pedidosTab!);
    await waitFor(() => expect(screen.getByText('GR-020')).toBeInTheDocument());

    await user.click(screen.getByTitle('Imprimir PDF'));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/pedidos-venta/20/download_pdf/', { responseType: 'blob' });
    });
  });

  it('muestra un toast de error cuando falla la descarga del PDF', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/') && !url.includes('download_pdf')) return Promise.resolve({ data: [PEDIDO_1] });
      if (url.includes('download_pdf')) return Promise.reject(new Error('network error'));
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    const tabs = screen.getAllByRole('tab');
    const pedidosTab = tabs.find((t) => t.textContent?.includes('Últimas Ventas'));
    await user.click(pedidosTab!);
    await waitFor(() => expect(screen.getByText('GR-020')).toBeInTheDocument());

    await user.click(screen.getByTitle('Imprimir PDF'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al descargar el PDF de la nota de venta.');
    });
  });

  // ── Reportes Excel ───────────────────────────────────────────────────────────

  async function irAReportes(user: ReturnType<typeof userEvent.setup>) {
    await esperarDirectorio();
    const tabs = screen.getAllByRole('tab');
    const reportesTab = tabs.find((t) => t.textContent?.includes('Reportes Excel'));
    await user.click(reportesTab!);
    await waitFor(() => expect(screen.getByText('Reportes Comerciales Avanzados')).toBeInTheDocument());
  }

  it('exporta el reporte de ventas y llama al endpoint de reporting esperado', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/ventas')) return Promise.resolve({ data: new Blob(['xlsx']) });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[0]);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/reporting/vendedores/1/ventas'),
        { responseType: 'blob' }
      );
    });
    expect(toast.success).toHaveBeenCalledWith('Excel descargado correctamente.');
  });

  it('muestra error 404 al exportar ventas sin datos para el rango seleccionado', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/ventas')) return Promise.reject({ response: { status: 404 } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[0]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No se encontraron datos para estos parámetros.');
    });
  });

  it('muestra error de servidor (500) al exportar el reporte de ventas', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/ventas')) return Promise.reject({ response: { status: 500 } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[0]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error del servidor al generar el reporte. Revisa los logs.');
    });
  });

  it('exporta el reporte de top clientes y muestra error 404 cuando no hay datos', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/top-clientes')) return Promise.reject({ response: { status: 404 } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[1]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No se encontraron clientes para estos parámetros.');
    });
  });

  it('exporta el reporte de cartera vencida (deudores) correctamente', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/deudores')) return Promise.resolve({ data: new Blob(['xlsx']) });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[2]);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/reporting/vendedores/1/deudores'),
        { responseType: 'blob' }
      );
    });
  });

  it('muestra error genérico al fallar la exportación de deudores sin ser 404', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/deudores')) return Promise.reject({ response: { status: 500 } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[2]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al exportar el reporte.');
    });
  });

  // ── Items del pedido (añadir / quitar) ────────────────────────────────────────

  it('muestra error si intenta añadir un item sin producto, peso o precio', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);

    await user.click(screen.getByRole('button', { name: /Añadir/i }));

    expect(toast.error).toHaveBeenCalledWith('Por favor completa todos los campos del item');
  });

  it('quita un item añadido y recalcula el total del pedido', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;
    await agregarItem(user, dialog);

    await waitFor(() => {
      const totalRow = dialog.querySelector('tr.bg-primary\\/5');
      expect(totalRow!.textContent).toContain('115.000');
    });

    const eliminarBtn = dialog.querySelector('table tbody tr td button') as HTMLElement;
    await user.click(eliminarBtn);

    await waitFor(() => {
      expect(dialog.querySelector('tr.bg-primary\\/5')).not.toBeInTheDocument();
    });
  });
});
