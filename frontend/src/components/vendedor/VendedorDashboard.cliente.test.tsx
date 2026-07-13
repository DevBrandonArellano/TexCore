import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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

const CLIENTE_1 = {
  id: 1,
  nombre_razon_social: 'Cliente Uno',
  limite_credito: 1000,
  saldo_pendiente: 0,
  plazo_credito_dias: 30,
  ruc_cedula: '1234567890',
  direccion_envio: 'Test Dir',
  nivel_precio: 'normal',
  tiene_beneficio: false,
  cartera_vencida: 0,
  is_active: true,
};

function mockApis(clientes: any[] = [CLIENTE_1]) {
  (apiClient.get as any).mockImplementation((url: string) => {
    if (url === '/clientes/') return Promise.resolve({ data: clientes });
    if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
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

async function esperarDirectorio() {
  await waitFor(() => expect(screen.getByText('Directorio de Clientes')).toBeInTheDocument());
}

function filaDe(nombre: string) {
  return screen.getByText(nombre).closest('tr') as HTMLElement;
}

describe('VendedorDashboard — Gestión de Clientes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    mockApis();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Creación de cliente ─────────────────────────────────────────────────────

  it('crea un nuevo cliente y llama a POST /clientes/ con los datos del formulario', async () => {
    (apiClient.post as any).mockResolvedValue({ data: { id: 99 } });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    await user.click(screen.getByRole('button', { name: /Nuevo Cliente/i }));
    await waitFor(() => expect(screen.getByText('Registrar Nuevo Cliente')).toBeInTheDocument());

    await user.type(screen.getByLabelText('RUC/Cédula'), '0999999999');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Textiles Andinos S.A.');
    await user.type(screen.getByLabelText('Dirección'), 'Av. Siempre Viva 123');

    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/clientes/',
        expect.objectContaining({
          ruc_cedula: '0999999999',
          nombre_razon_social: 'Textiles Andinos S.A.',
          direccion_envio: 'Av. Siempre Viva 123',
          nivel_precio: 'normal',
          limite_credito: 0,
          plazo_credito_dias: 0,
        })
      );
    });
    const payload = (apiClient.post as any).mock.calls[0][1];
    expect(payload).not.toHaveProperty('_justificacion_auditoria');
    expect(payload).not.toHaveProperty('saldo_pendiente');
    expect(payload).not.toHaveProperty('cartera_vencida');
    expect(toast.success).toHaveBeenCalledWith('Cliente registrado correctamente');
  });

  it('muestra un toast de error de validación por campo cuando el backend rechaza la creación', async () => {
    (apiClient.post as any).mockRejectedValue({
      response: { data: { ruc_cedula: ['Ya existe un cliente con este RUC.'] } },
    });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    await user.click(screen.getByRole('button', { name: /Nuevo Cliente/i }));
    await waitFor(() => expect(screen.getByText('Registrar Nuevo Cliente')).toBeInTheDocument());

    await user.type(screen.getByLabelText('RUC/Cédula'), '1234567890');
    await user.type(screen.getByLabelText('Nombre / Razón Social'), 'Cliente Duplicado');
    await user.type(screen.getByLabelText('Dirección'), 'Calle X');
    await user.click(screen.getByRole('button', { name: /^Registrar$/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Error de validación',
        expect.objectContaining({ description: expect.stringContaining('ruc_cedula') })
      );
    });
  });

  // ── Edición de cliente ──────────────────────────────────────────────────────

  it('abre el modal de edición con los datos del cliente precargados', async () => {
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    const fila = filaDe('Cliente Uno');
    const botones = within(fila).getAllByRole('button');
    await user.click(botones[0]); // botón de edición (ícono CreditCard)

    await waitFor(() => expect(screen.getByText('Editar Cliente')).toBeInTheDocument());
    expect(screen.getByDisplayValue('Cliente Uno')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1234567890')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Dir')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Cambio de dirección solicitado/i)).toBeInTheDocument();
  });

  it('llama a PUT /clientes/:id/ con la justificación de auditoría al actualizar', async () => {
    (apiClient.put as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    const fila = filaDe('Cliente Uno');
    const botones = within(fila).getAllByRole('button');
    await user.click(botones[0]);
    await waitFor(() => expect(screen.getByText('Editar Cliente')).toBeInTheDocument());

    const direccionInput = screen.getByDisplayValue('Test Dir');
    await user.clear(direccionInput);
    await user.type(direccionInput, 'Nueva Dirección 456');

    const justificacionInput = screen.getByPlaceholderText(/Cambio de dirección solicitado/i);
    await user.type(justificacionInput, 'Cliente solicitó cambio de dirección de envío');

    await user.click(screen.getByRole('button', { name: /^Actualizar$/i }));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith(
        '/clientes/1/',
        expect.objectContaining({
          direccion_envio: 'Nueva Dirección 456',
          _justificacion_auditoria: 'Cliente solicitó cambio de dirección de envío',
        })
      );
    });
    expect(toast.success).toHaveBeenCalledWith('Cliente actualizado correctamente');
  });

  // ── Inactivación de cliente ─────────────────────────────────────────────────

  it('inactiva al cliente cuando se confirma el diálogo nativo de confirmación', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    (apiClient.patch as any).mockResolvedValue({ data: {} });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    const fila = filaDe('Cliente Uno');
    const botones = within(fila).getAllByRole('button');
    await user.click(botones[1]); // botón de inactivar (ícono Trash2)

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith(
        '/clientes/1/',
        expect.objectContaining({ is_active: false })
      );
    });
    expect(toast.success).toHaveBeenCalledWith('Cliente inactivado correctamente');
  });

  it('no inactiva al cliente cuando se cancela el diálogo nativo de confirmación', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    const fila = filaDe('Cliente Uno');
    const botones = within(fila).getAllByRole('button');
    await user.click(botones[1]);

    expect(apiClient.patch).not.toHaveBeenCalled();
    expect(toast.success).not.toHaveBeenCalled();
  });

  // ── Búsqueda y paginación ────────────────────────────────────────────────────

  it('filtra el directorio de clientes según el término de búsqueda', async () => {
    mockApis([
      CLIENTE_1,
      { ...CLIENTE_1, id: 2, nombre_razon_social: 'Cliente Dos', ruc_cedula: '9999999999' },
    ]);
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    await waitFor(() => expect(screen.getByText('Cliente Dos')).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText('Buscar cliente...'), 'Uno');

    expect(screen.getByText('Cliente Uno')).toBeInTheDocument();
    expect(screen.queryByText('Cliente Dos')).not.toBeInTheDocument();
  });

  it('pagina el directorio de clientes cuando hay más de 20 resultados', async () => {
    const muchosClientes = Array.from({ length: 25 }, (_, i) => ({
      ...CLIENTE_1,
      id: i + 1,
      nombre_razon_social: `Cliente ${i + 1}`,
      ruc_cedula: `100000000${i}`,
    }));
    mockApis(muchosClientes);
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    await waitFor(() => expect(screen.getAllByText('Cliente 1').length).toBeGreaterThan(0), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());
    expect(screen.getByText('Cliente 1')).toBeInTheDocument();
    expect(screen.queryByText('Cliente 21')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Siguiente/i }));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('Cliente 21')).toBeInTheDocument();
    expect(screen.queryByText('Cliente 1')).not.toBeInTheDocument();
  });

  // ── Expediente de cliente ────────────────────────────────────────────────────

  it('abre el expediente del cliente y muestra su historial de pedidos y pagos', async () => {
    const clienteDetallado = {
      ...CLIENTE_1,
      pedidos: [
        { id: 5, guia_remision: 'GR-500', fecha_pedido: '2026-05-01T10:00:00Z', total: 150 },
      ],
      pagos: [
        { id: 7, fecha: '2026-05-02T10:00:00Z', metodo_pago: 'efectivo', monto: 50 },
      ],
    };
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/clientes/') return Promise.resolve({ data: [CLIENTE_1] });
      if (url === '/clientes/1/') return Promise.resolve({ data: clienteDetallado });
      if (url.includes('/pedidos-venta/')) return Promise.resolve({ data: [] });
      if (url.includes('/productos/')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    await user.click(screen.getByText('Cliente Uno'));

    await waitFor(() => {
      expect(screen.getByText(/Expediente de Cliente: Cliente Uno/)).toBeInTheDocument();
    });
    expect(screen.getByText('GR-500')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /Abonos \/ Recibos/i }));
    await waitFor(() => expect(screen.getByText('efectivo')).toBeInTheDocument());
  });

  // ── Mora / cartera vencida ───────────────────────────────────────────────────

  it('muestra la insignia de mora y los días transcurridos cuando el cliente tiene cartera vencida', async () => {
    const haceCincoDias = new Date();
    haceCincoDias.setDate(haceCincoDias.getDate() - 5);
    mockApis([
      {
        ...CLIENTE_1,
        cartera_vencida: 120,
        ultima_compra: {
          fecha: haceCincoDias.toISOString(),
          id_pedido: 1,
          items: [{ producto: 'Tela', cantidad: 1, piezas: 1, peso: 1 }],
        },
      },
    ]);
    renderComponent();
    await esperarDirectorio();

    await waitFor(() => expect(screen.getByText(/Mora: \$120.000/)).toBeInTheDocument());
    expect(screen.getByText(/Últ\. factura hace \d+ días/)).toBeInTheDocument();
  });

  // ── Reset del formulario de cliente ──────────────────────────────────────────

  it('limpia el formulario de Nuevo Cliente al cerrar el diálogo sin guardar', async () => {
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    await user.click(screen.getByRole('button', { name: /Nuevo Cliente/i }));
    await waitFor(() => expect(screen.getByText('Registrar Nuevo Cliente')).toBeInTheDocument());
    await user.type(screen.getByLabelText('RUC/Cédula'), '0011223344');

    // No hay botón "Cancelar" en este diálogo; se cierra con Escape para
    // disparar onOpenChange(false), que debe limpiar el formulario.
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByText('Registrar Nuevo Cliente')).not.toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Nuevo Cliente/i }));
    await waitFor(() => expect(screen.getByText('Registrar Nuevo Cliente')).toBeInTheDocument());
    expect((screen.getByLabelText('RUC/Cédula') as HTMLInputElement).value).toBe('');
  });

  // ── Manejo de errores ────────────────────────────────────────────────────────

  it('muestra un toast de error si la API falla al inactivar un cliente', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    (apiClient.patch as any).mockRejectedValue(new Error('network error'));
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();

    const fila = filaDe('Cliente Uno');
    const botones = within(fila).getAllByRole('button');
    await user.click(botones[1]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al inactivar el cliente');
    });
  });

  it('elimina el término de búsqueda y vuelve a mostrar todos los clientes', async () => {
    mockApis([
      CLIENTE_1,
      { ...CLIENTE_1, id: 2, nombre_razon_social: 'Cliente Dos', ruc_cedula: '9999999999' },
    ]);
    const user = userEvent.setup();
    renderComponent();
    await esperarDirectorio();
    await waitFor(() => expect(screen.getByText('Cliente Dos')).toBeInTheDocument());

    const input = screen.getByPlaceholderText('Buscar cliente...');
    await user.type(input, 'Uno');
    expect(screen.queryByText('Cliente Dos')).not.toBeInTheDocument();

    await user.clear(input);
    await waitFor(() => expect(screen.getByText('Cliente Dos')).toBeInTheDocument());
  });
});
