import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageOrdenesProduccion } from './ManageOrdenesProduccion';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import { OrdenProduccion, Maquina, Area } from '../../lib/types';

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
