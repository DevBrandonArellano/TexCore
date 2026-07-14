import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BodegueroDashboard } from './BodegueroDashboard';
import type { Producto, Bodega, LoteProduccion } from '../../lib/types';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
  },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: vi.fn(),
  },
}));

const mockUseAuth = vi.fn();
vi.mock('../../lib/auth', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../admin-sistemas/InventoryDashboard', () => ({
  InventoryDashboard: (props: any) => (
    <div data-testid="inventory-dashboard">
      <span data-testid="inv-productos">{props.productos.length}</span>
      <span data-testid="inv-bodegas">{props.bodegas.length}</span>
      <span data-testid="inv-sede">{props.sedeId}</span>
      <button onClick={props.onDataRefresh}>refrescar-inventario</button>
    </div>
  ),
}));

vi.mock('../shared/MRPDashboard', () => ({
  MRPDashboard: () => <div data-testid="mrp-dashboard">MRP Mock</div>,
}));

const PRODUCTO_1: Producto = {
  id: 1,
  codigo: 'HP-001',
  descripcion: 'Hilo Poliéster Blanco',
  tipo: 'hilo',
  unidad_medida: 'kg',
  stock_minimo: 10,
  precio_base: 5000,
};

const PRODUCTO_2: Producto = {
  id: 2,
  codigo: 'TL-002',
  descripcion: 'Tela Denim',
  tipo: 'tela',
  unidad_medida: 'metros',
  stock_minimo: 20,
  precio_base: 8000,
};

const BODEGA_1: Bodega = { id: 1, nombre: 'Bodega Central', sede: 3 };
const BODEGA_2: Bodega = { id: 2, nombre: 'Bodega Norte', sede: 3 };
const BODEGA_3: Bodega = { id: 3, nombre: 'Bodega Sur', sede: 3 };

const LOTE_1: LoteProduccion = {
  id: 1,
  orden_produccion: 1,
  codigo_lote: 'L-001',
  peso_neto_producido: 100,
  operario: 1,
  maquina: null,
  turno: 'mañana',
  hora_inicio: '2026-07-10T08:00:00',
  hora_final: '2026-07-10T12:00:00',
};

const ALERTA_1 = {
  producto: 'Hilo Poliéster Blanco',
  producto_codigo: 'HP-001',
  bodega: 'Bodega Central',
  stock_actual: '5',
  stock_minimo: '10',
};

function mockEndpoints(overrides: Record<string, any> = {}) {
  const defaults: Record<string, any> = {
    '/productos/': [],
    '/bodegas/': [],
    '/lotes-produccion/': [],
    '/proveedores/': [],
    '/inventory/alertas-stock/': [],
  };
  const data = { ...defaults, ...overrides };
  mockGet.mockImplementation((url: string) => {
    if (url in data) return Promise.resolve({ data: data[url] });
    return Promise.resolve({ data: [] });
  });
}

describe('BodegueroDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      profile: { user: { first_name: 'Juan', username: 'jperez', sede: 3 } },
    });
    mockEndpoints();
  });

  it('dado que las peticiones aun no resuelven cuando monta entonces muestra los placeholders de carga en las tarjetas', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<BodegueroDashboard />);

    expect(screen.getByText('Panel de Bodeguero')).toBeInTheDocument();
    expect(screen.getAllByText('...')).toHaveLength(3);
  });

  it('dado sin productos, bodegas ni lotes cuando carga entonces las tarjetas muestran cero', async () => {
    mockEndpoints();
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.queryAllByText('...')).toHaveLength(0));

    expect(screen.getByText('productos registrados').previousSibling).toHaveTextContent('0');
    expect(screen.getByText('bodegas en el sistema').previousSibling).toHaveTextContent('0');
    expect(screen.getByText('lotes de producción').previousSibling).toHaveTextContent('0');
  });

  it('dado productos, bodegas y lotes existentes cuando carga entonces las tarjetas reflejan las cantidades correctas', async () => {
    mockEndpoints({
      '/productos/': [PRODUCTO_1, PRODUCTO_2],
      '/bodegas/': [BODEGA_1, BODEGA_2, BODEGA_3],
      '/lotes-produccion/': [LOTE_1],
    });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByText('productos registrados').previousSibling).toHaveTextContent('2'));
    expect(screen.getByText('bodegas en el sistema').previousSibling).toHaveTextContent('3');
    expect(screen.getByText('lotes de producción').previousSibling).toHaveTextContent('1');

    expect(screen.getByTestId('inv-productos')).toHaveTextContent('2');
    expect(screen.getByTestId('inv-bodegas')).toHaveTextContent('3');
    expect(screen.getByTestId('inv-sede')).toHaveTextContent('3');
  });

  it('dado un perfil con nombre cuando carga entonces saluda usando el nombre', async () => {
    mockUseAuth.mockReturnValue({ profile: { user: { first_name: 'Maria', username: 'mgomez' } } });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByText(/Bienvenido, Maria\./)).toBeInTheDocument());
  });

  it('dado un perfil sin nombre cuando carga entonces saluda usando el username', async () => {
    mockUseAuth.mockReturnValue({ profile: { user: { first_name: '', username: 'mgomez' } } });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByText(/Bienvenido, mgomez\./)).toBeInTheDocument());
  });

  it('dado datos ya cargados cuando el usuario hace clic en Actualizar Datos entonces vuelve a solicitar la informacion', async () => {
    mockEndpoints({ '/productos/': [PRODUCTO_1] });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByText('productos registrados').previousSibling).toHaveTextContent('1'));
    const llamadasIniciales = mockGet.mock.calls.length;

    await userEvent.click(screen.getByRole('button', { name: /Actualizar Datos/ }));

    await waitFor(() => expect(mockGet.mock.calls.length).toBeGreaterThan(llamadasIniciales));
  });

  it('dado que fallan las peticiones de productos o bodegas cuando carga entonces muestra un toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/productos/') return Promise.reject(new Error('network error'));
      return Promise.resolve({ data: [] });
    });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar los datos'));
  });

  it('dado que fallan las peticiones opcionales de lotes y proveedores cuando carga entonces igual muestra productos y bodegas', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/productos/') return Promise.resolve({ data: [PRODUCTO_1] });
      if (url === '/bodegas/') return Promise.resolve({ data: [BODEGA_1] });
      if (url === '/lotes-produccion/') return Promise.reject(new Error('no lotes'));
      if (url === '/proveedores/') return Promise.reject(new Error('no proveedores'));
      return Promise.resolve({ data: [] });
    });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByText('productos registrados').previousSibling).toHaveTextContent('1'));
    expect(screen.getByText('bodegas en el sistema').previousSibling).toHaveTextContent('1');
    expect(screen.getByText('lotes de producción').previousSibling).toHaveTextContent('0');
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it('dado que las respuestas de productos, bodegas, lotes y proveedores vienen paginadas cuando carga entonces usa el campo results', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/productos/') return Promise.resolve({ data: { results: [PRODUCTO_1] } });
      if (url === '/bodegas/') return Promise.resolve({ data: { results: [BODEGA_1, BODEGA_2] } });
      if (url === '/lotes-produccion/') return Promise.resolve({ data: { results: [LOTE_1] } });
      if (url === '/proveedores/') return Promise.resolve({ data: { results: [] } });
      return Promise.resolve({ data: [] });
    });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByText('productos registrados').previousSibling).toHaveTextContent('1'));
    expect(screen.getByText('bodegas en el sistema').previousSibling).toHaveTextContent('2');
    expect(screen.getByText('lotes de producción').previousSibling).toHaveTextContent('1');
  });

  it('dado el dashboard cargado cuando el usuario cambia a la pestaña de inventario entonces se renderiza con los datos actuales', async () => {
    mockEndpoints({ '/productos/': [PRODUCTO_1], '/bodegas/': [BODEGA_1] });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    expect(screen.getByTestId('inv-productos')).toHaveTextContent('1');
  });

  it('dado el dashboard cargado cuando el usuario hace clic en la pestaña MRP entonces oculta el inventario y muestra el MRP', async () => {
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('tab', { name: /MRP/ }));

    expect(screen.getByTestId('mrp-dashboard')).toBeInTheDocument();
    expect(screen.queryByTestId('inventory-dashboard')).not.toBeInTheDocument();
  });

  describe('pestaña de alertas de stock', () => {
    it('dado que las alertas aun no resuelven cuando el usuario abre la pestaña entonces muestra el estado de carga', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url === '/inventory/alertas-stock/') return new Promise(() => {});
        return Promise.resolve({ data: [] });
      });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      expect(document.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
    });

    it('dado sin alertas de stock cuando carga entonces muestra el mensaje de que no hay alertas', async () => {
      mockEndpoints();
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() =>
        expect(screen.getByText('No hay alertas de stock bajo en este momento.')).toBeInTheDocument(),
      );
    });

    it('dado alertas de stock existentes cuando carga entonces muestra la tabla con los datos reales', async () => {
      mockEndpoints({ '/inventory/alertas-stock/': [ALERTA_1] });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());
      const row = screen.getByText('HP-001').closest('tr') as HTMLElement;
      expect(within(row).getByText('Hilo Poliéster Blanco')).toBeInTheDocument();
      expect(within(row).getByText('Bodega Central')).toBeInTheDocument();
      expect(within(row).getByText('5')).toBeInTheDocument();
      expect(within(row).getByText('10')).toBeInTheDocument();
      expect(within(row).getByText('Stock Bajo')).toBeInTheDocument();
    });

    it('dado mas de 20 alertas de stock cuando carga entonces pagina los resultados', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());
      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
      expect(screen.queryByText('HP-021')).not.toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));

      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
      expect(screen.getByText('HP-021')).toBeInTheDocument();
      expect(screen.queryByText('HP-001')).not.toBeInTheDocument();
    });

    it('dado que las alertas vienen paginadas con resultados cuando carga entonces usa el campo results', async () => {
      mockEndpoints({ '/inventory/alertas-stock/': { results: [ALERTA_1] } });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());
    });

    it('dado la primera pagina de alertas cuando carga entonces el boton Anterior esta deshabilitado y Siguiente habilitado', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());
      expect(screen.getByRole('button', { name: /Anterior/ })).toBeDisabled();
      expect(screen.getByRole('button', { name: /Siguiente/ })).toBeEnabled();
    });

    it('dado la segunda pagina de alertas cuando el usuario hace clic en Anterior entonces vuelve a la primera pagina', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));
      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));
      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Siguiente/ })).toBeDisabled();

      await userEvent.click(screen.getByRole('button', { name: /Anterior/ }));

      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
      expect(screen.getByText('HP-001')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina cuando el usuario escribe una pagina valida y presiona Enter entonces navega a esa pagina', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));
      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());

      const input = screen.getByRole('spinbutton');
      await userEvent.clear(input);
      await userEvent.type(input, '2');
      await userEvent.keyboard('{Enter}');

      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
      expect(screen.getByText('HP-021')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina cuando el usuario escribe una pagina fuera de rango y presiona Enter entonces no cambia de pagina', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));
      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());

      const input = screen.getByRole('spinbutton');
      await userEvent.clear(input);
      await userEvent.type(input, '99');
      await userEvent.keyboard('{Enter}');

      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
      expect(screen.getByText('HP-001')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina cuando el usuario presiona una tecla distinta de Enter entonces no cambia de pagina', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));
      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());

      const input = screen.getByRole('spinbutton');
      await userEvent.clear(input);
      await userEvent.type(input, '2');
      await userEvent.keyboard('{ArrowUp}');

      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina cuando el usuario escribe una pagina valida y quita el foco entonces navega a esa pagina', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));
      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());

      const input = screen.getByRole('spinbutton');
      await userEvent.clear(input);
      await userEvent.type(input, '2');
      await userEvent.tab();

      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
      expect(screen.getByText('HP-021')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina cuando el usuario escribe una pagina fuera de rango y quita el foco entonces no cambia de pagina', async () => {
      const alertas = Array.from({ length: 25 }, (_, i) => ({
        ...ALERTA_1,
        producto_codigo: `HP-${String(i + 1).padStart(3, '0')}`,
      }));
      mockEndpoints({ '/inventory/alertas-stock/': alertas });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));
      await waitFor(() => expect(screen.getByText('HP-001')).toBeInTheDocument());

      const input = screen.getByRole('spinbutton');
      await userEvent.clear(input);
      await userEvent.type(input, '0');
      await userEvent.tab();

      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
      expect(screen.getByText('HP-001')).toBeInTheDocument();
    });

    it('dado un error al obtener las alertas cuando falla la peticion entonces muestra un toast de error y el mensaje vacio', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url === '/inventory/alertas-stock/') return Promise.reject(new Error('boom'));
        return Promise.resolve({ data: [] });
      });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar las alertas de stock'));
      expect(screen.getByText('No hay alertas de stock bajo en este momento.')).toBeInTheDocument();
    });
  });
});
