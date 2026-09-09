import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OrdenDetalleSheet } from './OrdenDetalleSheet';
import type { OrdenProduccion } from '../../lib/types';

// Sin test propio hasta ahora.
vi.mock('../produccion/TrazabilidadProducto', () => ({
  TrazabilidadProducto: ({ ordenId }: any) => <div>trazabilidad-{ordenId}</div>,
}));

function baseOrden(overrides: Partial<OrdenProduccion> = {}): OrdenProduccion {
  return {
    id: 1, codigo: 'OP-001', estado: 'pendiente', prioridad: 'normal',
    peso_neto_requerido: 100, peso_producido: 0,
    sede: 1, area: 1, formula_color: null, bodega_quimicos: null,
    fecha_inicio_planificada: null, fecha_fin_planificada: null,
    fecha_creacion: null, observaciones: '', justificacion: '',
    inventario_descontado: false,
    ...overrides,
  } as OrdenProduccion;
}

function baseProps(overrides: Partial<React.ComponentProps<typeof OrdenDetalleSheet>> = {}) {
  return {
    open: true,
    onOpenChange: vi.fn(),
    orden: baseOrden(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onStatusChange: vi.fn(),
    onOpenLotDialog: vi.fn(),
    onOpenRequisitosDialog: vi.fn(),
    sedes: [{ id: 1, nombre: 'Sede Central' } as any],
    areas: [{ id: 1, nombre: 'Tintura' } as any],
    bodegas: [{ id: 1, nombre: 'Bodega Central' } as any],
    formulas: [{ id: 1, nombre_color: 'Rojo Carmín' } as any],
    ...overrides,
  };
}

describe('OrdenDetalleSheet', () => {
  it('dado orden nula cuando renderiza entonces no muestra nada', () => {
    const { container } = render(<OrdenDetalleSheet {...baseProps({ orden: null })} />);
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it('dado una orden con catalogos cuando renderiza entonces resuelve los nombres de sede, area, formula y bodega', () => {
    render(<OrdenDetalleSheet {...baseProps({
      orden: baseOrden({ sede: 1, area: 1, formula_color: 1, bodega_quimicos: 1 }),
    })} />);
    expect(screen.getByText('Sede Central')).toBeInTheDocument();
    expect(screen.getByText('Tintura')).toBeInTheDocument();
    expect(screen.getByText('Rojo Carmín')).toBeInTheDocument();
    expect(screen.getByText('Bodega Central')).toBeInTheDocument();
  });

  it('dado una orden sin catalogos resueltos cuando renderiza entonces muestra guiones', () => {
    render(<OrdenDetalleSheet {...baseProps({
      orden: baseOrden({ sede: 99, area: 99, formula_color: 99, bodega_quimicos: 99 }),
      sedes: [], areas: [], formulas: [], bodegas: [],
    })} />);
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('dado orden vencida cuando renderiza entonces muestra el badge Vencida', () => {
    const ayer = new Date();
    ayer.setDate(ayer.getDate() - 1);
    render(<OrdenDetalleSheet {...baseProps({
      orden: baseOrden({ estado: 'pendiente', fecha_fin_planificada: ayer.toISOString().split('T')[0] }),
    })} />);
    expect(screen.getByText('Vencida')).toBeInTheDocument();
  });

  it('dado orden que vence hoy cuando renderiza entonces muestra el badge Vence hoy', () => {
    const hoy = new Date().toISOString().split('T')[0];
    render(<OrdenDetalleSheet {...baseProps({
      orden: baseOrden({ estado: 'pendiente', fecha_fin_planificada: hoy }),
    })} />);
    expect(screen.getByText('Vence hoy')).toBeInTheDocument();
  });

  it('dado orden con inventario descontado cuando renderiza entonces muestra el badge de quimicos descontados', () => {
    render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ inventario_descontado: true }) })} />);
    expect(screen.getByText('✓ Químicos descontados')).toBeInTheDocument();
  });

  it('dado orden con observaciones y justificacion cuando renderiza entonces muestra la seccion de notas', () => {
    render(<OrdenDetalleSheet {...baseProps({
      orden: baseOrden({ observaciones: 'Nota operativa', justificacion: 'Justificación del cambio' }),
    })} />);
    expect(screen.getByText('Nota operativa')).toBeInTheDocument();
    expect(screen.getByText('Justificación del cambio')).toBeInTheDocument();
  });

  it('dado orden sin observaciones ni justificacion cuando renderiza entonces no muestra la seccion de notas', () => {
    render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ observaciones: '', justificacion: '' }) })} />);
    expect(screen.queryByText('Notas')).not.toBeInTheDocument();
  });

  it('dado orden pendiente cuando renderiza entonces muestra el boton Iniciar Proceso y no Marcar Finalizada', async () => {
    const onStatusChange = vi.fn();
    render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ estado: 'pendiente' }), onStatusChange })} />);
    expect(screen.queryByRole('button', { name: /Marcar como Finalizada/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Proceso/i }));
    expect(onStatusChange).toHaveBeenCalledWith(1, 'en_proceso');
  });

  it('dado orden en proceso cuando renderiza entonces muestra el boton Marcar como Finalizada', async () => {
    const onStatusChange = vi.fn();
    render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ estado: 'en_proceso' }), onStatusChange })} />);
    expect(screen.queryByRole('button', { name: /Iniciar Proceso/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Marcar como Finalizada/i }));
    expect(onStatusChange).toHaveBeenCalledWith(1, 'finalizada');
  });

  it('dado orden finalizada cuando renderiza entonces no muestra boton de cambio de estado y deshabilita Lote', () => {
    render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ estado: 'finalizada' }) })} />);
    expect(screen.queryByRole('button', { name: /Iniciar Proceso/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Marcar como Finalizada/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Lote/i })).toBeDisabled();
  });

  it('dado click en las acciones secundarias y editar/eliminar cuando se activan entonces llaman a sus handlers', async () => {
    const onOpenRequisitosDialog = vi.fn();
    const onOpenLotDialog = vi.fn();
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    render(<OrdenDetalleSheet {...baseProps({ onOpenRequisitosDialog, onOpenLotDialog, onEdit, onDelete })} />);

    await userEvent.click(screen.getByRole('button', { name: /Requisitos/i }));
    await userEvent.click(screen.getByRole('button', { name: /Lote/i }));
    await userEvent.click(screen.getByRole('button', { name: /Editar/i }));
    await userEvent.click(screen.getByRole('button', { name: /Eliminar/i }));

    expect(onOpenRequisitosDialog).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
    expect(onOpenLotDialog).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
    expect(onDelete).toHaveBeenCalledWith(1);
  });

  it('dado peso requerido en cero cuando calcula el porcentaje entonces no divide por cero', () => {
    render(<OrdenDetalleSheet {...baseProps({
      orden: baseOrden({ peso_neto_requerido: 0, peso_producido: 0 }),
    })} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });
});
