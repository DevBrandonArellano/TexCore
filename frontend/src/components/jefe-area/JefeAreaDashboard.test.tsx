import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JefeAreaDashboard } from './JefeAreaDashboard';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { Maquina, KPIArea, OrdenProduccion, User, Producto, LoteProduccion, Bodega, FormulaColor } from '../../lib/types';

// Mock axios / apiClient — JefeAreaDashboard usa apiClient directamente
// y ManageMaquinas usa useQuery (TanStack Query) sobre apiClient
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
    delete: (...args: any[]) => mockDelete(...args),
    put: (...args: any[]) => mockPut(...args),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  };
  return {
    default: { ...mockAxiosInstance, create: vi.fn(() => mockAxiosInstance) },
  };
});

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

// Mock Auth — el objeto profile debe ser una referencia ESTABLE entre renders:
// JefeAreaDashboard tiene un useEffect con [profile] como dependencia, y el
// useAuth real (basado en useState) sí mantiene la misma referencia mientras
// la sesión no cambia. Si aquí devolviéramos un objeto nuevo en cada llamada,
// el efecto se dispararía en bucle infinito en cada re-render.
const mockProfile = { user: { id: 1, role: 'jefe_area', area: 1 } };
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: mockProfile }),
}));

// ManageMaquinas NO se mockea: el test de regresión existente verifica que su botón
// "+ Nueva Máquina" (renderizado de verdad) no quede duplicado con el de este dashboard.

// Mock de hijos ya testeados en sus propios archivos — foco en la lógica propia de JefeAreaDashboard
vi.mock('../produccion/EtapasProduccion', () => ({
  EtapasProduccion: (props: any) => <div data-testid="etapas-produccion-mock">EtapasProduccion area:{props.areaId}</div>,
}));

vi.mock('../produccion/FlujoProduccion', () => ({
  FlujoProduccion: () => <div data-testid="flujo-produccion-mock">FlujoProduccion</div>,
}));

vi.mock('../produccion/TrazabilidadProducto', () => ({
  TrazabilidadProducto: (props: any) => (
    <div data-testid="trazabilidad-producto-mock">
      TrazabilidadProducto orden:{props.ordenId} allowRegister:{String(props.allowRegister)}
    </div>
  ),
}));

// Polyfills para Radix UI en jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

const makeQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

const renderComponent = () => {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <JefeAreaDashboard />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

const KPI_1: KPIArea = {
  area: 'Tintorería',
  total_produccion_kg: 1234,
  rendimiento_yield: 0.876,
  tiempo_promedio_lote_min: 45,
};

const MAQUINA_1: Maquina = {
  id: 1,
  nombre: 'Máquina A',
  capacidad_maxima: 100,
  eficiencia_ideal: 0.85,
  estado: 'operativa',
  area: 1,
  operarios: [1],
  operarios_nombres: ['operario1'],
};

const MAQUINA_2: Maquina = {
  id: 2,
  nombre: 'Máquina B',
  capacidad_maxima: 50,
  eficiencia_ideal: 0.85,
  estado: 'mantenimiento',
  area: 1,
  operarios: [],
  operarios_nombres: [],
};

const ORDEN_PENDIENTE: OrdenProduccion = {
  id: 10,
  codigo: 'OP-001',
  producto: 1,
  formula_color: 1,
  peso_neto_requerido: 500,
  estado: 'pendiente',
  fecha_creacion: '2026-07-01',
  fecha_modificacion: '2026-07-01',
  sede: 1,
  area: 1,
  producto_nombre: 'Hilo Blanco',
  formula_color_nombre: 'Rojo Carmesí',
  inventario_descontado: false,
} as OrdenProduccion;

const ORDEN_EN_PROCESO: OrdenProduccion = {
  id: 20,
  codigo: 'OP-002',
  producto: 2,
  formula_color: 1,
  peso_neto_requerido: 300,
  estado: 'en_proceso',
  fecha_creacion: '2026-07-02',
  fecha_modificacion: '2026-07-02',
  sede: 1,
  area: 1,
  producto_nombre: 'Tela Denim',
  inventario_descontado: false,
} as OrdenProduccion;

const OPERARIO_1: User = {
  id: 5,
  username: 'operario1',
  first_name: 'Juan',
  last_name: 'Perez',
  email: 'jp@test.com',
  area: 1,
  sede: 1,
  groups: [],
  permissions: [],
  bodegas_asignadas: [],
};

const PRODUCTO_HILO: Producto = {
  id: 1,
  codigo: 'HP-001',
  descripcion: 'Hilo Poliéster',
  tipo: 'hilo',
  unidad_medida: 'kg',
  stock_minimo: 10,
  precio_base: 5000,
};

const LOTE_1: LoteProduccion = {
  id: 1,
  orden_produccion: 20,
  codigo_lote: 'L-001',
  peso_neto_producido: 80,
  operario: 5,
  maquina: 1,
  maquina_nombre: 'Máquina A',
  operario_nombre: 'operario1',
  turno: 'mañana',
  hora_inicio: '2026-07-13T08:00:00',
  hora_final: '2026-07-13T12:00:00',
};

const BODEGA_1: Bodega = { id: 1, nombre: 'Bodega Central', sede: 1 };
const FORMULA_1: FormulaColor = {
  id: 1,
  codigo: 'F-001',
  nombre_color: 'Rojo Carmesí',
  tipo_sustrato: 'algodon',
  version: 1,
  estado: 'aprobada',
};

function mockEndpoints(overrides: Record<string, any> = {}) {
  const defaults: Record<string, any> = {
    '/kpi-area/': KPI_1,
    '/maquinas/': [],
    '/ordenes-produccion/': [],
    '/users/': [],
    '/productos/': [],
    '/lotes-produccion/': [],
    '/bodegas/': [],
    '/formula-colors/': [],
  };
  const data = { ...defaults, ...overrides };
  mockGet.mockImplementation((url: string) => {
    for (const key of Object.keys(data)) {
      if (url.startsWith(key)) return Promise.resolve({ data: data[key] });
    }
    return Promise.resolve({ data: [] });
  });
}

describe('JefeAreaDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEndpoints();
  });

  it('el card de Estado de Máquinas no tiene un botón propio de "Nueva Máquina" duplicado', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Estado de Máquinas y Carga')).toBeInTheDocument();
    });

    const botonesNuevaMaquina = screen.getAllByRole('button', { name: /Nueva Máquina/i });
    expect(botonesNuevaMaquina).toHaveLength(1);
  });

  describe('carga inicial', () => {
    it('dado que las peticiones aun no resuelven cuando monta entonces muestra el estado de carga', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      renderComponent();

      expect(screen.getByText('Cargando panel...')).toBeInTheDocument();
    });

    it('dado que las peticiones resuelven cuando monta entonces oculta el estado de carga y muestra el panel', async () => {
      renderComponent();

      await waitFor(() => expect(screen.queryByText('Cargando panel...')).not.toBeInTheDocument());
      expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument();
    });

    it('dado un error en alguna peticion cuando falla la carga entonces muestra un toast de error y deja de cargar', async () => {
      mockGet.mockRejectedValue(new Error('500'));
      renderComponent();

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar los datos del panel.'));
      expect(screen.queryByText('Cargando panel...')).not.toBeInTheDocument();
    });
  });

  describe('KPIs', () => {
    it('dado kpis cargados cuando monta entonces muestra produccion total, rendimiento y tiempo promedio', async () => {
      mockEndpoints({ '/kpi-area/': KPI_1 });
      renderComponent();

      await waitFor(() => expect(screen.getByText(`${KPI_1.total_produccion_kg.toLocaleString()} kg`)).toBeInTheDocument());
      expect(screen.getByText('87.6%')).toBeInTheDocument();
      expect(screen.getByText('45 min')).toBeInTheDocument();
    });

    it('dado productos con stock bajo cuando carga entonces la tarjeta de Alertas Activas refleja la cantidad', async () => {
      const lowStock = { ...PRODUCTO_HILO, id: 99, codigo: 'HP-099' };
      mockEndpoints({ '/productos/': [PRODUCTO_HILO, lowStock] });
      renderComponent();

      await waitFor(() => {
        const alertasCard = screen.getByText('Alertas Activas').closest('div.flex-shrink-0')?.parentElement;
        expect(within(alertasCard as HTMLElement).getByText('2')).toBeInTheDocument();
      });
    });

    it('dado el input de ir a pagina en alertas cuando se escribe un numero valido y se presiona Enter entonces conserva la pagina', async () => {
      mockEndpoints({ '/productos/': [PRODUCTO_HILO] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Stock Bajo: HP-001')).toBeInTheDocument());
      const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

      await userEvent.clear(irAInput);
      await userEvent.type(irAInput, '1{Enter}');

      expect(screen.getByText('Página 1 de 1')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina en alertas cuando pierde el foco con un numero valido entonces conserva la pagina', async () => {
      mockEndpoints({ '/productos/': [PRODUCTO_HILO] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Stock Bajo: HP-001')).toBeInTheDocument());
      const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

      await userEvent.clear(irAInput);
      await userEvent.type(irAInput, '1');
      await userEvent.tab();

      expect(screen.getByText('Página 1 de 1')).toBeInTheDocument();
    });
  });

  describe('estado de máquinas y carga', () => {
    it('dado maquinas existentes cuando carga entonces muestra su nombre, capacidad y estado', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1, MAQUINA_2] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina A')).toBeInTheDocument());
      expect(screen.getByText('Capacidad: 100 Kg/Turno')).toBeInTheDocument();
      expect(screen.getByText('✓ Operativa')).toBeInTheDocument();
      expect(screen.getByText('Máquina B')).toBeInTheDocument();
      expect(screen.getByText('⚙ Mantenimiento')).toBeInTheDocument();
    });

    it('dado una maquina con operarios asignados cuando carga entonces los lista por nombre', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('👤 operario1')).toBeInTheDocument());
      expect(screen.getByText('Operarios Asignados (1)')).toBeInTheDocument();
    });

    it('dado una maquina sin operarios asignados cuando carga entonces muestra el mensaje de sin operarios', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_2] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Sin operarios asignados')).toBeInTheDocument());
    });

    it('dado sin maquinas registradas cuando carga entonces muestra el mensaje vacio', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByText('No hay máquinas registradas en esta área.')).toBeInTheDocument());
    });

    it('dado lotes producidos hoy para una maquina cuando carga entonces calcula el porcentaje de carga', async () => {
      const today = new Date().toISOString().split('T')[0];
      const loteHoy: LoteProduccion = { ...LOTE_1, maquina: 1, peso_neto_producido: 50, hora_final: `${today}T12:00:00` };
      mockEndpoints({ '/maquinas/': [MAQUINA_1], '/lotes-produccion/': [loteHoy] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('50%')).toBeInTheDocument());
    });

    it('dado clic en el boton de activar/desactivar una maquina cuando la peticion tiene exito entonces cambia el estado y refresca', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1] });
      mockPatch.mockResolvedValueOnce({ data: {} });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina A')).toBeInTheDocument());
      mockGet.mockClear();

      await userEvent.click(screen.getByTitle('Desactivar'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/maquinas/1/', { estado: 'inactiva' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Máquina Máquina A ahora está inactiva.');
      await waitFor(() => expect(mockGet).toHaveBeenCalled());
    });

    it('dado clic en editar una maquina cuando se abre el dialogo entonces precarga sus datos', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina A')).toBeInTheDocument());

      await userEvent.click(screen.getByTitle('Editar máquina'));

      expect(screen.getByText('Editar Máquina')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Máquina A')).toBeInTheDocument();
      expect(screen.getByDisplayValue('100')).toBeInTheDocument();
    });

    it('dado un error al cambiar el estado de una maquina cuando falla la peticion entonces muestra un toast de error', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1] });
      mockPatch.mockRejectedValueOnce(new Error('500'));
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina A')).toBeInTheDocument());
      await userEvent.click(screen.getByTitle('Desactivar'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cambiar el estado de la máquina.'));
    });

    it('dado el dialogo de edicion de maquina cuando se modifican nombre, capacidad y estado y se guarda entonces envia el PUT actualizado', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1] });
      mockPut.mockResolvedValueOnce({ data: {} });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina A')).toBeInTheDocument());
      await userEvent.click(screen.getByTitle('Editar máquina'));

      const nombreInput = screen.getByLabelText('Nombre de la Máquina');
      await userEvent.clear(nombreInput);
      await userEvent.type(nombreInput, 'Máquina A Renovada');

      const capacidadInput = screen.getByLabelText(/Capacidad/);
      await userEvent.clear(capacidadInput);
      await userEvent.type(capacidadInput, '150');

      await userEvent.click(screen.getByRole('combobox'));
      await userEvent.click(await screen.findByRole('option', { name: 'Mantenimiento' }));

      mockGet.mockClear();
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() =>
        expect(mockPut).toHaveBeenCalledWith('/maquinas/1/', expect.objectContaining({
          nombre: 'Máquina A Renovada',
          capacidad_maxima: 150,
          estado: 'mantenimiento',
          area: 1,
        }))
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Máquina actualizada correctamente.');
      await waitFor(() => expect(mockGet).toHaveBeenCalled());
    });

    it('dado un error al guardar la maquina editada cuando falla el PUT entonces muestra un toast de error', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1] });
      mockPut.mockRejectedValueOnce(new Error('500'));
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina A')).toBeInTheDocument());
      await userEvent.click(screen.getByTitle('Editar máquina'));
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al guardar la máquina.'));
    });

    it('dado clic en un operario del dialogo de maquina cuando se marca y desmarca su checkbox entonces alterna su seleccion y se envia en el guardado', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_2], '/users/': [OPERARIO_1] });
      mockPut.mockResolvedValueOnce({ data: {} });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina B')).toBeInTheDocument());
      await userEvent.click(screen.getByTitle('Editar máquina'));

      const checkbox = screen.getByLabelText('operario1');
      expect(checkbox).not.toBeChecked();

      await userEvent.click(checkbox);
      expect(checkbox).toBeChecked();

      await userEvent.click(checkbox);
      expect(checkbox).not.toBeChecked();

      await userEvent.click(checkbox);
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() =>
        expect(mockPut).toHaveBeenCalledWith('/maquinas/2/', expect.objectContaining({ operarios: [5] }))
      );
    });

    it('dado el dialogo de edicion de maquina abierto cuando se hace clic en Cancelar entonces se cierra sin guardar', async () => {
      mockEndpoints({ '/maquinas/': [MAQUINA_1] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Máquina A')).toBeInTheDocument());
      await userEvent.click(screen.getByTitle('Editar máquina'));
      expect(screen.getByText('Editar Máquina')).toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

      await waitFor(() => expect(screen.queryByText('Editar Máquina')).not.toBeInTheDocument());
      expect(mockPut).not.toHaveBeenCalled();
    });
  });

  describe('órdenes de producción pendientes — asignación', () => {
    it('dado ordenes pendientes cuando carga entonces las muestra con su codigo y peso requerido', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_PENDIENTE], '/maquinas/': [MAQUINA_1], '/users/': [OPERARIO_1] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
      expect(screen.getByText('Hilo Blanco')).toBeInTheDocument();
      expect(screen.getByText(/500 Kg/)).toBeInTheDocument();
    });

    it('dado ninguna orden pendiente cuando carga entonces muestra el mensaje vacio', async () => {
      mockEndpoints({ '/ordenes-produccion/': [] });
      renderComponent();

      await waitFor(() =>
        expect(screen.getByText('No hay órdenes pendientes de asignación en tu área.')).toBeInTheDocument()
      );
    });

    it('dado clic en asignar sin seleccionar maquina ni operario cuando se confirma entonces muestra un toast de error', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_PENDIENTE], '/maquinas/': [MAQUINA_1], '/users/': [OPERARIO_1] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Asignar/ }));

      expect(toastErrorMock).toHaveBeenCalledWith('Debes seleccionar una máquina y un operario.');
      expect(mockPatch).not.toHaveBeenCalled();
    });

    it('dado seleccion de maquina y operario cuando se hace clic en asignar entonces envia el patch correcto y refresca', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_PENDIENTE], '/maquinas/': [MAQUINA_1], '/users/': [OPERARIO_1] });
      mockPatch.mockResolvedValueOnce({ data: {} });
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
      const filaOrden = screen.getByText('OP-001').closest('div.flex.flex-col') as HTMLElement;

      await userEvent.click(within(filaOrden).getAllByRole('combobox')[0]);
      await userEvent.click(await screen.findByRole('option', { name: 'Máquina A' }));

      await userEvent.click(within(filaOrden).getAllByRole('combobox')[1]);
      await userEvent.click(await screen.findByRole('option', { name: 'operario1' }));

      mockGet.mockClear();
      await userEvent.click(screen.getByRole('button', { name: /Asignar/ }));

      await waitFor(() =>
        expect(mockPatch).toHaveBeenCalledWith('/ordenes-produccion/10/', {
          maquina_asignada: 1,
          operario_asignado: 5,
          estado: 'en_proceso',
        })
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Orden asignada e iniciada correctamente.');
      await waitFor(() => expect(mockGet).toHaveBeenCalled());
    });

    it('dado el boton de asignar cuando no hay maquinas ni operarios cargados entonces esta deshabilitado', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_PENDIENTE], '/maquinas/': [], '/users/': [] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
      expect(screen.getByRole('button', { name: /Asignar/ })).toBeDisabled();
    });

    it('dado un error al asignar una orden cuando falla la peticion entonces muestra un toast de error', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_PENDIENTE], '/maquinas/': [MAQUINA_1], '/users/': [OPERARIO_1] });
      mockPatch.mockRejectedValueOnce(new Error('500'));
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
      const filaOrden = screen.getByText('OP-001').closest('div.flex.flex-col') as HTMLElement;

      await userEvent.click(within(filaOrden).getAllByRole('combobox')[0]);
      await userEvent.click(await screen.findByRole('option', { name: 'Máquina A' }));
      await userEvent.click(within(filaOrden).getAllByRole('combobox')[1]);
      await userEvent.click(await screen.findByRole('option', { name: 'operario1' }));

      await userEvent.click(screen.getByRole('button', { name: /Asignar/ }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al asignar la orden.'));
    });
  });

  describe('producción en curso — trazabilidad', () => {
    it('dado ordenes en proceso cuando carga entonces las muestra en la seccion de trazabilidad', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_EN_PROCESO] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-002')).toBeInTheDocument());
      expect(screen.getByText('Tela Denim')).toBeInTheDocument();
    });

    it('dado ninguna orden en proceso cuando carga entonces muestra el mensaje vacio de trazabilidad', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByText('No hay órdenes en proceso en tu área.')).toBeInTheDocument());
    });

    it('dado clic en Ver flujo / Registrar cuando se abre el dialogo entonces renderiza TrazabilidadProducto con la orden seleccionada', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_EN_PROCESO] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-002')).toBeInTheDocument());
      expect(screen.queryByTestId('trazabilidad-producto-mock')).not.toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: /Ver flujo \/ Registrar/ }));

      expect(screen.getByTestId('trazabilidad-producto-mock')).toHaveTextContent('orden:20');
      expect(screen.getByTestId('trazabilidad-producto-mock')).toHaveTextContent('allowRegister:true');
    });

    it('dado el dialogo de trazabilidad abierto cuando se presiona Escape entonces se cierra', async () => {
      mockEndpoints({ '/ordenes-produccion/': [ORDEN_EN_PROCESO] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('OP-002')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Ver flujo \/ Registrar/ }));
      expect(screen.getByTestId('trazabilidad-producto-mock')).toBeInTheDocument();

      await userEvent.keyboard('{Escape}');

      await waitFor(() => expect(screen.queryByTestId('trazabilidad-producto-mock')).not.toBeInTheDocument());
    });
  });

  describe('gestión de lotes recientes', () => {
    it('dado lotes existentes cuando carga entonces los muestra en la tabla', async () => {
      mockEndpoints({ '/lotes-produccion/': [LOTE_1] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      expect(screen.getByText('Máquina A')).toBeInTheDocument();
      expect(screen.getByText('operario1')).toBeInTheDocument();
      expect(screen.getByText('80 Kg')).toBeInTheDocument();
    });

    it('dado clic en Rechazar cuando el usuario confirma entonces llama al endpoint de rechazo y refresca', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      vi.spyOn(window, 'alert').mockImplementation(() => {});
      mockEndpoints({ '/lotes-produccion/': [LOTE_1] });
      mockPost.mockResolvedValueOnce({ data: {} });
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      mockGet.mockClear();

      await userEvent.click(screen.getByRole('button', { name: /Rechazar/ }));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/lotes-produccion/1/rechazar/'));
      expect(window.alert).toHaveBeenCalledWith('Lote rechazado y movimientos revertidos.');
      await waitFor(() => expect(mockGet).toHaveBeenCalled());
    });

    it('dado clic en Rechazar cuando el usuario cancela entonces no llama al endpoint de rechazo', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      mockEndpoints({ '/lotes-produccion/': [LOTE_1] });
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Rechazar/ }));

      expect(mockPost).not.toHaveBeenCalledWith('/lotes-produccion/1/rechazar/');
    });

    it('dado un error al rechazar un lote cuando falla la peticion entonces muestra una alerta de error', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      vi.spyOn(window, 'alert').mockImplementation(() => {});
      mockEndpoints({ '/lotes-produccion/': [LOTE_1] });
      mockPost.mockRejectedValueOnce(new Error('500'));
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Rechazar/ }));

      await waitFor(() => expect(window.alert).toHaveBeenCalledWith('Error al rechazar el lote.'));
    });

    const makeLotes = (count: number): LoteProduccion[] =>
      Array.from({ length: count }, (_, i) => ({
        ...LOTE_1,
        id: i + 1,
        codigo_lote: `L-${String(i + 1).padStart(3, '0')}`,
      }));

    it('dado mas de 20 lotes cuando se hace clic en Siguiente y Anterior entonces navega entre paginas', async () => {
      mockEndpoints({ '/lotes-produccion/': makeLotes(25) });
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Anterior/ })).toBeDisabled();

      await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));

      await waitFor(() => expect(screen.getByText('L-021')).toBeInTheDocument());
      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Siguiente/ })).toBeDisabled();

      await userEvent.click(screen.getByRole('button', { name: /Anterior/ }));

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina cuando se escribe un numero y se presiona Enter entonces salta a esa pagina', async () => {
      mockEndpoints({ '/lotes-produccion/': makeLotes(25) });
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

      await userEvent.clear(irAInput);
      await userEvent.type(irAInput, '2{Enter}');

      await waitFor(() => expect(screen.getByText('L-021')).toBeInTheDocument());
      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    });

    it('dado el input de ir a pagina cuando pierde el foco con un numero valido entonces salta a esa pagina', async () => {
      mockEndpoints({ '/lotes-produccion/': makeLotes(25) });
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

      await userEvent.clear(irAInput);
      await userEvent.type(irAInput, '2');
      await userEvent.tab();

      await waitFor(() => expect(screen.getByText('L-021')).toBeInTheDocument());
    });

    it('dado un numero invalido en el input de ir a pagina cuando pierde el foco entonces no cambia de pagina', async () => {
      mockEndpoints({ '/lotes-produccion/': makeLotes(25) });
      renderComponent();

      await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
      const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

      await userEvent.clear(irAInput);
      await userEvent.type(irAInput, '99');
      await userEvent.tab();

      expect(screen.getByText('L-001')).toBeInTheDocument();
      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    });
  });

  describe('nueva orden de producción', () => {
    it('dado clic en Nueva Orden cuando se abre el dialogo entonces muestra el formulario', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Orden/ }));

      expect(screen.getByText('Nueva Orden de Producción')).toBeInTheDocument();
    });

    it('dado campos obligatorios vacios cuando se hace clic en Crear Orden entonces muestra un toast de error', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Orden/ }));
      await userEvent.click(screen.getByRole('button', { name: /Crear Orden/ }));

      expect(toastErrorMock).toHaveBeenCalledWith('Completa todos los campos obligatorios');
      expect(mockPost).not.toHaveBeenCalledWith('/ordenes-produccion/', expect.anything());
    });

    it('dado todos los campos obligatorios completos cuando se hace clic en Crear Orden entonces envia el payload correcto', async () => {
      mockEndpoints({
        '/productos/': [PRODUCTO_HILO],
        '/bodegas/': [BODEGA_1],
        '/formula-colors/': [FORMULA_1],
      });
      mockPost.mockResolvedValueOnce({ data: {} });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Orden/ }));

      await userEvent.type(screen.getByLabelText(/Código de Orden/), 'OP-TEST-01');
      await userEvent.type(screen.getByLabelText(/Peso Requerido/), '250');

      await userEvent.click(screen.getAllByRole('combobox')[0]);
      await userEvent.click(await screen.findByRole('option', { name: /HP-001/ }));

      await userEvent.click(screen.getAllByRole('combobox')[1]);
      await userEvent.click(await screen.findByRole('option', { name: 'Bodega Central' }));

      await userEvent.click(screen.getAllByRole('combobox')[2]);
      await userEvent.click(await screen.findByRole('option', { name: /HP-001/ }));

      await userEvent.click(screen.getAllByRole('combobox')[3]);
      await userEvent.click(await screen.findByRole('option', { name: 'Bodega Central' }));

      mockGet.mockClear();
      await userEvent.click(screen.getByRole('button', { name: /Crear Orden/ }));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/ordenes-produccion/', expect.objectContaining({
          codigo: 'OP-TEST-01',
          peso_neto_requerido: 250,
          producto_entrada: 1,
          bodega_entrada: 1,
          producto_salida: 1,
          bodega_salida: 1,
          area: 1,
        }))
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Orden de producción creada correctamente');
      await waitFor(() => expect(mockGet).toHaveBeenCalled());
    });

    it('dado un error de la api con detalle de campos cuando falla la creacion entonces muestra un toast con el detalle', async () => {
      mockEndpoints({
        '/productos/': [PRODUCTO_HILO],
        '/bodegas/': [BODEGA_1],
      });
      mockPost.mockRejectedValueOnce({ response: { data: { codigo: ['ya existe'] } } });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Orden/ }));

      await userEvent.type(screen.getByLabelText(/Código de Orden/), 'OP-TEST-02');
      await userEvent.type(screen.getByLabelText(/Peso Requerido/), '100');

      await userEvent.click(screen.getAllByRole('combobox')[0]);
      await userEvent.click(await screen.findByRole('option', { name: /HP-001/ }));
      await userEvent.click(screen.getAllByRole('combobox')[1]);
      await userEvent.click(await screen.findByRole('option', { name: 'Bodega Central' }));
      await userEvent.click(screen.getAllByRole('combobox')[2]);
      await userEvent.click(await screen.findByRole('option', { name: /HP-001/ }));
      await userEvent.click(screen.getAllByRole('combobox')[3]);
      await userEvent.click(await screen.findByRole('option', { name: 'Bodega Central' }));

      await userEvent.click(screen.getByRole('button', { name: /Crear Orden/ }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('codigo: ya existe'));
    });

    it('dado formula de color y observaciones completadas cuando se crea la orden entonces el payload incluye ambos campos opcionales', async () => {
      mockEndpoints({
        '/productos/': [PRODUCTO_HILO],
        '/bodegas/': [BODEGA_1],
        '/formula-colors/': [FORMULA_1],
      });
      mockPost.mockResolvedValueOnce({ data: {} });
      renderComponent();

      await waitFor(() => expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Orden/ }));

      await userEvent.type(screen.getByLabelText(/Código de Orden/), 'OP-TEST-03');
      await userEvent.type(screen.getByLabelText(/Peso Requerido/), '75');

      await userEvent.click(screen.getAllByRole('combobox')[0]);
      await userEvent.click(await screen.findByRole('option', { name: /HP-001/ }));
      await userEvent.click(screen.getAllByRole('combobox')[1]);
      await userEvent.click(await screen.findByRole('option', { name: 'Bodega Central' }));
      await userEvent.click(screen.getAllByRole('combobox')[2]);
      await userEvent.click(await screen.findByRole('option', { name: /HP-001/ }));
      await userEvent.click(screen.getAllByRole('combobox')[3]);
      await userEvent.click(await screen.findByRole('option', { name: 'Bodega Central' }));
      await userEvent.click(screen.getAllByRole('combobox')[4]);
      await userEvent.click(await screen.findByRole('option', { name: /F-001/ }));

      await userEvent.type(screen.getByLabelText(/Observaciones/), 'Urgente para cliente VIP');

      mockGet.mockClear();
      await userEvent.click(screen.getByRole('button', { name: /Crear Orden/ }));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/ordenes-produccion/', expect.objectContaining({
          codigo: 'OP-TEST-03',
          formula_color: 1,
          observaciones: 'Urgente para cliente VIP',
        }))
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Orden de producción creada correctamente');
      await waitFor(() => expect(mockGet).toHaveBeenCalled());
    });

    it('dado clic en Cancelar cuando el dialogo esta abierto entonces lo cierra sin crear la orden', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Orden/ }));
      expect(screen.getByText('Nueva Orden de Producción')).toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: /Cancelar/ }));

      await waitFor(() => expect(screen.queryByText('Nueva Orden de Producción')).not.toBeInTheDocument());
      expect(mockPost).not.toHaveBeenCalled();
    });
  });

  describe('actualizar datos', () => {
    it('dado el panel ya cargado cuando el usuario hace clic en Actualizar Datos entonces vuelve a solicitar la información', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByText('Panel de Control - Área de Producción')).toBeInTheDocument());
      const llamadasIniciales = mockGet.mock.calls.length;

      await userEvent.click(screen.getByRole('button', { name: /Actualizar Datos/ }));

      await waitFor(() => expect(mockGet.mock.calls.length).toBeGreaterThan(llamadasIniciales));
    });
  });

  describe('componentes hijos delegados', () => {
    it('dado el panel cargado cuando renderiza entonces monta ManageMaquinas, EtapasProduccion y FlujoProduccion con el area del perfil', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByText('Gestión de Máquinas')).toBeInTheDocument());
      expect(screen.getByRole('heading', { name: 'Máquinas' })).toBeInTheDocument();
      expect(screen.getByTestId('etapas-produccion-mock')).toHaveTextContent('area:1');
      expect(screen.getByTestId('flujo-produccion-mock')).toBeInTheDocument();
    });
  });
});
