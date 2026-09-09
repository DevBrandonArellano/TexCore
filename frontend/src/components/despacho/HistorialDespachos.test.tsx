import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { HistorialDespachos } from './HistorialDespachos';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockNavigate = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

const DESPACHO_1 = {
  id: 1,
  fecha_despacho: '2026-07-10T14:30:00',
  usuario_nombre: 'Juan Pérez',
  total_bultos: 5,
  total_peso: '120.50',
  observaciones: '',
  pedidos_detalle: [
    { id: 1, guia_remision: 'G-001', cliente_nombre: 'Cliente A', cantidad_despachada: '10' },
  ],
  detalles: [
    { id: 1, codigo_lote: 'LOTE-001', producto_nombre: 'Hilo Poliéster', peso: '50.25', es_devolucion: false },
  ],
};

const DESPACHO_MULTI = {
  id: 2,
  fecha_despacho: '2026-07-05T09:00:00',
  usuario_nombre: 'Ana Torres',
  total_bultos: 8,
  total_peso: '200.00',
  observaciones: '',
  pedidos_detalle: [
    { id: 2, guia_remision: 'G-002', cliente_nombre: 'Cliente B', cantidad_despachada: '5' },
    { id: 3, guia_remision: 'G-003', cliente_nombre: 'Cliente C', cantidad_despachada: '15' },
  ],
  detalles: [
    { id: 2, codigo_lote: 'LOTE-002', producto_nombre: 'Hilo Nylon', peso: '100.00', es_devolucion: false },
  ],
};

const DESPACHO_CON_FALTANTES = {
  ...DESPACHO_1,
  id: 3,
  items_no_despachados: {
    'Hilo Nylon': { requerido: 100, escaneado: 60, faltante: 40 },
  },
};

function makeResponse(results: any[], overrides: Partial<{ count: number; next: string | null; previous: string | null }> = {}) {
  return { count: results.length, next: null, previous: null, results, ...overrides };
}

function renderComponent(initialEntries: string[] = ['/']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <HistorialDespachos />
    </MemoryRouter>,
  );
}

describe('HistorialDespachos', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockNavigate.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    window.open = vi.fn();
  });

  it('dado clic en imprimir historial cuando se presiona entonces llama al endpoint con los filtros y abre el pdf', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/inventory/historial-despachos/imprimir/')) {
        return Promise.resolve({ data: new Blob(['%PDF-fake']) });
      }
      return Promise.resolve({ data: makeResponse([]) });
    });
    renderComponent();
    await waitFor(() =>
      expect(screen.getByText('No se encontraron despachos para los filtros actuales.')).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole('button', { name: /imprimir historial/i }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      '/inventory/historial-despachos/imprimir/?',
      { responseType: 'blob' },
    ));
    expect(window.open).toHaveBeenCalledWith('blob:mock-url', '_blank');
  });

  it('dado clic en generar guia de remision cuando se presiona entonces abre el modal para ese despacho', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    renderComponent();
    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());

    await userEvent.click(screen.getByTitle('Generar Guía de Remisión'));

    expect(screen.getByText('Generar Guía de Remisión', { selector: 'h2' })).toBeInTheDocument();
  });

  it('dado clic en volver a despacho cuando se presiona entonces navega a la raiz', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([]) });
    renderComponent();

    await waitFor(() =>
      expect(screen.getByText('No se encontraron despachos para los filtros actuales.')).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole('button', { name: /volver a despacho/i }));

    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('dado datos aun no resueltos cuando monta entonces muestra el estado de carga', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { container } = renderComponent();

    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('dado sin despachos cuando carga entonces muestra el mensaje de lista vacia', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([]) });
    renderComponent();

    await waitFor(() =>
      expect(screen.getByText('No se encontraron despachos para los filtros actuales.')).toBeInTheDocument(),
    );
  });

  it('dado despachos existentes cuando carga entonces lista sus datos reales', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1, DESPACHO_MULTI]) });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());

    expect(screen.getByText('Juan Pérez')).toBeInTheDocument();
    expect(screen.getByText('Cliente A')).toBeInTheDocument();
    expect(screen.getByText('Guía: G-001')).toBeInTheDocument();
    expect(screen.getByText('120.50 kg')).toBeInTheDocument();
    expect(
      screen.getByText(format(new Date(DESPACHO_1.fecha_despacho), 'dd MMM yyyy', { locale: es })),
    ).toBeInTheDocument();

    expect(screen.getByText('#2')).toBeInTheDocument();
    expect(screen.getByText('2 Pedidos Múltiples')).toBeInTheDocument();
  });

  it('dado filtros de fecha cuando busca entonces refetch con fecha_desde y fecha_hasta y reinicia la pagina', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    const { container } = renderComponent(['/?page=2']);

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    expect(mockGet).toHaveBeenLastCalledWith('/inventory/historial-despachos/?page=2');

    const dateInputs = container.querySelectorAll('input[type="date"]');
    expect(dateInputs).toHaveLength(2);

    await userEvent.type(dateInputs[0], '2026-07-01');
    await userEvent.type(dateInputs[1], '2026-07-10');
    await userEvent.click(screen.getByRole('button', { name: /Buscar/ }));

    await waitFor(() =>
      expect(mockGet).toHaveBeenLastCalledWith(
        '/inventory/historial-despachos/?page=1&fecha_desde=2026-07-01&fecha_hasta=2026-07-10',
      ),
    );

    const limpiarButton = screen.getByRole('button', { name: 'Limpiar' });
    await userEvent.click(limpiarButton);

    await waitFor(() => expect(mockGet).toHaveBeenLastCalledWith('/inventory/historial-despachos/?page=1'));
    expect(screen.queryByRole('button', { name: 'Limpiar' })).not.toBeInTheDocument();
  });

  it('dado clic en ver detalles cuando abre el modal entonces muestra pedidos y lotes del despacho', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Ver detalles' }));

    expect(screen.getByText('Detalle de Despacho #1')).toBeInTheDocument();
    expect(screen.getByText('LOTE-001')).toBeInTheDocument();
    expect(screen.getByText('50.25 kg')).toBeInTheDocument();
  });

  it('dado items no despachados presentes cuando abre el modal de detalle entonces los muestra', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_CON_FALTANTES]) });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#3')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Ver detalles' }));

    expect(screen.getByText('Items No Despachados')).toBeInTheDocument();
    expect(screen.getByText('Hilo Nylon')).toBeInTheDocument();
    expect(screen.getByText('Requerido: 100 · Escaneado: 60 · Faltante: 40')).toBeInTheDocument();
  });

  it('dado despacho sin items no despachados cuando abre el modal de detalle entonces no muestra la seccion', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Ver detalles' }));

    expect(screen.queryByText('Items No Despachados')).not.toBeInTheDocument();
  });

  it('dado clic en revertir cuando abre el modal entonces deshabilita confirmar hasta ingresar justificacion', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Revertir despacho' }));

    expect(screen.getByText('Revertir Despacho')).toBeInTheDocument();
    expect(screen.getByText('Despacho #1')).toBeInTheDocument();
    expect(screen.getByText(/restaurarán 120.50 kg de stock/)).toBeInTheDocument();

    const confirmarButton = screen.getByRole('button', { name: 'Confirmar Reversión' });
    expect(confirmarButton).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Ingresa el motivo de la reversión/);
    await userEvent.type(textarea, 'Error en selección de lotes');

    expect(confirmarButton).not.toBeDisabled();

    await userEvent.clear(textarea);
    await userEvent.type(textarea, '   ');
    expect(confirmarButton).toBeDisabled();
  });

  it('dado justificacion valida cuando confirma la reversion entonces llama al endpoint y refresca la lista', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    mockPost.mockResolvedValueOnce({ data: {} });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Revertir despacho' }));

    const textarea = screen.getByPlaceholderText(/Ingresa el motivo de la reversión/);
    await userEvent.type(textarea, 'Cliente rechazó la mercadería');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Reversión' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith('/inventory/historial-despachos/1/revertir/', {
        justificacion: 'Cliente rechazó la mercadería',
      }),
    );
    await waitFor(() =>
      expect(toastSuccessMock).toHaveBeenCalledWith('Despacho revertido exitosamente. Stock restaurado a bodegas.'),
    );
    expect(screen.queryByText('Revertir Despacho')).not.toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  it('dado un error del servidor cuando confirma la reversion entonces muestra el toast de error y mantiene el modal abierto', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    mockPost.mockRejectedValueOnce({ response: { data: { error: 'El despacho ya fue revertido' } } });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Revertir despacho' }));

    const textarea = screen.getByPlaceholderText(/Ingresa el motivo de la reversión/);
    await userEvent.type(textarea, 'Motivo de prueba');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Reversión' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('El despacho ya fue revertido'));
    expect(screen.getByText('Revertir Despacho')).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it('dado solo fecha hasta llenada cuando busca entonces borra el filtro fecha_desde y aplica fecha_hasta', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    const { container } = renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    const dateInputs = container.querySelectorAll('input[type="date"]');
    await userEvent.type(dateInputs[1], '2026-07-10');
    await userEvent.click(screen.getByRole('button', { name: /Buscar/ }));

    await waitFor(() =>
      expect(mockGet).toHaveBeenLastCalledWith(
        '/inventory/historial-despachos/?page=1&fecha_hasta=2026-07-10',
      ),
    );
  });

  it('dado solo fecha desde llenada cuando busca entonces borra el filtro fecha_hasta y aplica fecha_desde', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    const { container } = renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    const dateInputs = container.querySelectorAll('input[type="date"]');
    await userEvent.type(dateInputs[0], '2026-07-01');
    await userEvent.click(screen.getByRole('button', { name: /Buscar/ }));

    await waitFor(() =>
      expect(mockGet).toHaveBeenLastCalledWith(
        '/inventory/historial-despachos/?page=1&fecha_desde=2026-07-01',
      ),
    );
  });

  it('dado error de reversion con clave justificacion cuando falla entonces muestra ese mensaje', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    mockPost.mockRejectedValueOnce({ response: { data: { justificacion: 'Justificación inválida' } } });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Revertir despacho' }));
    const textarea = screen.getByPlaceholderText(/Ingresa el motivo de la reversión/);
    await userEvent.type(textarea, 'Motivo de prueba');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Reversión' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Justificación inválida'));
  });

  it('dado error de reversion sin mensaje del backend cuando falla entonces muestra el mensaje generico', async () => {
    mockGet.mockResolvedValue({ data: makeResponse([DESPACHO_1]) });
    mockPost.mockRejectedValueOnce({ response: { data: {} } });
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Revertir despacho' }));
    const textarea = screen.getByPlaceholderText(/Ingresa el motivo de la reversión/);
    await userEvent.type(textarea, 'Motivo de prueba');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Reversión' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al revertir el despacho'));
  });

  it('dado filtros de fecha en la url cuando imprime el historial entonces los incluye en la peticion', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/inventory/historial-despachos/imprimir/')) {
        return Promise.resolve({ data: new Blob(['%PDF-fake']) });
      }
      return Promise.resolve({ data: makeResponse([DESPACHO_1]) });
    });
    renderComponent(['/?fecha_desde=2026-07-01&fecha_hasta=2026-07-10']);
    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /imprimir historial/i }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      '/inventory/historial-despachos/imprimir/?fecha_desde=2026-07-01&fecha_hasta=2026-07-10',
      { responseType: 'blob' },
    ));
  });

  it('dado error al cargar el historial cuando falla la peticion entonces muestra un toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    renderComponent();

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar el historial de despachos'),
    );
    expect(screen.getAllByRole('row')).toHaveLength(1);
  });
});
