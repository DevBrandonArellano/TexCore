import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageOrdenesProduccion } from './ManageOrdenesProduccion';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import { OrdenProduccion, Bodega, Maquina, Producto, FormulaColor, Sede, Area } from '../../lib/types';

// Mock ResizeObserver for Radix Dialogs
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

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
    maquina_asignada: 1,
    maquina_asignada_nombre: 'Jet 1',
    inventario_descontado: false,
    fecha_fin_planificada: '2026-05-10',
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
    maquina_asignada: 2,
    maquina_asignada_nombre: 'Jigger 1',
    inventario_descontado: false,
    fecha_fin_planificada: '2026-05-20',
  }
];

const mockMaquinas: Maquina[] = [
  { id: 1, nombre: 'Jet 1', capacidad_maxima: 150, eficiencia_ideal: 90, estado: 'operativa', area: 1 },
  { id: 2, nombre: 'Jigger 1', capacidad_maxima: 200, eficiencia_ideal: 85, estado: 'operativa', area: 1 }
];

const defaultProps = {
  ordenes: mockOrdenes,
  productos: [],
  formulas: [],
  sedes: [],
  maquinas: mockMaquinas,
  areas: [],
  bodegas: [],
  onOrdenCreate: vi.fn(),
  onOrdenUpdate: vi.fn(),
  onOrderStatusChange: vi.fn(),
  onOrdenDelete: vi.fn(),
  loading: false,
  onDataRefresh: vi.fn(),
};

describe('ManageOrdenesProduccion TDD Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () => render(
    <MemoryRouter initialEntries={['/']}>
      <ManageOrdenesProduccion {...defaultProps} />
    </MemoryRouter>
  );

  it('debe renderizar la lista de órdenes correctamente', () => {
    renderComponent();
    expect(screen.getByText('OP-001')).toBeInTheDocument();
    expect(screen.getByText('OP-002')).toBeInTheDocument();
    expect(screen.getByText('Jet 1')).toBeInTheDocument();
    expect(screen.getByText('Jigger 1')).toBeInTheDocument();
  });

  it('debe filtrar órdenes por estado', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const comboboxes = screen.getAllByRole('combobox');
    const statusFilter = comboboxes[0];
    await user.click(statusFilter);
    
    // Para interactuar con Select de Radix UI, usamos role 'option'
    const optionPendiente = await screen.findByRole('option', { name: /Pendiente/i });
    await user.click(optionPendiente);

    expect(screen.getByText('OP-002')).toBeInTheDocument();
    expect(screen.queryByText('OP-001')).not.toBeInTheDocument();
  });

  it('debe filtrar órdenes por máquina asignada', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    const comboboxes = screen.getAllByRole('combobox');
    const machineFilter = comboboxes[1];
    await user.click(machineFilter);
    
    const optionJet1 = await screen.findByRole('option', { name: /Jet 1/i });
    await user.click(optionJet1);

    expect(screen.getByText('OP-001')).toBeInTheDocument();
    expect(screen.queryByText('OP-002')).not.toBeInTheDocument();
  });
});
