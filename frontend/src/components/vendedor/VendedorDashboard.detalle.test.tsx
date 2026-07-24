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

const PEDIDO_PENDIENTE = {
  id: 10,
  cliente: 1,
  cliente_nombre: 'Cliente Prueba',
  guia_remision: 'GR-001',
  fecha_pedido: '2026-04-01T10:00:00Z',
  fecha_despacho: '',
  estado: 'pendiente',
  esta_pagado: false,
  sede: 1,
  total: 200,
  anulado: false,
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

function mockApis({ clientes = [CLIENTE_1], pedidos = [PEDIDO_PENDIENTE], productos = [PRODUCTO_1] } = {}) {
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

async function navigateToPedidos(user: ReturnType<typeof userEvent.setup>) {
  await esperarDirectorio();
  const tabs = screen.getAllByRole('tab');
  const pedidosTab = tabs.find((t) => t.textContent?.includes('Últimas Ventas'));
  if (pedidosTab) await user.click(pedidosTab);
}

async function abrirVentaNueva(user: ReturnType<typeof userEvent.setup>) {
  await esperarDirectorio();
  await user.click(screen.getByRole('button', { name: /Venta Nueva/i }));
  await waitFor(() => expect(screen.getByText('Registrar Nueva Venta')).toBeInTheDocument());
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

describe('VendedorDashboard — Carga inicial', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('dado que la carga inicial de datos falla con un error genérico cuando el dashboard se monta entonces muestra un toast de error', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.reject({ response: { status: 500 } });
      return Promise.resolve({ data: [] });
    });
    renderComponent();

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al cargar la información del vendedor');
    });
  });
});

describe('VendedorDashboard — Edición de pedidos: variaciones de campos', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  async function abrirEdicion(user: ReturnType<typeof userEvent.setup>) {
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('GR-001')).toBeInTheDocument());
    await user.click(screen.getByTitle('Editar pedido'));
    await waitFor(() => expect(screen.getByText(/Editar Pedido #10/i)).toBeInTheDocument());
  }

  it('dado un pedido pendiente cuando se cambia la fecha de despacho y se guarda entonces el PATCH incluye fecha_despacho', async () => {
    (apiClient.patch as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup();
    renderComponent();
    await abrirEdicion(user);

    const fechaInput = document.querySelector('input[type="date"]') as HTMLInputElement;
    await user.clear(fechaInput);
    await user.type(fechaInput, '2026-05-15');

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la modificación/);
    await user.type(textarea, 'se agenda fecha de despacho acordada');
    await user.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        '/pedidos-venta/10/modificar/',
        expect.objectContaining({ fecha_despacho: '2026-05-15' })
      );
    });
  });

  it('dado un pedido pendiente cuando se cambia el valor de retención y se guarda entonces el PATCH incluye valor_retencion parseado', async () => {
    (apiClient.patch as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup();
    renderComponent();
    await abrirEdicion(user);

    const retencionInput = screen.getByDisplayValue('0') as HTMLInputElement;
    await user.clear(retencionInput);
    await user.type(retencionInput, '25');

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la modificación/);
    await user.type(textarea, 'cliente entregó retención tardía');
    await user.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        '/pedidos-venta/10/modificar/',
        expect.objectContaining({ valor_retencion: 25 })
      );
    });
  });

  it('dado un pedido pendiente cuando se marca como pagado y se guarda entonces el PATCH incluye esta_pagado true', async () => {
    (apiClient.patch as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup();
    renderComponent();
    await abrirEdicion(user);

    const checkbox = document.getElementById('esta_pagado') as HTMLInputElement;
    await user.click(checkbox);

    const textarea = screen.getByPlaceholderText(/Describe el motivo de la modificación/);
    await user.type(textarea, 'cliente pagó en efectivo en oficina');
    await user.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        '/pedidos-venta/10/modificar/',
        expect.objectContaining({ esta_pagado: true })
      );
    });
  });

  it('dado que la API rechaza la edición cuando se guarda entonces muestra el toast de error del backend', async () => {
    (apiClient.patch as any).mockRejectedValue({
      response: { data: { error: 'No puedes modificar un pedido facturado.' } },
    });
    const user = userEvent.setup();
    renderComponent();
    await abrirEdicion(user);

    const guiaInput = screen.getByDisplayValue('GR-001');
    await user.clear(guiaInput);
    await user.type(guiaInput, 'GR-999');
    const textarea = screen.getByPlaceholderText(/Describe el motivo de la modificación/);
    await user.type(textarea, 'corrección solicitada por el cliente');
    await user.click(screen.getByRole('button', { name: /Guardar cambios/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No puedes modificar un pedido facturado.');
    });
  });

  it('dado el modal de edición abierto cuando se cierra con Escape sin guardar entonces no se envía ningún PATCH', async () => {
    const user = userEvent.setup();
    renderComponent();
    await abrirEdicion(user);

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByText(/Editar Pedido #10/i)).not.toBeInTheDocument());
    expect(apiClient.patch).not.toHaveBeenCalled();
  });
});

describe('VendedorDashboard — Cierre de modales sin confirmar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  it('dado el modal de anulación abierto cuando se cierra con Escape sin confirmar entonces no se envía ningún POST de anulación', async () => {
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('GR-001')).toBeInTheDocument());
    await user.click(screen.getByTitle('Anular pedido'));
    await waitFor(() => expect(screen.getByText(/Anular Pedido #10/i)).toBeInTheDocument());

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByText(/Anular Pedido #10/i)).not.toBeInTheDocument());
    expect(apiClient.post).not.toHaveBeenCalledWith('/pedidos-venta/10/anular/', expect.anything());
  });

  it('dado el modal de historial de anulación abierto cuando se hace clic en Cerrar entonces el modal se cierra', async () => {
    mockApis({ pedidos: [PEDIDO_ANULADO] });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());
    await user.click(screen.getByTitle('Ver motivo de anulación'));
    await waitFor(() => expect(screen.getByText(/Detalle de anulación/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /^Cerrar$/i }));

    await waitFor(() => expect(screen.queryByText(/Detalle de anulación/i)).not.toBeInTheDocument());
  });

  it('dado el modal de historial de anulación abierto cuando se cierra con Escape entonces también se cierra', async () => {
    mockApis({ pedidos: [PEDIDO_ANULADO] });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());
    await user.click(screen.getByTitle('Ver motivo de anulación'));
    await waitFor(() => expect(screen.getByText(/Detalle de anulación/i)).toBeInTheDocument());

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByText(/Detalle de anulación/i)).not.toBeInTheDocument());
  });

  it('dado el modal de reversión de pago abierto cuando se hace clic en Cancelar entonces se cierra sin llamar a la API', async () => {
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

    await user.click(screen.getByRole('button', { name: /^Cancelar$/i }));

    await waitFor(() => expect(screen.queryByText('Revertir Pago')).not.toBeInTheDocument());
    expect(apiClient.post).not.toHaveBeenCalledWith(expect.stringContaining('/revertir/'), expect.anything());
  });

  it('dado el modal de reversión de pago abierto cuando se cierra con Escape entonces también se cierra sin llamar a la API', async () => {
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

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByText('Revertir Pago')).not.toBeInTheDocument());
    expect(apiClient.post).not.toHaveBeenCalledWith(expect.stringContaining('/revertir/'), expect.anything());
  });
});

describe('VendedorDashboard — Venta Nueva: campos adicionales', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  it('dado el formulario de venta nueva cuando se ingresa una guía de remisión entonces el input refleja el valor escrito', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);

    const guiaInput = screen.getByPlaceholderText('Ej: GR-001') as HTMLInputElement;
    await user.type(guiaInput, 'GR-777');

    expect(guiaInput.value).toBe('GR-777');
  });

  it('dado un item con el switch de IVA desactivado cuando se añade al pedido entonces el subtotal no incluye el 15% de IVA', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;

    const dialogComboboxes = Array.from(dialog.querySelectorAll('[role="combobox"]'));
    await user.click(dialogComboboxes[1] as HTMLElement);
    const opcionProducto = await screen.findByText('Tela Algodon Premium');
    await user.click(opcionProducto);

    const ivaSwitch = screen.getByRole('switch', { name: '' }) || document.getElementById('iva-mode');
    const ivaToggle = document.getElementById('iva-mode') as HTMLElement;
    await user.click(ivaToggle);

    const allDialogInputs = dialog.querySelectorAll('input[type="text"]');
    const inputPeso = allDialogInputs[0] as HTMLInputElement;
    const inputPrecio = allDialogInputs[1] as HTMLInputElement;
    await user.clear(inputPeso);
    await user.type(inputPeso, '10');
    await user.clear(inputPrecio);
    await user.type(inputPrecio, '10');
    await user.click(screen.getByRole('button', { name: /Añadir/i }));

    await waitFor(() => {
      const totalRow = dialog.querySelector('tr.bg-primary\\/5');
      expect(totalRow!.textContent).toContain('100.000');
    });
  });

  it('dado que se ingresa un peso con ceros a la izquierda cuando se escribe "010" entonces el valor se normaliza a "10"', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;

    const allDialogInputs = dialog.querySelectorAll('input[type="text"]');
    const inputPeso = allDialogInputs[0] as HTMLInputElement;
    await user.clear(inputPeso);
    await user.type(inputPeso, '010');

    expect(inputPeso.value).toBe('10');
  });

  it('dado que se ingresa un precio con ceros a la izquierda cuando se escribe "010" entonces el valor se normaliza a "10"', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;

    const allDialogInputs = dialog.querySelectorAll('input[type="text"]');
    const inputPrecio = allDialogInputs[1] as HTMLInputElement;
    await user.clear(inputPrecio);
    await user.type(inputPrecio, '010');

    expect(inputPrecio.value).toBe('10');
  });

  it('dado que se escriben solo ceros en el peso entonces el valor se normaliza a un único "0"', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;

    const allDialogInputs = dialog.querySelectorAll('input[type="text"]');
    const inputPeso = allDialogInputs[0] as HTMLInputElement;
    await user.clear(inputPeso);
    await user.type(inputPeso, '00');

    expect(inputPeso.value).toBe('0');
  });

  it('dado el campo de retención con un valor cuando se borra y pierde el foco entonces se restablece a "0"', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;

    const dialogComboboxes = Array.from(dialog.querySelectorAll('[role="combobox"]'));
    await user.click(dialogComboboxes[1] as HTMLElement);
    const opcionProducto = await screen.findByText('Tela Algodon Premium');
    await user.click(opcionProducto);
    const allDialogInputs = dialog.querySelectorAll('input[type="text"]');
    await user.clear(allDialogInputs[0] as HTMLInputElement);
    await user.type(allDialogInputs[0] as HTMLInputElement, '10');
    await user.clear(allDialogInputs[1] as HTMLInputElement);
    await user.type(allDialogInputs[1] as HTMLInputElement, '10');
    await user.click(screen.getByRole('button', { name: /Añadir/i }));

    const switches = screen.getAllByRole('switch');
    const toggleRetencion = switches[switches.length - 2];
    await user.click(toggleRetencion);

    const inputRetencionWrapper = screen.getByText('Valor de Retención ($)').parentElement as HTMLElement;
    const inputRetencion = inputRetencionWrapper.querySelector('input') as HTMLInputElement;
    await user.clear(inputRetencion);
    await user.tab();

    expect(inputRetencion.value).toBe('0');
  });

  it('dado el switch "El cliente pagó en caja" cuando se activa entonces oculta la advertencia de venta al contado', async () => {
    mockApis({ clientes: [{ ...CLIENTE_1, plazo_credito_dias: 0 }] });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;

    const dialogComboboxes = Array.from(dialog.querySelectorAll('[role="combobox"]'));
    await user.click(dialogComboboxes[0] as HTMLElement);
    const opcionCliente = await screen.findByRole('option', { name: /Cliente Prueba/ });
    await user.click(opcionCliente);

    await waitFor(() => expect(screen.getByText(/Atención de Seguridad/)).toBeInTheDocument());

    const pagoSwitch = screen.getByText('¿El cliente pagó en caja?').closest('div')!.parentElement!.querySelector(
      'button[role="switch"]'
    ) as HTMLElement;
    await user.click(pagoSwitch);

    await waitFor(() => expect(screen.queryByText(/Atención de Seguridad/)).not.toBeInTheDocument());
  });

  it('dado el diálogo de venta nueva abierto cuando se hace clic en Cancelar entonces el diálogo se cierra', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);

    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;
    const cancelarBtn = within(dialog).getByRole('button', { name: /^Cancelar$/i });
    await user.click(cancelarBtn);

    await waitFor(() => expect(screen.queryByText('Registrar Nueva Venta')).not.toBeInTheDocument());
  });

  it('dado un pedido con retención aplicada cuando se elimina un item y la retención supera el nuevo total entonces se muestra error al finalizar', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirVentaNueva(user);
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;

    const dialogComboboxes = Array.from(dialog.querySelectorAll('[role="combobox"]'));
    await user.click(dialogComboboxes[0] as HTMLElement);
    const opcionCliente = await screen.findByRole('option', { name: /Cliente Prueba/ });
    await user.click(opcionCliente);

    const dialogComboboxes2 = Array.from(dialog.querySelectorAll('[role="combobox"]'));
    await user.click(dialogComboboxes2[1] as HTMLElement);
    await user.click((await screen.findAllByRole('option', { name: 'Tela Algodon Premium' })).at(-1)!);
    let inputs = dialog.querySelectorAll('input[type="text"]');
    await user.clear(inputs[0] as HTMLInputElement);
    await user.type(inputs[0] as HTMLInputElement, '10');
    await user.clear(inputs[1] as HTMLInputElement);
    await user.type(inputs[1] as HTMLInputElement, '10');
    await user.click(screen.getByRole('button', { name: /Añadir/i }));

    const dialogComboboxes3 = Array.from(dialog.querySelectorAll('[role="combobox"]'));
    await user.click(dialogComboboxes3[1] as HTMLElement);
    await user.click((await screen.findAllByRole('option', { name: 'Tela Algodon Premium' })).at(-1)!);
    inputs = dialog.querySelectorAll('input[type="text"]');
    await user.clear(inputs[0] as HTMLInputElement);
    await user.type(inputs[0] as HTMLInputElement, '10');
    await user.clear(inputs[1] as HTMLInputElement);
    await user.type(inputs[1] as HTMLInputElement, '10');
    await user.click(screen.getByRole('button', { name: /Añadir/i }));

    await waitFor(() => {
      const totalRow = dialog.querySelector('tr.bg-primary\\/5');
      expect(totalRow!.textContent).toContain('230.000');
    });

    const switches = screen.getAllByRole('switch');
    const toggleRetencion = switches[switches.length - 2];
    await user.click(toggleRetencion);
    const inputRetencionWrapper = screen.getByText('Valor de Retención ($)').parentElement as HTMLElement;
    const inputRetencion = inputRetencionWrapper.querySelector('input') as HTMLInputElement;
    await user.clear(inputRetencion);
    await user.type(inputRetencion, '200');
    expect(inputRetencion.value).toBe('200');

    const eliminarBtns = dialog.querySelectorAll('table tbody tr td button');
    await user.click(eliminarBtns[eliminarBtns.length - 1] as HTMLElement);

    await waitFor(() => {
      const totalRow = dialog.querySelector('tr.bg-primary\\/5');
      expect(totalRow!.textContent).toContain('115.000');
    });

    await user.click(screen.getByRole('button', { name: /Finalizar y Guardar/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('El valor de retención no puede superar el total de la factura');
    });
    expect(apiClient.post).not.toHaveBeenCalledWith('/pedidos-venta/', expect.anything());
  });
});

describe('VendedorDashboard — Nuevo Cliente: campos adicionales', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  async function abrirNuevoCliente(user: ReturnType<typeof userEvent.setup>) {
    await esperarDirectorio();
    await user.click(screen.getByRole('button', { name: /Nuevo Cliente/i }));
    await waitFor(() => expect(screen.getByText('Registrar Nuevo Cliente')).toBeInTheDocument());
  }

  it('dado el formulario de nuevo cliente cuando se selecciona nivel de precio Mayorista y se registra entonces el POST incluye nivel_precio mayorista', async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirNuevoCliente(user);

    await user.type(screen.getByLabelText('RUC/Cédula'), '0999999999');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Textiles Mayoristas');
    await user.type(screen.getByLabelText('Dirección'), 'Av. Principal');

    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;
    const combos = within(dialog).getAllByRole('combobox');
    await user.click(combos[0]);
    await user.click(await screen.findByText('Mayorista'));

    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/clientes/',
        expect.objectContaining({ nivel_precio: 'mayorista' })
      );
    });
  });

  it('dado el formulario de nuevo cliente cuando se ingresa un límite de crédito y se registra entonces el POST incluye ese límite', async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirNuevoCliente(user);

    await user.type(screen.getByLabelText('RUC/Cédula'), '0999999999');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Textiles Con Crédito');
    await user.type(screen.getByLabelText('Dirección'), 'Av. Principal');
    const limiteInput = screen.getByLabelText('Límite de Crédito ($)');
    await user.clear(limiteInput);
    await user.type(limiteInput, '2500');

    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/clientes/',
        expect.objectContaining({ limite_credito: 2500 })
      );
    });
  });

  it('dado el formulario de nuevo cliente cuando se selecciona un plazo de crédito de 60 días y se registra entonces el POST incluye ese plazo', async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirNuevoCliente(user);

    await user.type(screen.getByLabelText('RUC/Cédula'), '0999999999');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Textiles Plazo 60');
    await user.type(screen.getByLabelText('Dirección'), 'Av. Principal');

    const dialog = document.querySelector('[role="dialog"]') as HTMLElement;
    const combos = within(dialog).getAllByRole('combobox');
    await user.click(combos[1]);
    await user.click(await screen.findByText('60 Días'));

    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/clientes/',
        expect.objectContaining({ plazo_credito_dias: 60 })
      );
    });
  });

  it('dado el formulario de nuevo cliente cuando se activa "Tiene Beneficios" y se registra entonces el POST incluye tiene_beneficio true', async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirNuevoCliente(user);

    await user.type(screen.getByLabelText('RUC/Cédula'), '0999999999');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Textiles Beneficio');
    await user.type(screen.getByLabelText('Dirección'), 'Av. Principal');

    const beneficioSwitch = screen.getByText('Tiene Beneficios').closest('div')!.parentElement!.querySelector(
      'button[role="switch"]'
    ) as HTMLElement;
    await user.click(beneficioSwitch);

    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/clientes/',
        expect.objectContaining({ tiene_beneficio: true })
      );
    });
  });
});

describe('VendedorDashboard — Errores al guardar cliente', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  it('dado un error con data.detail cuando se crea un cliente entonces se muestra ese detalle como toast', async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: { detail: 'No tiene permisos para crear clientes.' } },
    });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    await user.click(screen.getByRole('button', { name: /Nuevo Cliente/i }));
    await waitFor(() => expect(screen.getByText('Registrar Nuevo Cliente')).toBeInTheDocument());

    await user.type(screen.getByLabelText('RUC/Cédula'), '0999999999');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Cliente X');
    await user.type(screen.getByLabelText('Dirección'), 'Calle X');
    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No tiene permisos para crear clientes.');
    });
  });

  it('dado un error sin response.data cuando se crea un cliente entonces se muestra un toast de error de conexión', async () => {
    (apiClient.post as any).mockRejectedValue(new Error('network down'));
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    await user.click(screen.getByRole('button', { name: /Nuevo Cliente/i }));
    await waitFor(() => expect(screen.getByText('Registrar Nuevo Cliente')).toBeInTheDocument());

    await user.type(screen.getByLabelText('RUC/Cédula'), '0999999999');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Cliente Y');
    await user.type(screen.getByLabelText('Dirección'), 'Calle Y');
    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error de conexión o servidor al guardar el cliente');
    });
  });
});

describe('VendedorDashboard — Paginación de clientes', () => {
  const muchosClientes = Array.from({ length: 25 }, (_, i) => ({
    ...CLIENTE_1,
    id: i + 1,
    nombre_razon_social: `Cliente ${i + 1}`,
    ruc_cedula: `100000000${i}`,
  }));

  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis({ clientes: muchosClientes });
  });

  it('dado más de 20 clientes en la página 2 cuando se hace clic en Anterior entonces vuelve a la página 1', async () => {
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /Siguiente/i }));
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Anterior/i }));

    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());
    expect(screen.getByText('Cliente 1')).toBeInTheDocument();
  });

  it('dado más de 20 clientes cuando se ingresa una página válida en "Ir a" y se presiona Enter entonces navega a esa página', async () => {
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());

    const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;
    await user.clear(irAInput);
    await user.type(irAInput, '2{Enter}');

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado más de 20 clientes cuando el input "Ir a" pierde el foco con una página válida entonces navega a esa página', async () => {
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());

    const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;
    await user.clear(irAInput);
    await user.type(irAInput, '2');
    await user.tab();

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });
});

describe('VendedorDashboard — Búsqueda y paginación de pedidos', () => {
  const muchosPedidos = Array.from({ length: 25 }, (_, i) => ({
    ...PEDIDO_PENDIENTE,
    id: i + 1,
    guia_remision: `GR-${String(i + 1).padStart(3, '0')}`,
  }));

  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('dado el listado de pedidos cuando se busca por guía de remisión entonces filtra los resultados', async () => {
    mockApis({ pedidos: [PEDIDO_PENDIENTE, PEDIDO_ANULADO] });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText('Buscar por guía o cliente...'), 'GR-001');

    expect(screen.getByText('GR-001')).toBeInTheDocument();
    expect(screen.queryByText('GR-002')).not.toBeInTheDocument();
  });

  it('dado un término de búsqueda de pedidos cuando se borra por completo entonces vuelve a mostrar todos los pedidos', async () => {
    mockApis({ pedidos: [PEDIDO_PENDIENTE, PEDIDO_ANULADO] });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());

    const input = screen.getByPlaceholderText('Buscar por guía o cliente...');
    await user.type(input, 'GR-001');
    expect(screen.queryByText('GR-002')).not.toBeInTheDocument();

    await user.clear(input);

    await waitFor(() => expect(screen.getByText('GR-002')).toBeInTheDocument());
  });

  it('dado más de 20 pedidos cuando se hace clic en Siguiente entonces navega a la página 2', async () => {
    mockApis({ pedidos: muchosPedidos });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Siguiente/i }));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado más de 20 pedidos en la página 2 cuando se hace clic en Anterior entonces vuelve a la página 1', async () => {
    mockApis({ pedidos: muchosPedidos });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /Siguiente/i }));
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Anterior/i }));

    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());
  });

  it('dado más de 20 pedidos cuando se ingresa una página válida en "Ir a" y se presiona Enter entonces navega a esa página', async () => {
    mockApis({ pedidos: muchosPedidos });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());

    const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;
    await user.clear(irAInput);
    await user.type(irAInput, '2{Enter}');

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado más de 20 pedidos cuando el input "Ir a" pierde el foco con una página válida entonces navega a esa página', async () => {
    mockApis({ pedidos: muchosPedidos });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());

    const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;
    await user.clear(irAInput);
    await user.type(irAInput, '2');
    await user.tab();

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });
});

describe('VendedorDashboard — Total de pedido con detalles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('dado un pedido con detalles cuando se renderiza el historial de ventas entonces el total se calcula sumando peso*precio + IVA de cada detalle', async () => {
    const pedidoConDetalles = {
      ...PEDIDO_PENDIENTE,
      valor_retencion: 10,
      detalles: [
        { id: 1, pedido_venta: 10, producto: 1, lote: null, cantidad: 1, piezas: 1, peso: 10, precio_unitario: 10, incluye_iva: true },
        { id: 2, pedido_venta: 10, producto: 1, lote: null, cantidad: 1, piezas: 1, peso: 5, precio_unitario: 4, incluye_iva: false },
      ],
    };
    mockApis({ pedidos: [pedidoConDetalles] });
    const user = userEvent.setup();
    renderComponent();
    await navigateToPedidos(user);
    await waitFor(() => expect(screen.getByText('GR-001')).toBeInTheDocument());

    // (10*10*1.15) + (5*4) - 10 retención = 115 + 20 - 10 = 125.000
    await waitFor(() => {
      const fila = screen.getByText('GR-001').closest('tr') as HTMLElement;
      expect(fila.textContent).toContain('125.000');
    });
  });
});

describe('VendedorDashboard — Reportes: fechas y variantes de exportación', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  async function irAReportes(user: ReturnType<typeof userEvent.setup>) {
    await esperarDirectorio();
    const tabs = screen.getAllByRole('tab');
    const reportesTab = tabs.find((t) => t.textContent?.includes('Reportes Excel'));
    await user.click(reportesTab!);
    await waitFor(() => expect(screen.getByText('Reportes Comerciales Avanzados')).toBeInTheDocument());
  }

  it('dado el formulario de reportes cuando se cambian las fechas de inicio y fin entonces los inputs reflejan los nuevos valores', async () => {
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const fechaInputs = document.querySelectorAll('input[type="date"]');
    const inicioInput = fechaInputs[0] as HTMLInputElement;
    const finInput = fechaInputs[1] as HTMLInputElement;

    await user.clear(inicioInput);
    await user.type(inicioInput, '2026-01-01');
    await user.clear(finInput);
    await user.type(finInput, '2026-01-31');

    expect(inicioInput.value).toBe('2026-01-01');
    expect(finInput.value).toBe('2026-01-31');
  });

  it('dado un rango de fechas válido cuando se exporta el reporte de top clientes exitosamente entonces descarga el archivo', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/top-clientes')) return Promise.resolve({ data: new Blob(['xlsx']) });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[1]);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/reporting/vendedores/1/top-clientes'),
        { responseType: 'blob' }
      );
    });
  });

  it('dado un error no-404 al exportar top clientes cuando la API falla entonces muestra el mensaje genérico de exportación', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/top-clientes')) return Promise.reject({ response: { status: 500 } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[1]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al exportar el reporte.');
    });
  });

  it('dado que no existen deudores para los parámetros cuando se exporta el reporte entonces muestra el mensaje específico de deudores', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/deudores')) return Promise.reject({ response: { status: 404 } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[2]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No se encontraron deudores en su cartera.');
    });
  });

  it('dado un error 422 al exportar ventas cuando la API responde entonces muestra el mensaje de parámetros inválidos', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/ventas')) return Promise.reject({ response: { status: 422 } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[0]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Parámetros inválidos. Verifica las fechas.');
    });
  });

  it('dado un error no clasificado al exportar ventas cuando la API falla entonces muestra el mensaje genérico de exportación', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      if (url.includes('/reporting/vendedores/1/ventas')) return Promise.reject(new Error('network error'));
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await irAReportes(user);

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[0]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al exportar el reporte.');
    });
  });
});

describe('VendedorDashboard — Expediente de cliente: campos adicionales de abono', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  it('dado el diálogo de abono abierto cuando se cambia el método de pago a Efectivo entonces el POST refleja el nuevo método', async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, { ...CLIENTE_1, pedidos: [], pagos: [] });
    await user.click(screen.getByRole('button', { name: /Abonos/i }));
    await waitFor(() => expect(screen.getByText('Registrar Abono / Pago')).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText('0.00'), '100');
    const dialog = screen.getByText('Registrar Abono / Pago').closest('[role="dialog"]') as HTMLElement;
    const metodoCombo = within(dialog).getAllByRole('combobox')[0];
    await user.click(metodoCombo);
    await user.click(await screen.findByText('Efectivo'));
    await user.click(screen.getByRole('button', { name: /Confirmar Abono/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/pagos-cliente/',
        expect.objectContaining({ metodo_pago: 'efectivo' })
      );
    });
  });

  it('dado el diálogo de abono abierto cuando se ingresa una referencia de comprobante entonces el POST la incluye', async () => {
    (apiClient.post as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, { ...CLIENTE_1, pedidos: [], pagos: [] });
    await user.click(screen.getByRole('button', { name: /Abonos/i }));
    await waitFor(() => expect(screen.getByText('Registrar Abono / Pago')).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText('0.00'), '100');
    await user.type(screen.getByPlaceholderText('# Transacción'), 'TRX-555');
    await user.click(screen.getByRole('button', { name: /Confirmar Abono/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/pagos-cliente/',
        expect.objectContaining({ comprobante: 'TRX-555' })
      );
    });
  });

  it('dado el diálogo de abono abierto cuando se hace clic en Cancelar entonces se cierra sin llamar a la API', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderComponent();
    await abrirExpedienteCliente(user, { ...CLIENTE_1, pedidos: [], pagos: [] });
    await user.click(screen.getByRole('button', { name: /Abonos/i }));
    await waitFor(() => expect(screen.getByText('Registrar Abono / Pago')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /^Cancelar$/i }));

    await waitFor(() => expect(screen.queryByText('Registrar Abono / Pago')).not.toBeInTheDocument());
    expect(apiClient.post).not.toHaveBeenCalledWith('/pagos-cliente/', expect.anything());
  });

  it('dado que falla la carga del detalle del cliente cuando se hace clic en su fila entonces usa el cliente de la lista como respaldo', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url === '/clientes/1/') return Promise.reject(new Error('network error'));
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    await user.click(screen.getByText('Cliente Prueba'));

    await waitFor(() => {
      expect(screen.getByText(/Expediente de Cliente: Cliente Prueba/)).toBeInTheDocument();
    });
  });

  it('dado un pedido en el historial del expediente cuando se hace clic en el botón de imprimir entonces descarga el PDF de ese pedido', async () => {
    const clienteDetallado = {
      ...CLIENTE_1,
      pedidos: [{ id: 30, guia_remision: 'GR-030', fecha_pedido: '2026-05-01T10:00:00Z', total: 150 }],
      pagos: [],
    };
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url === '/clientes/1/') return Promise.resolve({ data: clienteDetallado });
      if (url.includes('download_pdf')) return Promise.resolve({ data: new Blob(['pdf']) });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    await user.click(screen.getByText('Cliente Prueba'));
    await waitFor(() => expect(screen.getByText('GR-030')).toBeInTheDocument());

    const fila = screen.getByText('GR-030').closest('tr') as HTMLElement;
    await user.click(within(fila).getByRole('button'));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/pedidos-venta/30/download_pdf/', { responseType: 'blob' });
    });
  });
});
