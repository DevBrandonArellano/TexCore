import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BodegueroDashboard } from './BodegueroDashboard';
import type { Producto, Bodega, LoteProduccion, Quimico } from '../../lib/types';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
    delete: (...args: any[]) => mockDelete(...args),
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
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

vi.mock('../admin-sistemas/ManageProductos', () => ({
  ManageProductos: (props: any) => (
    <div data-testid="manage-productos">
      <span data-testid="manage-productos-count">{props.productos.length}</span>
      <button
        type="button"
        onClick={() => props.onProductCreate({
          codigo: 'INS-001',
          descripcion: 'Insumo de empaque',
          tipo: 'insumo',
          unidad_medida: 'unidades',
          stock_minimo: '12',
          precio_base: '2.5',
          presentacion: 'Caja',
          pais_origen: 'Ecuador',
          calidad: 'A',
        })}
      >
        crear-producto
      </button>
      <button
        type="button"
        onClick={() => props.onProductUpdate(1, {
          codigo: 'HP-001-A',
          descripcion: 'Hilo actualizado',
          tipo: 'hilo',
          unidad_medida: 'kg',
          stock_minimo: 15,
          precio_base: 6,
          presentacion: '',
          pais_origen: '',
          calidad: '',
        })}
      >
        actualizar-producto
      </button>
      <button type="button" onClick={() => props.onProductDelete(1)}>eliminar-producto</button>
      <button type="button" onClick={() => props.onProductCreate({})}>crear-producto-vacio</button>
    </div>
  ),
}));

vi.mock('../admin-sistemas/ManageQuimicos', () => ({
  ManageQuimicos: (props: any) => (
    <div data-testid="manage-quimicos">
      <span data-testid="manage-quimicos-count">{props.quimicos.length}</span>
      <button
        type="button"
        onClick={() => props.onChemicalCreate({
          codigo: 'Q-001',
          descripcion: 'Soda cáustica',
          unidad_medida: 'kg',
          precio_base: '3.75',
          presentacion: 'Saco',
        })}
      >
        crear-quimico
      </button>
      <button
        type="button"
        onClick={() => props.onChemicalUpdate(10, {
          codigo: 'Q-001-A',
          descripcion: 'Soda actualizada',
          unidad_medida: 'kg',
          precio_base: 4,
          presentacion: '',
        })}
      >
        actualizar-quimico
      </button>
      <button type="button" onClick={() => props.onChemicalDelete(10)}>eliminar-quimico</button>
      <button type="button" onClick={() => props.onChemicalCreate({})}>crear-quimico-vacio</button>
    </div>
  ),
}));

vi.mock('../shared/MRPDashboard', () => ({
  MRPDashboard: () => <div data-testid="mrp-dashboard">MRP Mock</div>,
}));

const mockHandleExport = vi.fn();
let mockExportLoadingState: Record<string, boolean> = {};
vi.mock('../admin-sistemas/useReportesExport', () => ({
  useReportesExport: () => ({ loading: mockExportLoadingState, handleExport: mockHandleExport }),
}));

// Shim de Radix Select — ver el mismo patrón en ReportesView.test.tsx.
const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}>
      <div>{children}</div>
    </SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return (
      <button type="button" onClick={() => onValueChange(value)}>
        {children}
      </button>
    );
  },
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

const QUIMICO_1: Quimico = {
  id: 10,
  codigo: 'Q-001',
  descripcion: 'Soda cáustica',
  tipo: 'quimico',
  unidad_medida: 'kg',
  precio_base: 3.75,
};

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
    '/chemicals/': [],
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
    mockHandleExport.mockReset();
    mockExportLoadingState = {};
    mockPost.mockResolvedValue({ data: {} });
    mockPatch.mockResolvedValue({ data: {} });
    mockDelete.mockResolvedValue({ data: {} });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
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
      if (url === '/chemicals/') return Promise.resolve({ data: { results: [QUIMICO_1] } });
      return Promise.resolve({ data: [] });
    });
    render(<BodegueroDashboard />);

    await waitFor(() => expect(screen.getByText('productos registrados').previousSibling).toHaveTextContent('1'));
    expect(screen.getByText('bodegas en el sistema').previousSibling).toHaveTextContent('2');
    expect(screen.getByText('lotes de producción').previousSibling).toHaveTextContent('1');
  });

  it('dado el dashboard cargado cuando abre Catálogos entonces muestra productos, insumos y químicos existentes', async () => {
    mockEndpoints({ '/productos/': [PRODUCTO_1, PRODUCTO_2], '/chemicals/': [QUIMICO_1] });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    expect(screen.getByTestId('manage-productos')).toBeInTheDocument();
    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('2');

    await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

    expect(screen.getByTestId('manage-quimicos')).toBeInTheDocument();
    expect(screen.getByTestId('manage-quimicos-count')).toHaveTextContent('1');
  });

  it('dado Catálogos cuando crea un insumo entonces llama a productos con sede y actualiza la lista', async () => {
    mockEndpoints({ '/productos/': [PRODUCTO_1] });
    mockPost.mockResolvedValueOnce({
      data: {
        id: 3,
        codigo: 'INS-001',
        descripcion: 'Insumo de empaque',
        tipo: 'insumo',
        unidad_medida: 'unidades',
        stock_minimo: 12,
        precio_base: 2.5,
        sede: 3,
      },
    });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    await userEvent.click(screen.getByRole('button', { name: 'crear-producto' }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/productos/', {
      codigo: 'INS-001',
      descripcion: 'Insumo de empaque',
      tipo: 'insumo',
      unidad_medida: 'unidades',
      stock_minimo: 12,
      precio_base: 2.5,
      presentacion: 'Caja',
      pais_origen: 'Ecuador',
      calidad: 'A',
      sede: 3,
    }));
    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('2');
    expect(toastSuccessMock).toHaveBeenCalledWith('Producto creado exitosamente');
  });

  it('dado Catálogos cuando actualiza y elimina producto entonces usa los endpoints de productos', async () => {
    mockEndpoints({ '/productos/': [PRODUCTO_1] });
    mockPatch.mockResolvedValueOnce({ data: { ...PRODUCTO_1, codigo: 'HP-001-A', descripcion: 'Hilo actualizado' } });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    await userEvent.click(screen.getByRole('button', { name: 'actualizar-producto' }));
    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/productos/1/', expect.objectContaining({
      codigo: 'HP-001-A',
      descripcion: 'Hilo actualizado',
      tipo: 'hilo',
      stock_minimo: 15,
      precio_base: 6,
      presentacion: null,
      pais_origen: null,
      calidad: null,
    })));

    await userEvent.click(screen.getByRole('button', { name: 'eliminar-producto' }));
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/productos/1/'));
    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('0');
  });

  it('dado Catálogos cuando crea, actualiza y elimina químico entonces usa los endpoints de chemicals', async () => {
    mockEndpoints({ '/chemicals/': [QUIMICO_1] });
    mockPost.mockResolvedValueOnce({ data: { ...QUIMICO_1, id: 11 } });
    mockPatch.mockResolvedValueOnce({ data: { ...QUIMICO_1, codigo: 'Q-001-A' } });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));
    await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

    await userEvent.click(screen.getByRole('button', { name: 'crear-quimico' }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/chemicals/', {
      codigo: 'Q-001',
      descripcion: 'Soda cáustica',
      tipo: 'quimico',
      unidad_medida: 'kg',
      stock_minimo: 0,
      precio_base: 3.75,
      presentacion: 'Saco',
      sede: 3,
    }));
    expect(screen.getByTestId('manage-quimicos-count')).toHaveTextContent('2');

    await userEvent.click(screen.getByRole('button', { name: 'actualizar-quimico' }));
    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/chemicals/10/', expect.objectContaining({
      codigo: 'Q-001-A',
      descripcion: 'Soda actualizada',
      tipo: 'quimico',
      precio_base: 4,
      presentacion: null,
    })));

    await userEvent.click(screen.getByRole('button', { name: 'eliminar-quimico' }));
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/chemicals/10/'));
  });

  it('dado creacion de quimico cuando se crea exitosamente entonces se sincroniza e incrementa tambien la lista de productos', async () => {
    mockEndpoints({ '/chemicals/': [QUIMICO_1], '/productos/': [PRODUCTO_1] });
    mockPost.mockResolvedValueOnce({ data: { ...QUIMICO_1, id: 99, codigo: 'Q-99', descripcion: 'Nuevo Quimico' } });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('1');
    await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));
    expect(screen.getByTestId('manage-quimicos-count')).toHaveTextContent('1');

    await userEvent.click(screen.getByRole('button', { name: 'crear-quimico' }));
    await waitFor(() => expect(screen.getByTestId('manage-quimicos-count')).toHaveTextContent('2'));

    await userEvent.click(screen.getByRole('tab', { name: /Productos e Insumos/ }));
    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('2');
  });

  it('dado creacion de producto tipo insumo cuando se crea exitosamente entonces se sincroniza con la lista de quimicos', async () => {
    mockEndpoints({ '/chemicals/': [QUIMICO_1], '/productos/': [PRODUCTO_1] });
    mockPost.mockResolvedValueOnce({
      data: {
        id: 101,
        codigo: 'INS-001',
        descripcion: 'Insumo de empaque',
        tipo: 'insumo',
        unidad_medida: 'unidades',
        stock_minimo: 12,
        precio_base: 2.5,
      },
    });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('1');

    await userEvent.click(screen.getByRole('button', { name: 'crear-producto' }));
    await waitFor(() => expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('2'));

    await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));
    expect(screen.getByTestId('manage-quimicos-count')).toHaveTextContent('2');
  });

  it('dado eliminacion de quimico cuando se confirma entonces se remueve de quimicos y productos', async () => {
    mockEndpoints({
      '/chemicals/': [QUIMICO_1],
      '/productos/': [PRODUCTO_1, { ...QUIMICO_1, stock_minimo: 0 }],
    });
    mockDelete.mockResolvedValueOnce({});
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('2');

    await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));
    expect(screen.getByTestId('manage-quimicos-count')).toHaveTextContent('1');
    await userEvent.click(screen.getByRole('button', { name: 'eliminar-quimico' }));

    await waitFor(() => expect(screen.getByTestId('manage-quimicos-count')).toHaveTextContent('0'));

    await userEvent.click(screen.getByRole('tab', { name: /Productos e Insumos/ }));
    expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('1');
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

    it('dado bodegas asignadas cuando abre la pestaña de alertas entonces muestra el selector para exportar', async () => {
      mockEndpoints({ '/bodegas/': [BODEGA_1, BODEGA_2], '/inventory/alertas-stock/': [ALERTA_1] });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() => expect(screen.getByRole('button', { name: 'Bodega Central' })).toBeInTheDocument());
      expect(screen.getByRole('button', { name: 'Bodega Norte' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Exportar Excel/ })).toBeInTheDocument();
    });

    it('dado ninguna bodega seleccionada cuando abre la pestaña de alertas entonces el boton Exportar Excel esta deshabilitado', async () => {
      mockEndpoints({ '/bodegas/': [BODEGA_1], '/inventory/alertas-stock/': [ALERTA_1] });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      await waitFor(() => expect(screen.getByRole('button', { name: /Exportar Excel/ })).toBeDisabled());
    });

    it('dado una bodega seleccionada cuando hace clic en Exportar Excel entonces exporta el reporte stock-bajo', async () => {
      mockEndpoints({ '/bodegas/': [BODEGA_1], '/inventory/alertas-stock/': [ALERTA_1] });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));
      await waitFor(() => expect(screen.getByRole('button', { name: 'Bodega Central' })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: 'Bodega Central' }));
      const exportButton = screen.getByRole('button', { name: /Exportar Excel/ });
      await waitFor(() => expect(exportButton).toBeEnabled());
      await userEvent.click(exportButton);

      expect(mockHandleExport).toHaveBeenCalledWith('stock-bajo');
    });

    it('dado una exportacion en curso cuando abre la pestaña de alertas entonces el boton muestra Generando', async () => {
      mockExportLoadingState = { 'stock-bajo': true };
      mockEndpoints({ '/bodegas/': [BODEGA_1], '/inventory/alertas-stock/': [ALERTA_1] });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      expect(await screen.findByText('Generando...')).toBeInTheDocument();
    });

    it('dado una respuesta de alertas sin arreglo ni campo results cuando carga entonces no muestra alertas', async () => {
      mockEndpoints({ '/inventory/alertas-stock/': {} });
      render(<BodegueroDashboard />);
      await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: /Alertas/ }));

      expect(await screen.findByText('No hay alertas de stock bajo en este momento.')).toBeInTheDocument();
    });
  });

  it('dado crear un producto sin campos opcionales cuando se envia entonces usa los valores por defecto', async () => {
    mockEndpoints({ '/productos/': [PRODUCTO_1] });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    await userEvent.click(screen.getByRole('button', { name: 'crear-producto-vacio' }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/productos/', {
      codigo: '',
      descripcion: '',
      tipo: 'hilo',
      unidad_medida: 'kg',
      stock_minimo: 0,
      precio_base: 0,
      presentacion: null,
      pais_origen: null,
      calidad: null,
      sede: 3,
    }));
  });

  it('dado crear un quimico sin campos opcionales cuando se envia entonces usa los valores por defecto', async () => {
    mockEndpoints({ '/chemicals/': [QUIMICO_1] });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));
    await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

    await userEvent.click(screen.getByRole('button', { name: 'crear-quimico-vacio' }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/chemicals/', {
      codigo: '',
      descripcion: '',
      tipo: 'quimico',
      unidad_medida: 'kg',
      stock_minimo: 0,
      precio_base: 0,
      presentacion: null,
      sede: 3,
    }));
  });

  it('dado varios productos cuando actualiza uno entonces conserva los demas sin modificar', async () => {
    mockEndpoints({ '/productos/': [PRODUCTO_1, PRODUCTO_2] });
    mockPatch.mockResolvedValueOnce({ data: { ...PRODUCTO_1, codigo: 'HP-001-A' } });
    render(<BodegueroDashboard />);
    await waitFor(() => expect(screen.getByTestId('inventory-dashboard')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('tab', { name: /Catálogos/ }));

    await userEvent.click(screen.getByRole('button', { name: 'actualizar-producto' }));

    await waitFor(() => expect(screen.getByTestId('manage-productos-count')).toHaveTextContent('2'));
  });
});
