import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OrdenDetalleSheet } from './OrdenDetalleSheet';
import type { OrdenProduccion } from '../../lib/types';

vi.mock('../produccion/TrazabilidadProducto', () => ({
  TrazabilidadProducto: ({ ordenId }: any) => <div>trazabilidad-{ordenId}</div>,
}));

const mockPatch = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { patch: (...args: any[]) => mockPatch(...args) },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
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
  beforeEach(() => {
    mockPatch.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

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

  // --- Baño de Tintura: litros_bano y relacion_bano (spec 2026-09-24 D3) ---
  describe('Baño de Tintura', () => {
    it('dado una orden sin formula cuando renderiza entonces no muestra la seccion de bano', () => {
      render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ formula_color: null }) })} />);
      expect(screen.queryByLabelText('Litros de Baño')).not.toBeInTheDocument();
    });

    it('dado una orden con formula cuando renderiza entonces muestra litros y relacion precargados', () => {
      render(<OrdenDetalleSheet {...baseProps({
        orden: baseOrden({ formula_color: 1, litros_bano: '1000.00', relacion_bano: '10.0000' }),
      })} />);
      expect(screen.getByLabelText('Litros de Baño')).toHaveValue(1000);
      expect(screen.getByText('1:10.00')).toBeInTheDocument();
    });

    it('dado una orden con formula sin litros aun cuando renderiza entonces indica que no se ha calculado', () => {
      render(<OrdenDetalleSheet {...baseProps({
        orden: baseOrden({ formula_color: 1, litros_bano: null, relacion_bano: null }),
      })} />);
      expect(screen.getByLabelText('Litros de Baño')).toHaveValue(null);
      expect(screen.getByText('Aún no calculada')).toBeInTheDocument();
    });

    it('dado litros invalidos cuando hace click en guardar entonces muestra un error y no llama al backend', async () => {
      render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ formula_color: 1 }) })} />);
      await userEvent.clear(screen.getByLabelText('Litros de Baño'));
      await userEvent.type(screen.getByLabelText('Litros de Baño'), '0');
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      expect(toastErrorMock).toHaveBeenCalledWith('Ingresa un número de litros mayor a cero.');
      expect(mockPatch).not.toHaveBeenCalled();
    });

    it('dado litros validos sin quimicos descontados cuando guarda entonces hace PATCH sin pedir justificacion', async () => {
      mockPatch.mockResolvedValueOnce({ data: {} });
      const onDataRefresh = vi.fn();
      render(<OrdenDetalleSheet {...baseProps({
        orden: baseOrden({ id: 5, formula_color: 1, inventario_descontado: false }), onDataRefresh,
      })} />);

      await userEvent.clear(screen.getByLabelText('Litros de Baño'));
      await userEvent.type(screen.getByLabelText('Litros de Baño'), '860');
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/ordenes-produccion/5/', { litros_bano: 860 }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Litros de baño actualizados.');
      expect(onDataRefresh).toHaveBeenCalled();
    });

    it('dado quimicos ya descontados cuando guarda sin justificacion entonces no llama al backend', async () => {
      vi.spyOn(window, 'prompt').mockReturnValue('');
      render(<OrdenDetalleSheet {...baseProps({
        orden: baseOrden({ formula_color: 1, inventario_descontado: true }),
      })} />);

      await userEvent.clear(screen.getByLabelText('Litros de Baño'));
      await userEvent.type(screen.getByLabelText('Litros de Baño'), '900');
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      expect(toastErrorMock).toHaveBeenCalledWith(
        'La justificación es obligatoria para modificar una orden con químicos descontados.');
      expect(mockPatch).not.toHaveBeenCalled();
    });

    it('dado quimicos ya descontados cuando guarda con justificacion entonces envia litros y justificacion', async () => {
      vi.spyOn(window, 'prompt').mockReturnValue('Ajuste solicitado por el ingeniero');
      mockPatch.mockResolvedValueOnce({ data: {} });
      render(<OrdenDetalleSheet {...baseProps({
        orden: baseOrden({ id: 7, formula_color: 1, inventario_descontado: true }),
      })} />);

      await userEvent.clear(screen.getByLabelText('Litros de Baño'));
      await userEvent.type(screen.getByLabelText('Litros de Baño'), '900');
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/ordenes-produccion/7/', {
        litros_bano: 900, justificacion: 'Ajuste solicitado por el ingeniero',
      }));
    });

    it('dado el backend rechaza la peticion cuando guarda entonces muestra el detalle del error', async () => {
      mockPatch.mockRejectedValueOnce({ response: { data: { litros_bano: ['supera el volumen de la máquina'] } } });
      render(<OrdenDetalleSheet {...baseProps({ orden: baseOrden({ formula_color: 1 }) })} />);

      await userEvent.clear(screen.getByLabelText('Litros de Baño'));
      await userEvent.type(screen.getByLabelText('Litros de Baño'), '5000');
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith(
        JSON.stringify({ litros_bano: ['supera el volumen de la máquina'] })));
    });
  });
});
