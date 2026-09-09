import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageAreas } from './ManageAreas';
import { Area, Sede } from '../../lib/types';

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: vi.fn(),
  },
}));

const SEDE_1: Sede = { id: 1, nombre: 'Sede Norte', location: 'Bogotá', status: 'activo' };
const SEDE_2: Sede = { id: 2, nombre: 'Sede Sur', location: 'Medellín', status: 'activo' };
const AREA_1: Area = { id: 10, nombre: 'Producción A', sede: 1 };

function renderComponent(overrides: Partial<React.ComponentProps<typeof ManageAreas>> = {}) {
  const props: React.ComponentProps<typeof ManageAreas> = {
    areas: [],
    sedes: [SEDE_1, SEDE_2],
    selectedSedeId: '1',
    onAreaCreate: vi.fn().mockResolvedValue(true),
    onAreaUpdate: vi.fn().mockResolvedValue(true),
    onAreaDelete: vi.fn(),
    loading: false,
    ...overrides,
  };
  const view = render(<ManageAreas {...props} />);
  return { ...view, props };
}

describe('ManageAreas', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin areas cuando no esta cargando entonces la tabla no muestra filas de datos', () => {
    renderComponent({ areas: [] });
    expect(screen.getAllByRole('row')).toHaveLength(1);
  });

  it('dado loading true cuando carga entonces muestra filas esqueleto', () => {
    renderComponent({ loading: true, areas: [] });
    expect(screen.getAllByRole('row')).toHaveLength(5);
  });

  it('dado areas existentes cuando carga entonces las lista con su sede y ubicacion', () => {
    renderComponent({ areas: [AREA_1] });
    expect(screen.getByText('Producción A')).toBeInTheDocument();
    expect(screen.getByText('Sede Norte')).toBeInTheDocument();
    expect(screen.getByText('Bogotá')).toBeInTheDocument();
  });

  it('dado area sin sede coincidente cuando carga entonces muestra N/A', () => {
    renderComponent({ areas: [{ id: 11, nombre: 'Huérfana', sede: 999 }] });
    expect(screen.getAllByText('N/A')).toHaveLength(2);
  });

  it('dado boton nueva area cuando se abre el dialogo entonces asigna la sede segun selectedSedeId', async () => {
    renderComponent({ areas: [], selectedSedeId: '2' });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    expect(screen.getByPlaceholderText('ej: Producción A')).toBeInTheDocument();
    expect(screen.getByText('Sede Sur')).toBeInTheDocument();
  });

  it('dado selectedSedeId invalido cuando abre el dialogo para crear entonces usa la primera sede', async () => {
    renderComponent({ areas: [], selectedSedeId: '999' });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    expect(screen.getByText('Sede Norte')).toBeInTheDocument();
  });

  it('dado sin sedes disponibles cuando abre el dialogo para crear entonces no puede autoasignar una sede', async () => {
    renderComponent({ areas: [], sedes: [] });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    expect(screen.getByText('Selecciona una sede en el menú lateral')).toBeInTheDocument();
  });

  it('dado sin sedes disponibles cuando intenta guardar sin sede entonces muestra el error de sede requerida', async () => {
    const onAreaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ areas: [], sedes: [], onAreaCreate });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    await userEvent.type(screen.getByPlaceholderText('ej: Producción A'), 'Área nueva');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Área' }));

    await waitFor(() => expect(screen.getAllByText('Selecciona una sede en el menú lateral').length).toBeGreaterThanOrEqual(2));
    expect(onAreaCreate).not.toHaveBeenCalled();
  });

  it('dado nueva area sin nombre cuando intenta guardar entonces muestra error y no llama onAreaCreate', async () => {
    const onAreaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ areas: [], onAreaCreate });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Área' }));

    expect(await screen.findByText('El nombre es requerido')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onAreaCreate).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando crea el area entonces llama onAreaCreate con el payload correcto y cierra el dialogo', async () => {
    const onAreaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ areas: [], selectedSedeId: '1', onAreaCreate });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    await userEvent.type(screen.getByPlaceholderText('ej: Producción A'), 'Teñido');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Área' }));

    await waitFor(() => expect(onAreaCreate).toHaveBeenCalledWith({ nombre: 'Teñido', sede: 1 }));
    await waitFor(() => expect(screen.queryByPlaceholderText('ej: Producción A')).not.toBeInTheDocument());
  });

  it('dado onAreaCreate falla cuando intenta crear entonces el dialogo permanece abierto', async () => {
    const onAreaCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ areas: [], onAreaCreate });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    await userEvent.type(screen.getByPlaceholderText('ej: Producción A'), 'Teñido');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Área' }));

    await waitFor(() => expect(onAreaCreate).toHaveBeenCalled());
    expect(screen.getByPlaceholderText('ej: Producción A')).toBeInTheDocument();
  });

  it('dado editar un area existente cuando abre el dialogo entonces precarga sus datos', async () => {
    renderComponent({ areas: [AREA_1] });
    const dataRow = screen.getAllByRole('row')[1];
    const [editButton] = within(dataRow).getAllByRole('button');
    await userEvent.click(editButton);

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText('Modifica la información del área')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('ej: Producción A')).toHaveValue('Producción A');
    expect(within(dialog).getByText('Sede Norte')).toBeInTheDocument();
  });

  it('dado editar cuando guarda entonces llama onAreaUpdate con el id y el payload correcto', async () => {
    const onAreaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ areas: [AREA_1], onAreaUpdate });
    const dataRow = screen.getAllByRole('row')[1];
    const [editButton] = within(dataRow).getAllByRole('button');
    await userEvent.click(editButton);

    const nombreInput = screen.getByPlaceholderText('ej: Producción A');
    await userEvent.clear(nombreInput);
    await userEvent.type(nombreInput, 'Producción B');
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Área' }));

    await waitFor(() =>
      expect(onAreaUpdate).toHaveBeenCalledWith(10, { nombre: 'Producción B', sede: 1 }),
    );
    await waitFor(() => expect(screen.queryByPlaceholderText('ej: Producción A')).not.toBeInTheDocument());
  });

  it('dado dialogo abierto cuando se cancela entonces se cierra sin llamar a onAreaCreate', async () => {
    const onAreaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ areas: [], onAreaCreate });
    await userEvent.click(screen.getByRole('button', { name: /Nueva Área/i }));
    await userEvent.type(screen.getByPlaceholderText('ej: Producción A'), 'Teñido');
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => expect(screen.queryByPlaceholderText('ej: Producción A')).not.toBeInTheDocument());
    expect(onAreaCreate).not.toHaveBeenCalled();
  });

  it('dado eliminar cuando se hace click en el boton eliminar entonces llama onAreaDelete con el id', async () => {
    const onAreaDelete = vi.fn();
    renderComponent({ areas: [AREA_1], onAreaDelete });
    const dataRow = screen.getAllByRole('row')[1];
    const [, deleteButton] = within(dataRow).getAllByRole('button');
    await userEvent.click(deleteButton);

    expect(onAreaDelete).toHaveBeenCalledWith(10);
  });
});
