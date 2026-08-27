import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { format } from 'date-fns';
import { MRPDashboard } from './MRPDashboard';
import type { RequerimientoMaterial, OrdenCompraSugerida } from '../../lib/types';

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
const toastInfoMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
    info: (...args: any[]) => toastInfoMock(...args),
  },
}));

const SUGERENCIA_1: OrdenCompraSugerida = {
  id: 1,
  producto: 10,
  producto_nombre: 'Hilo Poliéster Blanco',
  producto_codigo: 'HP-001',
  sede: 1,
  sede_nombre: 'Sede Norte',
  cantidad_sugerida: 1500,
  estado: 'PENDIENTE',
  fecha_generacion: '2026-07-10T14:30:00',
};

const REQUERIMIENTO_1: RequerimientoMaterial = {
  id: 1,
  producto_requerido: 10,
  producto_nombre: 'Hilo Poliéster Blanco',
  producto_codigo: 'HP-001',
  cantidad_necesaria: 800,
  sede: 1,
  sede_nombre: 'Sede Norte',
  origen_tipo: 'PEDIDO',
  origen_id: 55,
  fecha_requerida: '2026-07-15',
  fecha_calculo: '2026-07-10T10:00:00',
};

function mockFetch(sugerencias: OrdenCompraSugerida[] = [], requerimientos: RequerimientoMaterial[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url === '/inventory/sugerencias-compra/') return Promise.resolve({ data: sugerencias });
    if (url === '/inventory/requerimientos-material/') return Promise.resolve({ data: requerimientos });
    return Promise.resolve({ data: [] });
  });
}

describe('MRPDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    toastInfoMock.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('dado datos aun no resueltos cuando monta entonces muestra el estado de carga', async () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<MRPDashboard />);

    expect(screen.getByText('Cargando planificación...')).toBeInTheDocument();
  });

  it('dado sin sugerencias ni requerimientos cuando carga entonces muestra los mensajes vacios', async () => {
    mockFetch([], []);
    render(<MRPDashboard />);

    await waitFor(() => expect(screen.getByText('No hay sugerencias de compra pendientes.')).toBeInTheDocument());

    const tables = screen.getAllByRole('table');
    expect(tables).toHaveLength(1);
    const requerimientosTable = tables[0];
    expect(within(requerimientosTable).queryAllByRole('row')).toHaveLength(1);
  });

  it('dado sugerencias y requerimientos existentes cuando carga entonces muestra sus datos reales', async () => {
    mockFetch([SUGERENCIA_1], [REQUERIMIENTO_1]);
    render(<MRPDashboard />);

    await waitFor(() => expect(screen.getAllByText('Hilo Poliéster Blanco')).toHaveLength(2));

    expect(screen.getAllByText('HP-001')).toHaveLength(2);
    expect(screen.getAllByText('Sede Norte')).toHaveLength(2);
    expect(screen.getByText(Number(SUGERENCIA_1.cantidad_sugerida).toLocaleString())).toBeInTheDocument();
    expect(screen.getByText(Number(REQUERIMIENTO_1.cantidad_necesaria).toLocaleString())).toBeInTheDocument();
    expect(screen.getByText('PENDIENTE')).toBeInTheDocument();
    expect(screen.getByText('PEDIDO #55')).toBeInTheDocument();
    expect(screen.getByText(format(new Date(SUGERENCIA_1.fecha_generacion), 'dd/MM/yyyy HH:mm'))).toBeInTheDocument();
    expect(screen.getByText(format(new Date(REQUERIMIENTO_1.fecha_requerida!), 'dd/MM/yyyy'))).toBeInTheDocument();
  });

  it('dado un requerimiento sin fecha requerida cuando carga entonces muestra un guion', async () => {
    mockFetch([], [{ ...REQUERIMIENTO_1, fecha_requerida: undefined }]);
    render(<MRPDashboard />);

    await waitFor(() => expect(screen.getByText('Hilo Poliéster Blanco')).toBeInTheDocument());
    expect(screen.getByText('-')).toBeInTheDocument();
  });

  it('dado mas de 20 sugerencias cuando carga entonces pagina los resultados', async () => {
    const sugerencias = Array.from({ length: 25 }, (_, i) => ({
      ...SUGERENCIA_1,
      id: i + 1,
      producto_nombre: `Producto ${i + 1}`,
    }));
    mockFetch(sugerencias, []);
    render(<MRPDashboard />);

    await waitFor(() => expect(screen.getByText('Producto 1')).toBeInTheDocument());
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.queryByText('Producto 21')).not.toBeInTheDocument();

    const siguienteButtons = screen.getAllByRole('button', { name: /Siguiente/ });
    await userEvent.click(siguienteButtons[0]);

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Producto 21')).toBeInTheDocument();
    expect(screen.queryByText('Producto 1')).not.toBeInTheDocument();
  });

  it('dado mas de 20 requerimientos cuando carga entonces pagina los resultados', async () => {
    const requerimientos = Array.from({ length: 25 }, (_, i) => ({
      ...REQUERIMIENTO_1,
      id: i + 1,
      producto_nombre: `Requerido ${i + 1}`,
    }));
    mockFetch([], requerimientos);
    render(<MRPDashboard />);

    await waitFor(() => expect(screen.getByText('Requerido 1')).toBeInTheDocument());
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.queryByText('Requerido 21')).not.toBeInTheDocument();

    const siguienteButtons = screen.getAllByRole('button', { name: /Siguiente/ });
    await userEvent.click(siguienteButtons[0]);

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Requerido 21')).toBeInTheDocument();
    expect(screen.queryByText('Requerido 1')).not.toBeInTheDocument();
  });

  it('dado mas de 20 sugerencias cuando escribe una pagina valida en Ir a y presiona Enter entonces navega', async () => {
    const sugerencias = Array.from({ length: 25 }, (_, i) => ({ ...SUGERENCIA_1, id: i + 1, producto_nombre: `Producto ${i + 1}` }));
    mockFetch(sugerencias, []);
    render(<MRPDashboard />);
    await waitFor(() => expect(screen.getByText('Producto 1')).toBeInTheDocument());

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Producto 21')).toBeInTheDocument();
  });

  it('dado mas de 20 sugerencias cuando el input Ir a pierde el foco con un numero valido entonces navega', async () => {
    const sugerencias = Array.from({ length: 25 }, (_, i) => ({ ...SUGERENCIA_1, id: i + 1, producto_nombre: `Producto ${i + 1}` }));
    mockFetch(sugerencias, []);
    render(<MRPDashboard />);
    await waitFor(() => expect(screen.getByText('Producto 1')).toBeInTheDocument());

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2');
    await userEvent.tab();

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
  });

  it('dado mas de 20 sugerencias cuando escribe un numero fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const sugerencias = Array.from({ length: 25 }, (_, i) => ({ ...SUGERENCIA_1, id: i + 1, producto_nombre: `Producto ${i + 1}` }));
    mockFetch(sugerencias, []);
    render(<MRPDashboard />);
    await waitFor(() => expect(screen.getByText('Producto 1')).toBeInTheDocument());

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado mas de 20 requerimientos cuando escribe una pagina valida en Ir a y presiona Enter entonces navega', async () => {
    const requerimientos = Array.from({ length: 25 }, (_, i) => ({ ...REQUERIMIENTO_1, id: i + 1, producto_nombre: `Requerido ${i + 1}` }));
    mockFetch([], requerimientos);
    render(<MRPDashboard />);
    await waitFor(() => expect(screen.getByText('Requerido 1')).toBeInTheDocument());

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Requerido 21')).toBeInTheDocument();
  });

  it('dado error al obtener datos cuando falla la peticion entonces muestra un toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    render(<MRPDashboard />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar datos del MRP'));
    expect(screen.getByText('No hay sugerencias de compra pendientes.')).toBeInTheDocument();
  });

  it('dado clic en ejecutar motor mrp cuando responde con exito inmediato entonces refresca los datos', async () => {
    mockFetch([], []);
    mockPost.mockResolvedValueOnce({ status: 200, data: {} });
    render(<MRPDashboard />);

    await waitFor(() => expect(screen.getByText('No hay sugerencias de compra pendientes.')).toBeInTheDocument());
    expect(mockGet).toHaveBeenCalledTimes(2);

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar Motor MRP/ }));

    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Motor MRP ejecutado con éxito'));
    expect(mockPost).toHaveBeenCalledWith('/inventory/sugerencias-compra/ejecutar-mrp/');
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(4));
  });

  it('dado clic en ejecutar motor mrp cuando se procesa en segundo plano entonces avisa y refresca tras un tiempo', async () => {
    vi.useFakeTimers();
    mockFetch([], []);
    mockPost.mockResolvedValueOnce({ status: 202, data: {} });
    render(<MRPDashboard />);

    await vi.waitFor(() => expect(screen.getByText('No hay sugerencias de compra pendientes.')).toBeInTheDocument());
    expect(mockGet).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getByRole('button', { name: /Ejecutar Motor MRP/ }));

    await vi.waitFor(() =>
      expect(toastInfoMock).toHaveBeenCalledWith(
        'Motor MRP iniciado en segundo plano. Los resultados aparecerán en unos instantes.',
      ),
    );
    expect(mockGet).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(3000);

    expect(mockGet).toHaveBeenCalledTimes(4);
  });

  it('dado clic en ejecutar motor mrp cuando la peticion falla entonces muestra un toast de error', async () => {
    mockFetch([], []);
    mockPost.mockRejectedValueOnce(new Error('boom'));
    render(<MRPDashboard />);

    await waitFor(() => expect(screen.getByText('No hay sugerencias de compra pendientes.')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar Motor MRP/ }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al ejecutar el motor MRP'));
  });
});
