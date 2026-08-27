import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageOrdenesProduccion } from './ManageOrdenesProduccion';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import { OrdenProduccion, Maquina, Area, Sede } from '../../lib/types';

// Mock axios / apiClient — necesario porque el componente hace GET /areas/ al abrir el diálogo
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  };
  return {
    default: { ...mockAxiosInstance, create: vi.fn(() => mockAxiosInstance) },
  };
});
import apiClient from '../../lib/axios';

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: any[]) => toastErrorMock(...args), success: vi.fn() },
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

// ── Fixtures ──────────────────────────────────────────────────────────────────

const mockAreas: Area[] = [
  { id: 1, nombre: 'Tintorería', sede: 1 },
  { id: 2, nombre: 'Empaquetado', sede: 1 },
];

const mockSedes: Sede[] = [
  { id: 1, nombre: 'Planta Quito', location: 'Quito Norte', status: 'activo' },
];

const mockOrdenes: OrdenProduccion[] = [
  {
    id: 1,
    codigo: 'OP-001',
    producto: 1,
    producto_nombre: 'Tela Algodón',
    formula_color: 1,
    formula_color_nombre: 'Rojo Pasión',
    peso_neto_requerido: 100,
    peso_producido: 50,
    estado: 'en_proceso',
    fecha_creacion: '2026-05-01',
    fecha_modificacion: '2026-05-01',
    sede: 1,
    sede_nombre: 'Quito',
    area: 1,
    maquina_asignada: 1,
    maquina_asignada_nombre: 'Jet 1',
    inventario_descontado: false,
    fecha_fin_planificada: '2099-05-10',
    prioridad: 'normal',
  },
  {
    id: 2,
    codigo: 'OP-002',
    producto: 2,
    producto_nombre: 'Tela Poliéster',
    formula_color: 2,
    formula_color_nombre: 'Azul Marino',
    peso_neto_requerido: 200,
    peso_producido: 0,
    estado: 'pendiente',
    fecha_creacion: '2026-05-02',
    fecha_modificacion: '2026-05-02',
    sede: 1,
    sede_nombre: 'Quito',
    area: 2,
    maquina_asignada: 2,
    maquina_asignada_nombre: 'Jigger 1',
    inventario_descontado: false,
    fecha_fin_planificada: '2099-05-20',
    prioridad: 'alta',
  },
];

const mockMaquinas: Maquina[] = [
  { id: 1, nombre: 'Jet 1', capacidad_maxima: 150, eficiencia_ideal: 90, estado: 'operativa', area: 1 },
  { id: 2, nombre: 'Jigger 1', capacidad_maxima: 200, eficiencia_ideal: 85, estado: 'operativa', area: 1 },
];

const defaultProps = {
  ordenes: mockOrdenes,
  productos: [],
  formulas: [],
  sedes: [],
  maquinas: mockMaquinas,
  areas: [],          // prop inicial vacío — las áreas frescas llegan via fetch al abrir el diálogo
  bodegas: [],
  onOrdenCreate: vi.fn(),
  onOrdenUpdate: vi.fn(),
  onOrderStatusChange: vi.fn(),
  onOrdenDelete: vi.fn(),
  loading: false,
  onDataRefresh: vi.fn(),
};

const renderComponent = () =>
  render(
    <MemoryRouter initialEntries={['/']}>
      <ManageOrdenesProduccion {...defaultProps} />
    </MemoryRouter>
  );

// ── Tests: tabla ──────────────────────────────────────────────────────────────

describe('ManageOrdenesProduccion — tabla', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
      return Promise.resolve({ data: [] });
    });
  });

  it('renderiza los códigos y máquinas de todas las órdenes', () => {
    renderComponent();
    expect(screen.getByText('OP-001')).toBeInTheDocument();
    expect(screen.getByText('OP-002')).toBeInTheDocument();
    expect(screen.getByText('Jet 1')).toBeInTheDocument();
    expect(screen.getByText('Jigger 1')).toBeInTheDocument();
  });

  it('filtra por estado: al seleccionar Pendiente solo muestra OP-002', async () => {
    const user = userEvent.setup();
    renderComponent();

    const comboboxes = screen.getAllByRole('combobox');
    await user.click(comboboxes[0]); // primer select: filtro de estado

    const optionPendiente = await screen.findByRole('option', { name: /Pendiente/i });
    await user.click(optionPendiente);

    expect(screen.getByText('OP-002')).toBeInTheDocument();
    expect(screen.queryByText('OP-001')).not.toBeInTheDocument();
  });

  it('filtra por máquina: al seleccionar Jet 1 solo muestra OP-001', async () => {
    const user = userEvent.setup();
    renderComponent();

    const comboboxes = screen.getAllByRole('combobox');
    await user.click(comboboxes[1]); // segundo select: filtro de máquina

    const optionJet1 = await screen.findByRole('option', { name: /Jet 1/i });
    await user.click(optionJet1);

    expect(screen.getByText('OP-001')).toBeInTheDocument();
    expect(screen.queryByText('OP-002')).not.toBeInTheDocument();
  });
});

// ── Tests: diálogo nueva orden ────────────────────────────────────────────────

describe('ManageOrdenesProduccion — diálogo nueva orden', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
      return Promise.resolve({ data: [] });
    });
  });

  it('al abrir el diálogo hace GET /areas/ para obtener áreas frescas', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/areas/');
    });
  });

  it('tras abrir el diálogo el placeholder del área cambia a "Selecciona el área de destino"', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));

    // Inicialmente (areas=[]) se muestra "No hay áreas registradas".
    // Tras el fetch con mockAreas, areas.length > 0 y el placeholder cambia.
    await waitFor(() => {
      expect(screen.getByText('Selecciona el área de destino')).toBeInTheDocument();
    });
  });

  it('el diálogo muestra el input de Código', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Código/i)).toBeInTheDocument();
    });
  });
});

// ── Tests: OrdenDetalleSheet (clic en fila) ───────────────────────────────────

describe('ManageOrdenesProduccion — OrdenDetalleSheet (clic en fila)', () => {
  // Props con catálogos poblados para que el Sheet resuelva nombres
  const propsConCatalogos = {
    ...defaultProps,
    sedes: mockSedes,
    areas: mockAreas,
  };

  const renderConCatalogos = () =>
    render(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...propsConCatalogos} />
      </MemoryRouter>
    );

  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
      if (url.includes('trazabilidad')) return Promise.resolve({ data: null });
      return Promise.resolve({ data: [] });
    });
  });

  it('al hacer clic en una fila el Sheet se abre mostrando el código de la orden', async () => {
    const user = userEvent.setup();
    renderConCatalogos();

    // Antes del clic existe un solo 'OP-001' (en la tabla)
    await user.click(screen.getByText('OP-001'));

    // Tras abrir el Sheet el código aparece también en el título del panel
    await waitFor(() => {
      expect(screen.getAllByText('OP-001').length).toBeGreaterThanOrEqual(2);
    });
  });

  it('el Sheet resuelve el nombre del área desde el catálogo (no del campo _nombre)', async () => {
    const user = userEvent.setup();
    renderConCatalogos();

    await user.click(screen.getByText('OP-001'));

    // OP-001 tiene area:1, mockAreas[0] = {id:1, nombre:'Tintorería'} → debe aparecer
    await waitFor(() => {
      expect(screen.getByText('Tintorería')).toBeInTheDocument();
    });
  });

  it('el Sheet resuelve el nombre de la sede desde el catálogo', async () => {
    const user = userEvent.setup();
    renderConCatalogos();

    await user.click(screen.getByText('OP-001'));

    // OP-001 tiene sede:1, mockSedes[0] = {id:1, nombre:'Planta Quito'}
    await waitFor(() => {
      expect(screen.getByText('Planta Quito')).toBeInTheDocument();
    });
  });

  it('el Sheet NO muestra los labels "Máquina" ni "Operario" dentro del panel', async () => {
    const user = userEvent.setup();
    renderConCatalogos();

    await user.click(screen.getByText('OP-001'));

    // Espera a que el Sheet se abra
    const sheetContent = await waitFor(() => {
      const el = document.querySelector('[data-slot="sheet-content"]');
      expect(el).not.toBeNull();
      return el as HTMLElement;
    });

    const inSheet = within(sheetContent);
    // Los labels Máquina y Operario fueron eliminados del Sheet (los gestiona el Jefe de Área)
    expect(inSheet.queryByText('Máquina')).not.toBeInTheDocument();
    expect(inSheet.queryByText('Operario')).not.toBeInTheDocument();
  });

  it('el botón Editar del Sheet abre el formulario de edición', async () => {
    const user = userEvent.setup();
    renderConCatalogos();

    await user.click(screen.getByText('OP-001'));

    // Espera a que el Sheet se abra
    await waitFor(() => {
      expect(screen.getAllByText('OP-001').length).toBeGreaterThanOrEqual(2);
    });

    // Clic en Editar dentro del Sheet
    const sheetContent = document.querySelector('[data-slot="sheet-content"]') as HTMLElement;
    const btnEditar = within(sheetContent).getByRole('button', { name: /Editar/i });
    await user.click(btnEditar);

    // El formulario de edición debe abrirse (contiene el input de Código)
    await waitFor(() => {
      expect(screen.getByLabelText(/Código/i)).toBeInTheDocument();
    });
  });

  it('al presionar Escape con el Sheet abierto entonces limpia la orden seleccionada', async () => {
    const user = userEvent.setup();
    renderConCatalogos();

    await user.click(screen.getByText('OP-001'));
    await waitFor(() => {
      expect(screen.getAllByText('OP-001').length).toBeGreaterThanOrEqual(2);
    });

    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.getAllByText('OP-001').length).toBe(1);
    });
  });
});

// ── Tests: ramas adicionales de cobertura ──────────────────────────────────────

describe('ManageOrdenesProduccion — ramas adicionales de cobertura', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
      return Promise.resolve({ data: [] });
    });
  });

  it('dado que /areas/ responde en formato paginado {results} entonces usa .results', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: { results: mockAreas } });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => {
      expect(screen.getByText('Selecciona el área de destino')).toBeInTheDocument();
    });
  });

  it('dado que /areas/ responde sin resultados ni results entonces usa un arreglo vacio', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: {} });
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    renderComponent();
    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => {
      expect(screen.getByText('No hay áreas registradas')).toBeInTheDocument();
    });
  });

  it('dado ?page=0 en la URL entonces normaliza a la pagina 1', () => {
    render(
      <MemoryRouter initialEntries={['/?page=0']}>
        <ManageOrdenesProduccion {...defaultProps} />
      </MemoryRouter>
    );
    expect(screen.getByText(/Página 1 de/)).toBeInTheDocument();
  });

  it('al presionar Escape en el dialogo de nueva orden entonces se cierra y resetea el formulario', async () => {
    const user = userEvent.setup();
    renderComponent();
    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/Código/i)).toBeInTheDocument();
    });
    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByLabelText(/Código/i)).not.toBeInTheDocument();
    });
  });

  it('dado el dialogo de nueva orden abierto cuando areasProp cambia entonces no sincroniza hasta cerrar', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return new Promise(() => {});
      return Promise.resolve({ data: [] });
    });
    const user = userEvent.setup();
    const { rerender } = render(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...defaultProps} areas={[]} />
      </MemoryRouter>
    );
    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/Código/i)).toBeInTheDocument();
    });
    rerender(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...defaultProps} areas={mockAreas} />
      </MemoryRouter>
    );
    expect(screen.getByText('No hay áreas registradas')).toBeInTheDocument();
  });

  it('dado sin onOrderStatusChange cuando intenta iniciar el proceso entonces muestra un toast de error', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...defaultProps} onOrderStatusChange={undefined} />
      </MemoryRouter>
    );
    const row = screen.getByText('OP-002').closest('tr') as HTMLElement; // OP-002 está 'pendiente'
    const menuButton = within(row).getByRole('button', { name: 'Abrir menu' });
    await user.click(menuButton);
    const iniciarItem = await screen.findByRole('menuitem', { name: /Iniciar Proceso/i });
    await user.click(iniciarItem);
    expect(toastErrorMock).toHaveBeenCalledWith('La función de cambio de estado no está implementada.');
  });

  it('dado una orden con campos ausentes cuando edita entonces usa los valores por defecto y muestra "Sin asignar" y "-"', async () => {
    const mockOrdenSparse: any = {
      id: 3,
      codigo: 'OP-003',
      producto_nombre: 'Producto X',
      formula_color_nombre: '',
      peso_neto_requerido: 30,
      peso_producido: 0,
      estado: 'pendiente',
      fecha_creacion: '2026-05-03',
      fecha_modificacion: '2026-05-03',
      inventario_descontado: true,
    };
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...defaultProps} ordenes={[...mockOrdenes, mockOrdenSparse]} />
      </MemoryRouter>
    );

    // Rama de tabla: sin maquina_asignada_nombre -> "Sin asignar"; sin fecha_fin_planificada -> "-"
    const row = screen.getByText('OP-003').closest('tr') as HTMLElement;
    expect(within(row).getByText('Sin asignar')).toBeInTheDocument();
    expect(within(row).getByText('-')).toBeInTheDocument();

    // Rama de handleEdit: producto/formula_color/sede/area/fechas/prioridad ausentes
    const menuButton = within(row).getByRole('button', { name: 'Abrir menu' });
    await user.click(menuButton);
    const editarItem = await screen.findByRole('menuitem', { name: /Editar/i });
    await user.click(editarItem);

    await waitFor(() => {
      expect(screen.getByLabelText(/Código/i)).toHaveValue('OP-003');
    });
  });

  it('dado una orden vencida cuando renderiza entonces resalta la fecha en rojo', () => {
    const ordenVencida: any = {
      ...mockOrdenes[0],
      id: 4,
      codigo: 'OP-004',
      fecha_fin_planificada: '2020-01-01',
    };
    render(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...defaultProps} ordenes={[...mockOrdenes, ordenVencida]} />
      </MemoryRouter>
    );
    const fecha = screen.getByText('2020-01-01');
    expect(fecha.className).toContain('text-red-600');
  });

  it('dado una orden que vence hoy cuando renderiza entonces resalta la fecha en ambar', () => {
    const hoy = new Date().toISOString().split('T')[0];
    const ordenHoy: any = {
      ...mockOrdenes[0],
      id: 5,
      codigo: 'OP-005',
      fecha_fin_planificada: hoy,
    };
    render(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...defaultProps} ordenes={[...mockOrdenes, ordenHoy]} />
      </MemoryRouter>
    );
    const fecha = screen.getByText(hoy);
    expect(fecha.className).toContain('text-amber-600');
  });
});

// ── Tests: paginación con muchas órdenes ────────────────────────────────────────

describe('ManageOrdenesProduccion — paginación con muchas órdenes', () => {
  const manyOrdenes: OrdenProduccion[] = Array.from({ length: 25 }, (_, i) => ({
    ...mockOrdenes[0],
    id: i + 10,
    codigo: `OP-${100 + i}`,
  }));

  const renderManyOrdenes = () =>
    render(
      <MemoryRouter initialEntries={['/']}>
        <ManageOrdenesProduccion {...defaultProps} ordenes={manyOrdenes} />
      </MemoryRouter>
    );

  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
      return Promise.resolve({ data: [] });
    });
  });

  it('dado "Ir a página" con un valor valido cuando pierde el foco entonces navega', async () => {
    const user = userEvent.setup();
    renderManyOrdenes();
    const irAInput = screen.getByRole('spinbutton');
    await user.clear(irAInput);
    await user.type(irAInput, '2');
    await user.tab();
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado "Ir a página" con un valor fuera de rango cuando pierde el foco entonces no cambia de pagina', async () => {
    const user = userEvent.setup();
    renderManyOrdenes();
    const irAInput = screen.getByRole('spinbutton');
    await user.clear(irAInput);
    await user.type(irAInput, '99');
    await user.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado "Ir a página" con 0 cuando pierde el foco entonces no cambia de pagina', async () => {
    const user = userEvent.setup();
    renderManyOrdenes();
    const irAInput = screen.getByRole('spinbutton');
    await user.clear(irAInput);
    await user.type(irAInput, '0');
    await user.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado "Ir a página" vacio cuando pierde el foco entonces no cambia de pagina', async () => {
    const user = userEvent.setup();
    renderManyOrdenes();
    const irAInput = screen.getByRole('spinbutton');
    await user.clear(irAInput);
    await user.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });
});
