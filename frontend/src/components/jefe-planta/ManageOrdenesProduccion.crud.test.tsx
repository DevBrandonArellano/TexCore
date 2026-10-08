import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageOrdenesProduccion } from './ManageOrdenesProduccion';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import { OrdenProduccion, Maquina, Area, Sede, Producto, Bodega, FormulaColor } from '../../lib/types';

// Mock axios / apiClient — mismo patrón que ManageOrdenesProduccion.test.tsx
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

// Mock sonner — para poder verificar los toasts de validación / éxito / error
const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => toastErrorMock(...args),
    success: (...args: unknown[]) => toastSuccessMock(...args),
  },
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

const mockProductos: Producto[] = [
  { id: 1, codigo: 'P-1', descripcion: 'Tela Cruda', tipo: 'tela', unidad_medida: 'kg', stock_minimo: 10, precio_base: 5 },
  { id: 2, codigo: 'P-2', descripcion: 'Tela Teñida', tipo: 'tela', unidad_medida: 'kg', stock_minimo: 10, precio_base: 8 },
];

const mockBodegas: Bodega[] = [
  { id: 1, nombre: 'Bodega Central', sede: 1 },
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

const buildProps = (overrides: Partial<React.ComponentProps<typeof ManageOrdenesProduccion>> = {}) => ({
  ordenes: mockOrdenes,
  productos: mockProductos,
  formulas: [],
  sedes: mockSedes,
  maquinas: mockMaquinas,
  areas: mockAreas,
  bodegas: mockBodegas,
  onOrdenCreate: vi.fn(() => Promise.resolve(true)),
  onOrdenUpdate: vi.fn(() => Promise.resolve(true)),
  onOrderStatusChange: vi.fn(() => Promise.resolve(true)),
  onOrdenDelete: vi.fn(() => Promise.resolve(true)),
  loading: false,
  onDataRefresh: vi.fn(),
  ...overrides,
});

const renderComponent = (overrides: Partial<React.ComponentProps<typeof ManageOrdenesProduccion>> = {}) => {
  const props = buildProps(overrides);
  render(
    <MemoryRouter initialEntries={['/']}>
      <ManageOrdenesProduccion {...props} />
    </MemoryRouter>
  );
  return props;
};

const getDialogContent = () => document.querySelector('[data-slot="dialog-content"]') as HTMLElement;
const getSheetContent = () => document.querySelector('[data-slot="sheet-content"]') as HTMLElement;

const openRowMenu = async (user: ReturnType<typeof userEvent.setup>, rowIndex: number) => {
  const triggers = screen.getAllByRole('button', { name: /Abrir menu/i });
  await user.click(triggers[rowIndex]);
};

beforeEach(() => {
  vi.clearAllMocks();
  (apiClient.get as Mock).mockImplementation((url: string) => {
    if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
    if (url.includes('trazabilidad')) return Promise.resolve({ data: null });
    if (url.includes('requisitos_materiales')) return Promise.resolve({ data: { peso_total_op: 0, requisitos: [] } });
    return Promise.resolve({ data: [] });
  });
});

// ── Tests: creación de OP ─────────────────────────────────────────────────────

describe('ManageOrdenesProduccion — crear orden', () => {
  it('dado el formulario vacío cuando se hace clic en Crear entonces muestra un toast de error y no llama a onOrdenCreate', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => expect(screen.getByLabelText(/Código/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /^Crear$/i }));

    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(props.onOrdenCreate).not.toHaveBeenCalled();
  });

  it('dado código, área y peso completos cuando se hace clic en Crear entonces llama a onOrdenCreate con el payload transformado y cierra el diálogo', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => expect(screen.getByText('Selecciona el área de destino')).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Código/i), 'OP-100');
    await user.type(screen.getByLabelText(/Peso Neto Requerido/i), '150');

    const dialog = getDialogContent();
    const comboboxes = within(dialog).getAllByRole('combobox');
    await user.click(comboboxes[0]); // Área
    await user.click(await screen.findByRole('option', { name: 'Tintorería' }));

    await user.click(comboboxes[1]); // Prioridad
    await user.click(await screen.findByRole('option', { name: 'Alta' }));

    await user.click(screen.getByRole('button', { name: /^Crear$/i }));

    await waitFor(() => {
      expect(props.onOrdenCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          codigo: 'OP-100',
          peso_neto_requerido: '150',
          area: 1,
          prioridad: 'alta',
        })
      );
    });

    // El diálogo se cierra tras un create exitoso
    await waitFor(() => {
      expect(screen.queryByLabelText(/Código/i)).not.toBeInTheDocument();
    });
  });

  it('dado que onOrdenCreate resuelve false cuando se envía el formulario entonces el diálogo permanece abierto', async () => {
    const user = userEvent.setup();
    renderComponent({ onOrdenCreate: vi.fn(() => Promise.resolve(false)) });

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => expect(screen.getByText('Selecciona el área de destino')).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Código/i), 'OP-100');
    await user.type(screen.getByLabelText(/Peso Neto Requerido/i), '150');

    const dialog = getDialogContent();
    const comboboxes = within(dialog).getAllByRole('combobox');
    await user.click(comboboxes[0]);
    await user.click(await screen.findByRole('option', { name: 'Tintorería' }));

    await user.click(screen.getByRole('button', { name: /^Crear$/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Código/i)).toBeInTheDocument();
    });
  });

  it('dado el formulario de creación abierto cuando cancela entonces se cierra sin llamar a onOrdenCreate', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => expect(screen.getByLabelText(/Código/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Cancelar/i }));

    await waitFor(() => {
      expect(screen.queryByLabelText(/Código/i)).not.toBeInTheDocument();
    });
    expect(props.onOrdenCreate).not.toHaveBeenCalled();
  });
});

// ── Tests: edición de OP ──────────────────────────────────────────────────────

describe('ManageOrdenesProduccion — editar orden', () => {
  it('dado el menú de acciones de fila cuando se hace clic en Editar entonces abre el formulario con Actualizar', async () => {
    const user = userEvent.setup();
    renderComponent();

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Editar/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Actualizar/i })).toBeInTheDocument();
    });
    // El código de la orden se precarga en el input
    expect(screen.getByLabelText(/Código/i)).toHaveValue('OP-001');
  });

  it('dado un formulario de edición sin producto de salida cuando se hace clic en Actualizar entonces muestra el error de validación y no llama a onOrdenUpdate', async () => {
    // OP-001 sólo trae el campo legado `producto` (sin producto_salida), por lo que
    // handleEdit precarga producto_entrada desde ese alias pero deja producto_salida vacío.
    const user = userEvent.setup();
    const props = renderComponent();

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Editar/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Actualizar/i })).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Actualizar/i }));

    expect(await screen.findByText('El producto de salida es requerido')).toBeInTheDocument();
    expect(props.onOrdenUpdate).not.toHaveBeenCalled();
  });

  it('dado producto de entrada y salida seleccionados cuando se hace clic en Actualizar entonces llama a onOrdenUpdate con el id y el payload transformado', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Editar/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Actualizar/i })).toBeInTheDocument());

    const dialog = getDialogContent();
    const comboboxes = within(dialog).getAllByRole('combobox');
    // Orden en el formulario de edición: producto_entrada, bodega_entrada, producto_salida, bodega_salida, área, prioridad
    await user.click(comboboxes[0]);
    await user.click(await screen.findByRole('option', { name: 'Tela Cruda' }));

    await user.click(comboboxes[2]);
    await user.click(await screen.findByRole('option', { name: 'Tela Teñida' }));

    await user.click(screen.getByRole('button', { name: /Actualizar/i }));

    await waitFor(() => {
      expect(props.onOrdenUpdate).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          producto_entrada: 1,
          producto_salida: 2,
        })
      );
    });
  });
});

// ── Tests: fórmula, bodega de químicos y justificación ──────────────────────

const formulaOficial = { id: 10, codigo: 'F-10', nombre_color: 'Rojo Oficial', version_oficial: 2 } as FormulaColor;
const formulaEnPruebas = { id: 11, codigo: 'F-11', nombre_color: 'Verde en Pruebas', version_oficial: null } as FormulaColor;

describe('ManageOrdenesProduccion — fórmula y químicos', () => {
  it('dado fórmulas con y sin versión oficial cuando crea una orden entonces solo ofrece las oficiales y envía fórmula y bodega', async () => {
    const user = userEvent.setup();
    const props = renderComponent({ formulas: [formulaOficial, formulaEnPruebas] });

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => expect(screen.getByText('Selecciona el área de destino')).toBeInTheDocument());
    await user.type(screen.getByLabelText(/Código/i), 'OP-200');
    await user.type(screen.getByLabelText(/Peso Neto Requerido/i), '80');

    const comboboxes = within(getDialogContent()).getAllByRole('combobox');
    await user.click(comboboxes[0]);
    await user.click(await screen.findByRole('option', { name: 'Tintorería' }));

    // Orden en creación: área, prioridad, fórmula, bodega de químicos
    await user.click(comboboxes[2]);
    expect(screen.queryByRole('option', { name: /Verde en Pruebas/ })).not.toBeInTheDocument();
    await user.click(await screen.findByRole('option', { name: /Rojo Oficial/ }));

    await user.click(comboboxes[3]);
    await user.click(await screen.findByRole('option', { name: 'Bodega Central' }));

    await user.click(screen.getByRole('button', { name: /^Crear$/i }));

    await waitFor(() => expect(props.onOrdenCreate).toHaveBeenCalledWith(
      expect.objectContaining({ formula_color: 10, bodega_quimicos: 1 }),
    ));
  });

  it('dado fórmula y bodega elegidas cuando vuelve a «Sin fórmula» y «Sin bodega» entonces envía ambos en null', async () => {
    const user = userEvent.setup();
    const props = renderComponent({ formulas: [formulaOficial] });

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => expect(screen.getByText('Selecciona el área de destino')).toBeInTheDocument());
    await user.type(screen.getByLabelText(/Código/i), 'OP-300');
    await user.type(screen.getByLabelText(/Peso Neto Requerido/i), '50');
    const comboboxes = within(getDialogContent()).getAllByRole('combobox');
    await user.click(comboboxes[0]);
    await user.click(await screen.findByRole('option', { name: 'Tintorería' }));

    await user.click(comboboxes[2]);
    await user.click(await screen.findByRole('option', { name: /Rojo Oficial/ }));
    // Con fórmula y sin bodega se avisa que no habrá descuento de químicos.
    expect(screen.getByText(/Sin bodega no se descuentan los químicos/)).toBeInTheDocument();
    await user.click(comboboxes[3]);
    await user.click(await screen.findByRole('option', { name: 'Bodega Central' }));

    await user.click(comboboxes[2]);
    await user.click(await screen.findByRole('option', { name: 'Sin fórmula' }));
    await user.click(comboboxes[3]);
    await user.click(await screen.findByRole('option', { name: 'Sin bodega' }));
    expect(screen.queryByText(/Sin bodega no se descuentan los químicos/)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^Crear$/i }));
    await waitFor(() => expect(props.onOrdenCreate).toHaveBeenCalledWith(
      expect.objectContaining({ formula_color: null, bodega_quimicos: null }),
    ));
  });

  it('dado una orden sin químicos descontados cuando la edita entonces no pide justificación', async () => {
    const user = userEvent.setup();
    renderComponent();

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Editar/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Actualizar/i })).toBeInTheDocument());

    expect(screen.queryByLabelText(/Justificación del cambio/i)).not.toBeInTheDocument();
  });

  it('dado una orden con químicos descontados cuando actualiza sin justificación entonces la exige y no envía', async () => {
    const user = userEvent.setup();
    const ordenes = [{ ...mockOrdenes[0], producto_entrada: 1, producto_salida: 2, inventario_descontado: true }];
    const props = renderComponent({ ordenes: ordenes as OrdenProduccion[] });

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Editar/i }));
    await waitFor(() => expect(screen.getByLabelText(/Justificación del cambio/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Actualizar/i }));

    expect(await screen.findByText(/indica la justificación del cambio/i)).toBeInTheDocument();
    expect(props.onOrdenUpdate).not.toHaveBeenCalled();
  });

  it('dado una orden con químicos descontados cuando actualiza con justificación entonces la envía', async () => {
    const user = userEvent.setup();
    const ordenes = [{ ...mockOrdenes[0], producto_entrada: 1, producto_salida: 2, inventario_descontado: true }];
    const props = renderComponent({ ordenes: ordenes as OrdenProduccion[] });

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Editar/i }));
    await user.type(await screen.findByLabelText(/Justificación del cambio/i), 'Pedido aumentó a 120 kg');
    await user.click(screen.getByRole('button', { name: /Actualizar/i }));

    await waitFor(() => expect(props.onOrdenUpdate).toHaveBeenCalledWith(
      1, expect.objectContaining({ justificacion: 'Pedido aumentó a 120 kg' }),
    ));
  });
});

// ── Tests: eliminar orden ─────────────────────────────────────────────────────

describe('ManageOrdenesProduccion — eliminar orden', () => {
  it('dado el menú de acciones de fila cuando se hace clic en Eliminar entonces llama a onOrdenDelete con el id de la orden', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Eliminar/i }));

    // No elimina sin justificación: primero abre el diálogo (ISO 9001).
    expect(props.onOrdenDelete).not.toHaveBeenCalled();
    const dialogo = await screen.findByRole('dialog');
    await user.type(within(dialogo).getByLabelText('Justificación'), 'Orden duplicada');
    await user.click(within(dialogo).getByRole('button', { name: 'Eliminar orden' }));

    expect(props.onOrdenDelete).toHaveBeenCalledWith(1, 'Orden duplicada');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('dado el Sheet de detalle abierto cuando se hace clic en Eliminar entonces llama a onOrdenDelete y cierra el Sheet', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await user.click(screen.getByText('OP-001'));
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    const btnEliminar = within(getSheetContent()).getByRole('button', { name: /Eliminar/i });
    await user.click(btnEliminar);

    await waitFor(() => {
      expect(document.querySelector('[data-slot="sheet-content"]')).not.toBeInTheDocument();
    });
    const dialogo = await screen.findByRole('dialog');
    await user.type(within(dialogo).getByLabelText('Justificación'), 'Orden duplicada');
    await user.click(within(dialogo).getByRole('button', { name: 'Eliminar orden' }));
    expect(props.onOrdenDelete).toHaveBeenCalledWith(1, 'Orden duplicada');
  });
});

// ── Tests: cambio de estado ───────────────────────────────────────────────────

describe('ManageOrdenesProduccion — cambio de estado', () => {
  it('dado una orden pendiente en el Sheet cuando se hace clic en "Iniciar Proceso" entonces llama a onOrderStatusChange con en_proceso', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await user.click(screen.getByText('OP-002')); // pendiente
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /Iniciar Proceso/i }));

    expect(props.onOrderStatusChange).toHaveBeenCalledWith(2, 'en_proceso');
  });

  it('dado una orden en proceso en el Sheet cuando se hace clic en "Marcar como Finalizada" entonces llama a onOrderStatusChange con finalizada', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await user.click(screen.getByText('OP-001')); // en_proceso
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /Marcar como Finalizada/i }));

    expect(props.onOrderStatusChange).toHaveBeenCalledWith(1, 'finalizada');
  });

  it('dado que no se provee onOrderStatusChange cuando se intenta cambiar el estado entonces muestra un toast de error', async () => {
    const user = userEvent.setup();
    renderComponent({ onOrderStatusChange: undefined });

    await user.click(screen.getByText('OP-002'));
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /Iniciar Proceso/i }));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('La función de cambio de estado no está implementada.');
    });
  });

  it('dado el menú de acciones de fila de una orden pendiente cuando se hace clic en "Iniciar Proceso" entonces llama a onOrderStatusChange', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await openRowMenu(user, 1); // OP-002, pendiente
    await user.click(screen.getByRole('menuitem', { name: /Iniciar Proceso/i }));

    expect(props.onOrderStatusChange).toHaveBeenCalledWith(2, 'en_proceso');
  });

  it('dado el menú de acciones de fila de una orden en proceso cuando se hace clic en "Marcar como Finalizada" entonces llama a onOrderStatusChange', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await openRowMenu(user, 0); // OP-001, en_proceso
    await user.click(screen.getByRole('menuitem', { name: /Marcar como Finalizada/i }));

    expect(props.onOrderStatusChange).toHaveBeenCalledWith(1, 'finalizada');
  });
});

// ── Tests: Requisitos de Materiales ───────────────────────────────────────────

describe('ManageOrdenesProduccion — Requisitos de Materiales', () => {
  it('dado clic en Requisitos desde el Sheet cuando la API responde entonces muestra el detalle de insumos', async () => {
    const user = userEvent.setup();
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
      if (url.includes('trazabilidad')) return Promise.resolve({ data: null });
      if (url.includes('requisitos_materiales')) {
        return Promise.resolve({
          data: {
            peso_total_op: 100,
            requisitos: [
              { producto_nombre: 'Colorante Rojo', tipo: 'quimico', es_base: false, cantidad_requerida: 5, unidad: 'kg' },
            ],
          },
        });
      }
      return Promise.resolve({ data: [] });
    });

    renderComponent();

    await user.click(screen.getByText('OP-001'));
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /Requisitos/i }));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/ordenes-produccion/1/requisitos_materiales/');
    });

    expect(await screen.findByText('Colorante Rojo')).toBeInTheDocument();
    expect(within(getDialogContent()).getByText('100 Kg')).toBeInTheDocument();
  });

  it('dado que la API de requisitos falla cuando se abre el diálogo entonces muestra un toast de error', async () => {
    const user = userEvent.setup();
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.startsWith('/areas')) return Promise.resolve({ data: mockAreas });
      if (url.includes('trazabilidad')) return Promise.resolve({ data: null });
      if (url.includes('requisitos_materiales')) return Promise.reject(new Error('fail'));
      return Promise.resolve({ data: [] });
    });

    renderComponent();

    await user.click(screen.getByText('OP-001'));
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /Requisitos/i }));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar los requisitos de materiales.');
    });
  });
});

// ── Tests: Registrar Lote ─────────────────────────────────────────────────────

describe('ManageOrdenesProduccion — Registrar Lote', () => {
  it('dado el diálogo de Lote sin código ni peso cuando se hace clic en Registrar Lote entonces muestra un toast de error y no hace POST', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByText('OP-001'));
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /^Lote$/i }));

    const btnRegistrar = await screen.findByRole('button', { name: /Registrar Lote/i });
    await user.click(btnRegistrar);

    expect(toastErrorMock).toHaveBeenCalledWith('El código del lote y el peso producido son requeridos.');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('dado un formulario de Lote completo cuando se hace clic en Registrar Lote entonces hace POST, muestra éxito y refresca los datos', async () => {
    const user = userEvent.setup();
    const props = renderComponent();
    (apiClient.post as Mock).mockResolvedValue({ data: {} });

    await user.click(screen.getByText('OP-001'));
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /^Lote$/i }));

    await screen.findByLabelText(/Código de Lote/i);
    await user.type(screen.getByLabelText(/Código de Lote/i), 'LOTE-1');
    await user.type(screen.getByLabelText(/Peso Neto Producido/i), '45');

    await user.click(screen.getByRole('button', { name: /Registrar Lote/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/ordenes-produccion/1/registrar-lote/',
        expect.objectContaining({ codigo_lote: 'LOTE-1', peso_neto_producido: '45' })
      );
    });
    expect(toastSuccessMock).toHaveBeenCalledWith('Lote de producción registrado exitosamente.');
    expect(props.onDataRefresh).toHaveBeenCalled();
  });

  it('dado que la API de registrar-lote falla cuando se envía el formulario entonces muestra el mensaje de error del backend', async () => {
    const user = userEvent.setup();
    renderComponent();
    (apiClient.post as Mock).mockRejectedValue({ response: { status: 400, data: { error: 'Máquina no disponible' } } });

    await user.click(screen.getByText('OP-001'));
    await waitFor(() => expect(getSheetContent()).toBeTruthy());

    await user.click(within(getSheetContent()).getByRole('button', { name: /^Lote$/i }));

    await screen.findByLabelText(/Código de Lote/i);
    await user.type(screen.getByLabelText(/Código de Lote/i), 'LOTE-1');
    await user.type(screen.getByLabelText(/Peso Neto Producido/i), '45');

    await user.click(screen.getByRole('button', { name: /Registrar Lote/i }));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Máquina no disponible');
    });
  });

  it('dado el menú de acciones de fila cuando se hace clic en Registrar Lote entonces abre el diálogo de Lote', async () => {
    const user = userEvent.setup();
    renderComponent();

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Registrar Lote/i }));

    expect(await screen.findByText(/Registrar Lote para OP: OP-001/i)).toBeInTheDocument();
  });

  it('dado el menú de acciones de fila cuando se hace clic en Ver Requisitos entonces abre el diálogo de Requisitos', async () => {
    const user = userEvent.setup();
    renderComponent();

    await openRowMenu(user, 0);
    await user.click(screen.getByRole('menuitem', { name: /Ver Requisitos/i }));

    expect(await screen.findByText(/Requisitos de Materiales para OP: OP-001/i)).toBeInTheDocument();
  });
});

// ── Tests: búsqueda ────────────────────────────────────────────────────────────

describe('ManageOrdenesProduccion — búsqueda', () => {
  it('dado un término de búsqueda que coincide con un código cuando se escribe entonces filtra la tabla, y al borrarlo reaparecen todas', async () => {
    const user = userEvent.setup();
    renderComponent();

    const searchInput = screen.getByPlaceholderText(/Buscar por código, producto/i);
    await user.type(searchInput, 'OP-002');

    await waitFor(() => {
      expect(screen.queryByText('OP-001')).not.toBeInTheDocument();
      expect(screen.getByText('OP-002')).toBeInTheDocument();
    });

    await user.clear(searchInput);

    await waitFor(() => {
      expect(screen.getByText('OP-001')).toBeInTheDocument();
      expect(screen.getByText('OP-002')).toBeInTheDocument();
    });
  });

  it('dado un filtro de estado activo cuando se selecciona "Todos los estados" entonces reaparecen todas las órdenes', async () => {
    const user = userEvent.setup();
    renderComponent();

    const comboboxes = screen.getAllByRole('combobox');
    await user.click(comboboxes[0]);
    await user.click(await screen.findByRole('option', { name: /Pendiente/i }));

    expect(screen.queryByText('OP-001')).not.toBeInTheDocument();

    await user.click(comboboxes[0]);
    await user.click(await screen.findByRole('option', { name: /Todos los estados/i }));

    await waitFor(() => {
      expect(screen.getByText('OP-001')).toBeInTheDocument();
      expect(screen.getByText('OP-002')).toBeInTheDocument();
    });
  });

  it('dado un filtro de máquina activo cuando se selecciona "Todas las máquinas" entonces reaparecen todas las órdenes', async () => {
    const user = userEvent.setup();
    renderComponent();

    const comboboxes = screen.getAllByRole('combobox');
    await user.click(comboboxes[1]);
    await user.click(await screen.findByRole('option', { name: /Jet 1/i }));

    expect(screen.queryByText('OP-002')).not.toBeInTheDocument();

    await user.click(comboboxes[1]);
    await user.click(await screen.findByRole('option', { name: /Todas las máquinas/i }));

    await waitFor(() => {
      expect(screen.getByText('OP-001')).toBeInTheDocument();
      expect(screen.getByText('OP-002')).toBeInTheDocument();
    });
  });
});

// ── Tests: estado de carga ────────────────────────────────────────────────────

describe('ManageOrdenesProduccion — estado de carga', () => {
  it('dado loading=true cuando renderiza entonces muestra filas Skeleton y el botón "Cargando Catálogos..." deshabilitado', () => {
    renderComponent({ loading: true });

    const btn = screen.getByRole('button', { name: /Cargando Catálogos/i });
    expect(btn).toBeDisabled();
    // 5 filas de skeleton en lugar de las órdenes reales
    expect(screen.queryByText('OP-001')).not.toBeInTheDocument();
  });
});

// ── Tests: paginación ──────────────────────────────────────────────────────────

const buildManyOrdenes = (count: number): OrdenProduccion[] =>
  Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    codigo: `OP-${(i + 1).toString().padStart(3, '0')}`,
    producto: 1,
    producto_nombre: 'Tela Algodón',
    formula_color: 1,
    formula_color_nombre: 'Rojo Pasión',
    peso_neto_requerido: 100,
    peso_producido: 0,
    estado: 'pendiente' as const,
    fecha_creacion: '2026-05-01',
    fecha_modificacion: '2026-05-01',
    sede: 1,
    sede_nombre: 'Quito',
    area: 1,
    maquina_asignada: 1,
    maquina_asignada_nombre: 'Jet 1',
    inventario_descontado: false,
    fecha_fin_planificada: '2099-05-10',
    prioridad: 'normal' as const,
  }));

describe('ManageOrdenesProduccion — paginación', () => {
  it('dado más de 20 órdenes cuando se hace clic en Siguiente entonces avanza a la página 2', async () => {
    const user = userEvent.setup();
    renderComponent({ ordenes: buildManyOrdenes(25) });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('OP-001')).toBeInTheDocument();
    expect(screen.queryByText('OP-021')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Siguiente/i }));

    await waitFor(() => {
      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    });
    expect(screen.getByText('OP-021')).toBeInTheDocument();
    expect(screen.queryByText('OP-001')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Anterior/i }));

    await waitFor(() => {
      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    });
  });

  it('dado el input "Ir a" cuando se escribe un número de página válido y se presiona Enter entonces navega a esa página', async () => {
    const user = userEvent.setup();
    renderComponent({ ordenes: buildManyOrdenes(25) });

    const pageInput = screen.getByDisplayValue('1');
    await user.clear(pageInput);
    await user.type(pageInput, '2{Enter}');

    await waitFor(() => {
      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    });
  });
});

// ── Tests: variantes de badges en el Sheet ────────────────────────────────────

describe('ManageOrdenesProduccion — badges de estado y prioridad en el Sheet', () => {
  const ordenFinalizadaBaja: OrdenProduccion = {
    ...mockOrdenes[0],
    id: 3,
    codigo: 'OP-003',
    estado: 'finalizada',
    prioridad: 'baja',
  };
  const ordenUrgente: OrdenProduccion = {
    ...mockOrdenes[1],
    id: 4,
    codigo: 'OP-004',
    prioridad: 'urgente',
  };

  it('dado una orden finalizada con prioridad baja cuando se abre el Sheet entonces muestra los badges "Finalizada" y "Baja"', async () => {
    const user = userEvent.setup();
    renderComponent({ ordenes: [ordenFinalizadaBaja] });

    await user.click(screen.getByText('OP-003'));
    const sheet = await waitFor(() => getSheetContent());

    expect(within(sheet).getByText('Finalizada')).toBeInTheDocument();
    expect(within(sheet).getByText('Baja')).toBeInTheDocument();
    // Una orden finalizada no debe ofrecer cambio de estado
    expect(within(sheet).queryByRole('button', { name: /Iniciar Proceso/i })).not.toBeInTheDocument();
    expect(within(sheet).queryByRole('button', { name: /Marcar como Finalizada/i })).not.toBeInTheDocument();
  });

  it('dado una orden con prioridad urgente cuando se abre el Sheet entonces muestra el badge "Urgente"', async () => {
    const user = userEvent.setup();
    renderComponent({ ordenes: [ordenUrgente] });

    await user.click(screen.getByText('OP-004'));
    const sheet = await waitFor(() => getSheetContent());

    expect(within(sheet).getByText('Urgente')).toBeInTheDocument();
  });
});

// ── Tests: campos adicionales del formulario de creación ──────────────────────

describe('ManageOrdenesProduccion — campos de fechas y observaciones', () => {
  it('dado fechas de inicio/fin y observaciones completadas cuando se crea la orden entonces se envían en el payload', async () => {
    const user = userEvent.setup();
    const props = renderComponent();

    await user.click(screen.getByRole('button', { name: /Nueva Orden/i }));
    await waitFor(() => expect(screen.getByText('Selecciona el área de destino')).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Código/i), 'OP-200');
    await user.type(screen.getByLabelText(/Peso Neto Requerido/i), '80');

    const dialog = getDialogContent();
    const comboboxes = within(dialog).getAllByRole('combobox');
    await user.click(comboboxes[0]);
    await user.click(await screen.findByRole('option', { name: 'Tintorería' }));

    const fechaInicio = screen.getByLabelText(/Fecha Inicio/i);
    const fechaFin = screen.getByLabelText(/Fecha Fin/i);
    await user.type(fechaInicio, '2026-08-01');
    await user.type(fechaFin, '2026-08-15');
    await user.type(screen.getByLabelText(/Observaciones/i), 'Entregar con urgencia');

    await user.click(screen.getByRole('button', { name: /^Crear$/i }));

    await waitFor(() => {
      expect(props.onOrdenCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          codigo: 'OP-200',
          fecha_inicio_planificada: '2026-08-01',
          fecha_fin_planificada: '2026-08-15',
          observaciones: 'Entregar con urgencia',
        })
      );
    });
  });
});
