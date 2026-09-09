import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DespachoDashboard } from './DespachoDashboard';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
const toastWarningMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
    warning: (...args: any[]) => toastWarningMock(...args),
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const PEDIDO_1 = {
  id: 1,
  cliente: 100,
  cliente_nombre: 'Cliente A',
  guia_remision: 'G-001',
  fecha_pedido: '2026-07-01T12:00:00',
  estado: 'pendiente',
  esta_pagado: true,
  sede: 1,
  detalles: [
    { id: 1, pedido_venta: 1, producto: 10, producto_nombre: 'Hilo Poliéster', producto_descripcion: 'Hilo Poliéster', lote: null, cantidad: 1, piezas: 1, peso: 50, precio_unitario: 1 },
  ],
  total: 500,
  anulado: false,
};

const PEDIDO_2 = {
  ...PEDIDO_1,
  id: 2,
  guia_remision: 'G-002',
  esta_pagado: false,
  detalles: [
    { id: 2, pedido_venta: 2, producto: 11, producto_nombre: 'Hilo Nylon', producto_descripcion: 'Hilo Nylon', lote: null, cantidad: 1, piezas: 1, peso: 30, precio_unitario: 1 },
  ],
};

const PEDIDO_3 = {
  ...PEDIDO_1,
  id: 3,
  cliente: 200,
  cliente_nombre: 'Cliente B',
  guia_remision: 'G-003',
};

function mockPedidosResponse(pedidos: any[]) {
  mockGet.mockImplementation((url: string) => {
    if (url.startsWith('/pedidos-venta/?estado=pendiente')) {
      return Promise.resolve({ data: pedidos });
    }
    if (url.includes('/download_pdf/')) {
      return Promise.resolve({ data: new Blob(['pdf']) });
    }
    return Promise.resolve({ data: [] });
  });
}

function renderComponent() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <DespachoDashboard />
    </MemoryRouter>,
  );
}

async function enterDespachoMode(pedidos: any[], selectIndexes: number[] = [0]) {
  mockPedidosResponse(pedidos);
  renderComponent();
  await waitFor(() => expect(screen.getByText(`#${pedidos[0].guia_remision}`)).toBeInTheDocument());

  const checkboxes = screen.getAllByRole('checkbox');
  for (const idx of selectIndexes) {
    await userEvent.click(checkboxes[idx]);
  }
  await userEvent.click(screen.getByRole('button', { name: /Iniciar Despacho/ }));
  await waitFor(() => expect(screen.getByText('Procesando Despacho')).toBeInTheDocument());
}

async function scanLote(codigo: string) {
  const input = screen.getByPlaceholderText('Escanea aquí (Ej: LOTE-1234)');
  await userEvent.type(input, `${codigo}{enter}`);
}

describe('DespachoDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    toastWarningMock.mockReset();
    mockNavigate.mockReset();
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    window.open = vi.fn();
  });

  it('dado datos aun no resueltos cuando monta entonces muestra el estado de carga', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { container } = renderComponent();

    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('dado pedidos pendientes cuando carga entonces lista los datos reales', async () => {
    mockPedidosResponse([PEDIDO_1, PEDIDO_2]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());
    expect(screen.getAllByText('Cliente A')).toHaveLength(2);
    expect(screen.getByText('#G-002')).toBeInTheDocument();
    expect(screen.getByText('50.00 kg')).toBeInTheDocument();
    expect(screen.getByText('30.00 kg')).toBeInTheDocument();
    expect(screen.getByText('Pagado')).toBeInTheDocument();
    expect(screen.getByText('Crédito')).toBeInTheDocument();
  });

  it('dado sin pedidos pendientes cuando carga entonces muestra el mensaje de lista vacia', async () => {
    mockPedidosResponse([]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('No hay pedidos pendientes.')).toBeInTheDocument());
  });

  it('dado error al cargar pedidos cuando falla la peticion entonces muestra un toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    renderComponent();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar pedidos pendientes'));
    expect(screen.getByText('No hay pedidos pendientes.')).toBeInTheDocument();
  });

  it('dado un texto de busqueda cuando filtra entonces solo muestra los pedidos coincidentes', async () => {
    mockPedidosResponse([PEDIDO_1, PEDIDO_3]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('Cliente A')).toBeInTheDocument());
    expect(screen.getByText('Cliente B')).toBeInTheDocument();

    const search = screen.getByPlaceholderText('Buscar por cliente, guía...');
    await userEvent.type(search, 'Cliente B');

    await waitFor(() => expect(screen.queryByText('Cliente A')).not.toBeInTheDocument());
    expect(screen.getByText('Cliente B')).toBeInTheDocument();
  });

  it('dado un pedido seleccionado cuando marca la fila entonces muestra el contador y el boton iniciar despacho', async () => {
    mockPedidosResponse([PEDIDO_1, PEDIDO_2]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());
    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[0]);

    expect(screen.getByText('1 Pedido')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Iniciar Despacho/ })).toBeInTheDocument();
  });

  it('dado pedidos de distintos clientes cuando inicia despacho entonces advierte pero continua', async () => {
    await enterDespachoMode([PEDIDO_1, PEDIDO_3], [0, 1]);

    expect(toastWarningMock).toHaveBeenCalledWith(
      'Has seleccionado pedidos de diferentes clientes. Asegúrate de que esto sea intencional.',
    );
  });

  it('dado pedidos del mismo cliente cuando inicia despacho entonces no advierte', async () => {
    await enterDespachoMode([PEDIDO_1, PEDIDO_2], [0, 1]);

    expect(toastWarningMock).not.toHaveBeenCalled();
  });

  it('dado el modo despacho recien iniciado cuando aun no escanea entonces muestra el mensaje de espera', async () => {
    await enterDespachoMode([PEDIDO_1]);

    expect(screen.getByText('Esperando escaneo...')).toBeInTheDocument();
    expect(screen.getByText('0.00 / 50.00 kg')).toBeInTheDocument();
  });

  it('dado un codigo de lote valido cuando escanea entonces lo agrega a la tabla y notifica', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({
      data: { valid: true, lote: { codigo: 'LOTE-1001', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '25.50' } },
    });

    await scanLote('LOTE-1001');

    expect(mockPost).toHaveBeenCalledWith('/scanning/validate', { code: 'LOTE-1001' });
    await waitFor(() => expect(screen.getByText('LOTE-1001')).toBeInTheDocument());
    expect(screen.getByText('25.50')).toBeInTheDocument();
    expect(toastSuccessMock).toHaveBeenCalledWith('Lote LOTE-1001 agregado (25.5kg)');
  });

  it('dado un codigo de lote invalido con motivo cuando escanea entonces muestra el motivo', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({ data: { valid: false, reason: 'Lote ya despachado anteriormente' } });

    await scanLote('LOTE-9999');

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Lote ya despachado anteriormente'));
    expect(screen.getByText('Esperando escaneo...')).toBeInTheDocument();
  });

  it('dado un codigo de lote invalido sin motivo cuando escanea entonces muestra el mensaje por defecto', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({ data: { valid: false } });

    await scanLote('LOTE-9999');

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Lote no válido o no disponible'));
  });

  it('dado un error de red cuando escanea entonces muestra un toast de error', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockRejectedValueOnce(new Error('boom'));

    await scanLote('LOTE-1001');

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al validar el código de barras'));
  });

  it('dado un lote ya escaneado cuando lo vuelve a escanear entonces advierte y no lo duplica', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({
      data: { valid: true, lote: { codigo: 'LOTE-1001', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '25.50' } },
    });
    await scanLote('LOTE-1001');
    await waitFor(() => expect(screen.getByText('LOTE-1001')).toBeInTheDocument());

    await scanLote('LOTE-1001');

    expect(toastWarningMock).toHaveBeenCalledWith('Este lote ya fue escaneado.');
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText('LOTE-1001')).toHaveLength(1);
  });

  it('dado un item escaneado cuando lo elimina entonces lo remueve de la tabla', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({
      data: { valid: true, lote: { codigo: 'LOTE-1001', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '25.50' } },
    });
    await scanLote('LOTE-1001');
    await waitFor(() => expect(screen.getByText('LOTE-1001')).toBeInTheDocument());

    const row = screen.getByText('LOTE-1001').closest('tr')!;
    const removeButton = within(row).getByRole('button');
    await userEvent.click(removeButton);

    expect(screen.queryByText('LOTE-1001')).not.toBeInTheDocument();
    expect(screen.getByText('Esperando escaneo...')).toBeInTheDocument();
  });

  it('dado items escaneados cuando coinciden con lo requerido entonces actualiza el progreso de la carga', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost
      .mockResolvedValueOnce({
        data: { valid: true, lote: { codigo: 'LOTE-1001', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '25.50' } },
      })
      .mockResolvedValueOnce({
        data: { valid: true, lote: { codigo: 'LOTE-1002', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '24.50' } },
      });

    await scanLote('LOTE-1001');
    await waitFor(() => expect(screen.getByText('25.50 / 50.00 kg')).toBeInTheDocument());

    await scanLote('LOTE-1002');
    await waitFor(() => expect(screen.getByText('50.00 / 50.00 kg')).toBeInTheDocument());
  });

  it('dado un despacho exitoso cuando confirma la salida entonces envia los lotes y descarga los pdf', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({
      data: { valid: true, lote: { codigo: 'LOTE-1001', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '50.00' } },
    });
    await scanLote('LOTE-1001');
    await waitFor(() => expect(screen.getByText('LOTE-1001')).toBeInTheDocument());

    mockPost.mockResolvedValueOnce({ data: {} });
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Salida' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith('/inventory/process-despacho/', {
        pedidos: [1],
        lotes: ['LOTE-1001'],
        confirmar_incompleto: false,
      }),
    );
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Despacho procesado exitosamente'));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/pedidos-venta/1/download_pdf/', { responseType: 'blob' }));
    expect(window.open).toHaveBeenCalledWith('blob:mock-url', '_blank');
    await waitFor(() => expect(screen.getByText('Panel de Despacho')).toBeInTheDocument());
  });

  it('dado una respuesta 409 con items incompletos cuando confirma la salida entonces muestra el modal con la tabla de faltantes', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { items_incompletos: { 'Hilo Poliéster': { requerido: 50, escaneado: 25.5, faltante: 24.5 } } },
      },
    });

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Salida' }));

    await waitFor(() => expect(screen.getByText('Despacho incompleto')).toBeInTheDocument());
    expect(screen.getByText('50.00 kg')).toBeInTheDocument();
    expect(screen.getByText('25.50 kg')).toBeInTheDocument();
    expect(screen.getByText('-24.50 kg')).toBeInTheDocument();
  });

  it('dado el modal de despacho incompleto abierto cuando cancela entonces sigue escaneando sin enviar de nuevo', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { items_incompletos: { 'Hilo Poliéster': { requerido: 50, escaneado: 25.5, faltante: 24.5 } } },
      },
    });
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Salida' }));
    await waitFor(() => expect(screen.getByText('Despacho incompleto')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar — seguir escaneando' }));

    expect(screen.queryByText('Despacho incompleto')).not.toBeInTheDocument();
    expect(screen.getByText('Procesando Despacho')).toBeInTheDocument();
    expect(mockPost).toHaveBeenCalledTimes(1);
  });

  it('dado el modal de despacho incompleto abierto cuando despacha de todas formas entonces reenvia con confirmar_incompleto true', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { items_incompletos: { 'Hilo Poliéster': { requerido: 50, escaneado: 25.5, faltante: 24.5 } } },
      },
    });
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Salida' }));
    await waitFor(() => expect(screen.getByText('Despacho incompleto')).toBeInTheDocument());

    mockPost.mockResolvedValueOnce({ data: {} });
    await userEvent.click(screen.getByRole('button', { name: 'Despachar de todas formas' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenLastCalledWith('/inventory/process-despacho/', {
        pedidos: [1],
        lotes: [],
        confirmar_incompleto: true,
      }),
    );
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Despacho procesado exitosamente'));
    expect(screen.queryByText('Despacho incompleto')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Panel de Despacho')).toBeInTheDocument());
  });

  it('dado un error del servidor distinto de 409 cuando confirma la salida entonces muestra un toast de error y permanece en modo despacho', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockRejectedValueOnce({ response: { status: 500, data: {} } });

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Salida' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al procesar el despacho'));
    expect(screen.getByText('Procesando Despacho')).toBeInTheDocument();
    expect(screen.queryByText('Despacho incompleto')).not.toBeInTheDocument();
  });

  it('dado el modo despacho cuando hace clic en cancelar entonces vuelve a la seleccion de pedidos', async () => {
    await enterDespachoMode([PEDIDO_1]);

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(screen.getByText('Panel de Despacho')).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado mas de 20 pedidos pendientes cuando carga entonces pagina los resultados', async () => {
    const pedidos = Array.from({ length: 25 }, (_, i) => ({
      ...PEDIDO_1,
      id: i + 1,
      guia_remision: `G-${String(i + 1).padStart(3, '0')}`,
    }));
    mockPedidosResponse(pedidos);
    renderComponent();

    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.queryByText('#G-021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('#G-021')).toBeInTheDocument();
    expect(screen.queryByText('#G-001')).not.toBeInTheDocument();
  });

  it('dado sin pedidos seleccionados cuando hace clic en ver historial entonces navega a la pantalla de historial', async () => {
    mockPedidosResponse([PEDIDO_1]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('Cliente A')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /Ver Historial/ }));

    expect(mockNavigate).toHaveBeenCalledWith('/despacho/historial');
  });

  it('dado un lote escaneado de un producto no requerido cuando actualiza la carga entonces lo agrega igualmente al listado', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({
      data: { valid: true, lote: { codigo: 'LOTE-9001', producto_id: 99, producto_nombre: 'Producto Extra', peso: '10.00' } },
    });

    await scanLote('LOTE-9001');

    await waitFor(() => expect(screen.getByText('10.00 / 0.00 kg')).toBeInTheDocument());
    expect(screen.getAllByText('Producto Extra')).toHaveLength(2);
  });

  it('dado un pedido seleccionado cuando hace clic en el checkbox de nuevo entonces lo deselecciona', async () => {
    mockPedidosResponse([PEDIDO_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());
    const checkbox = screen.getAllByRole('checkbox')[0];
    await userEvent.click(checkbox);
    expect(screen.getByText('1 Pedido')).toBeInTheDocument();

    await userEvent.click(checkbox);

    expect(screen.queryByText('1 Pedido')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Iniciar Despacho/ })).not.toBeInTheDocument();
  });

  it('dado un pedido cuando hace clic en la fila fuera del checkbox entonces tambien lo selecciona', async () => {
    mockPedidosResponse([PEDIDO_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Cliente A')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Cliente A'));

    expect(screen.getByText('1 Pedido')).toBeInTheDocument();
    expect(screen.getAllByRole('checkbox')[0]).toBeChecked();
  });

  it('dado un codigo de barras vacio cuando envia el formulario entonces no valida nada', async () => {
    await enterDespachoMode([PEDIDO_1]);

    await scanLote('   ');

    expect(mockPost).not.toHaveBeenCalled();
    expect(screen.getByText('Esperando escaneo...')).toBeInTheDocument();
  });

  it('dado un error al descargar el pdf cuando finaliza el despacho entonces muestra un toast de error por pedido', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({
      data: { valid: true, lote: { codigo: 'LOTE-1001', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '50.00' } },
    });
    await scanLote('LOTE-1001');
    await waitFor(() => expect(screen.getByText('LOTE-1001')).toBeInTheDocument());

    mockGet.mockImplementation((url: string) => {
      if (url.includes('/download_pdf/')) return Promise.reject(new Error('fail'));
      return Promise.resolve({ data: [PEDIDO_1] });
    });
    mockPost.mockResolvedValueOnce({ data: {} });

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Salida' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al imprimir pedido #1'));
  });

  it('dado un texto de busqueda cuando lo borra entonces vuelve a mostrar todos los pedidos', async () => {
    mockPedidosResponse([PEDIDO_1, PEDIDO_3]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Cliente A')).toBeInTheDocument());

    const search = screen.getByPlaceholderText('Buscar por cliente, guía...');
    await userEvent.type(search, 'Cliente B');
    await waitFor(() => expect(screen.queryByText('Cliente A')).not.toBeInTheDocument());

    await userEvent.clear(search);

    await waitFor(() => expect(screen.getByText('Cliente A')).toBeInTheDocument());
    expect(screen.getByText('Cliente B')).toBeInTheDocument();
  });

  it('dado la pagina 2 cuando hace clic en anterior entonces vuelve a la pagina 1', async () => {
    const pedidos = Array.from({ length: 25 }, (_, i) => ({
      ...PEDIDO_1,
      id: i + 1,
      guia_remision: `G-${String(i + 1).padStart(3, '0')}`,
    }));
    mockPedidosResponse(pedidos);
    renderComponent();
    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Anterior/ }));

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('#G-001')).toBeInTheDocument();
  });

  it('dado el campo ir a pagina cuando escribe un numero valido y presiona enter entonces navega a esa pagina', async () => {
    const pedidos = Array.from({ length: 25 }, (_, i) => ({
      ...PEDIDO_1,
      id: i + 1,
      guia_remision: `G-${String(i + 1).padStart(3, '0')}`,
    }));
    mockPedidosResponse(pedidos);
    renderComponent();
    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());

    const pageInput = screen.getByRole('spinbutton');
    await userEvent.clear(pageInput);
    await userEvent.type(pageInput, '2{enter}');

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('#G-021')).toBeInTheDocument();
  });

  it('dado el campo ir a pagina cuando escribe un numero valido y pierde el foco entonces navega a esa pagina', async () => {
    const pedidos = Array.from({ length: 25 }, (_, i) => ({
      ...PEDIDO_1,
      id: i + 1,
      guia_remision: `G-${String(i + 1).padStart(3, '0')}`,
    }));
    mockPedidosResponse(pedidos);
    renderComponent();
    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());

    const pageInput = screen.getByRole('spinbutton');
    await userEvent.clear(pageInput);
    await userEvent.type(pageInput, '2');
    await userEvent.tab();

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado una respuesta paginada con results cuando carga entonces extrae el arreglo de pedidos', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/pedidos-venta/?estado=pendiente')) {
        return Promise.resolve({ data: { results: [PEDIDO_1] } });
      }
      return Promise.resolve({ data: [] });
    });
    renderComponent();
    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());
  });

  it('dado un detalle sin producto_descripcion cuando calcula requerimientos entonces usa el nombre de fallback Producto <id>', async () => {
    const pedidoSinDescripcion = {
      ...PEDIDO_1,
      detalles: [{ id: 1, pedido_venta: 1, producto: 77, lote: null, cantidad: 1, piezas: 1, peso: 50, precio_unitario: 1 }],
    };
    await enterDespachoMode([pedidoSinDescripcion]);

    expect(screen.getByText('0.00 / 50.00 kg')).toBeInTheDocument();
    expect(screen.getByText('Producto 77')).toBeInTheDocument();
  });

  it('dado un pedido sin detalles cuando entra en modo despacho entonces no hay requerimientos calculados', async () => {
    const pedidoSinDetalles = { ...PEDIDO_1, detalles: undefined };
    await enterDespachoMode([pedidoSinDetalles]);

    expect(screen.getByText('No hay requerimientos calculados.')).toBeInTheDocument();
  });

  it('dado un pedido sin detalles cuando renderiza la fila entonces muestra 0 productos y 0.00 kg', async () => {
    const pedidoSinDetalles = { ...PEDIDO_1, detalles: undefined };
    mockPedidosResponse([pedidoSinDetalles]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());
    expect(screen.getByText('0 prod.')).toBeInTheDocument();
    expect(screen.getByText('0.00 kg')).toBeInTheDocument();
  });

  it('dado un pedido sin guia_remision cuando renderiza la fila entonces usa el id como fallback', async () => {
    const pedidoSinGuia = { ...PEDIDO_1, guia_remision: null };
    mockPedidosResponse([pedidoSinGuia]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument());
  });

  it('dado un pedido con estado despachado_parcial cuando renderiza la fila entonces muestra el badge Parcial', async () => {
    const pedidoParcial = { ...PEDIDO_1, estado: 'despachado_parcial' };
    mockPedidosResponse([pedidoParcial]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('Parcial')).toBeInTheDocument());
  });

  it('dado un id seleccionado que ya no existe en la lista de pedidos cuando recalcula requerimientos entonces lo ignora sin romper', async () => {
    mockPedidosResponse([PEDIDO_1, PEDIDO_2]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('#G-001')).toBeInTheDocument());

    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[0]);
    await userEvent.click(checkboxes[1]);

    const search = screen.getByPlaceholderText('Buscar por cliente, guía...');
    await userEvent.type(search, 'G-002');
    await waitFor(() => expect(screen.queryByText('#G-001')).not.toBeInTheDocument());

    expect(screen.getByText('2 Pedidos')).toBeInTheDocument();
  });

  it('dado un despacho exitoso con despacho_id cuando imprime documentos entonces incluye el historial_id en la query', async () => {
    await enterDespachoMode([PEDIDO_1]);
    mockPost.mockResolvedValueOnce({
      data: { valid: true, lote: { codigo: 'LOTE-1001', producto_id: 10, producto_nombre: 'Hilo Poliéster', peso: '50.00' } },
    });
    await scanLote('LOTE-1001');
    await waitFor(() => expect(screen.getByText('LOTE-1001')).toBeInTheDocument());

    mockPost.mockResolvedValueOnce({ data: { despacho_id: 999 } });
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Salida' }));

    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith('/pedidos-venta/1/download_pdf/?historial_id=999', { responseType: 'blob' }),
    );
  });
});
