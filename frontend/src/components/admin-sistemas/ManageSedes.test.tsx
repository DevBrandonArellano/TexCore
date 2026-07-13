import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageSedes } from './ManageSedes';
import { Sede } from '../../lib/types';

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastErrorMock(...args),
  },
}));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}>
      <div>{children}</div>
    </SelectCtx.Provider>
  ),
  SelectTrigger: ({ children, id }: any) => <div id={id}>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const SEDE_1: Sede = {
  id: 1,
  nombre: 'Sede Principal',
  location: 'Ciudad de México',
  status: 'activo',
};

const SEDE_2: Sede = {
  id: 2,
  nombre: 'Sede Norte',
  location: 'Monterrey',
  status: 'inactivo',
};

function renderComponent(overrides: Partial<React.ComponentProps<typeof ManageSedes>> = {}) {
  const onSedeCreate = vi.fn().mockResolvedValue(true);
  const onSedeUpdate = vi.fn().mockResolvedValue(true);
  const onSedeDelete = vi.fn().mockResolvedValue(undefined);
  const props = {
    sedes: [],
    onSedeCreate,
    onSedeUpdate,
    onSedeDelete,
    ...overrides,
  };
  const utils = render(<ManageSedes {...props} />);
  return { ...utils, onSedeCreate, onSedeUpdate, onSedeDelete };
}

describe('ManageSedes', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin sedes cuando carga entonces la tabla no muestra filas de datos', () => {
    renderComponent({ sedes: [] });
    expect(screen.getByText('Nombre')).toBeInTheDocument();
    expect(screen.queryByText('Sede Principal')).not.toBeInTheDocument();
  });

  it('dado sedes cargando cuando sedesLoading es true entonces muestra los esqueletos', () => {
    const { container } = renderComponent({ sedes: [], sedesLoading: true });
    expect(container.querySelectorAll('tbody tr')).toHaveLength(3);
  });

  it('dado sedes existentes cuando carga entonces las lista con su ubicacion y estado', () => {
    renderComponent({ sedes: [SEDE_1, SEDE_2] });
    expect(screen.getByText('Sede Principal')).toBeInTheDocument();
    expect(screen.getByText('Ciudad de México')).toBeInTheDocument();
    expect(screen.getByText('Activo')).toBeInTheDocument();
    expect(screen.getByText('Sede Norte')).toBeInTheDocument();
    expect(screen.getByText('Monterrey')).toBeInTheDocument();
    expect(screen.getByText('Inactivo')).toBeInTheDocument();
  });

  it('dado nueva sede cuando abre el dialogo entonces muestra el formulario vacio', async () => {
    renderComponent();
    await userEvent.click(screen.getByText('Nueva Sede'));

    expect(screen.getByText('Completa el formulario para crear una nueva sede')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('ej: Sede Principal')).toHaveValue('');
    expect(screen.getByPlaceholderText('ej: Ciudad de México')).toHaveValue('');
  });

  it('dado campos vacios cuando intenta guardar entonces muestra errores y no llama a crear', async () => {
    const { onSedeCreate } = renderComponent();
    await userEvent.click(screen.getByText('Nueva Sede'));
    await userEvent.click(screen.getByText('Crear Sede'));

    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(screen.getByText('El nombre es requerido')).toBeInTheDocument();
    expect(screen.getByText('La ubicación es requerida')).toBeInTheDocument();
    expect(onSedeCreate).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando crea una sede entonces envia el payload correcto y cierra el dialogo', async () => {
    const { onSedeCreate } = renderComponent();
    await userEvent.click(screen.getByText('Nueva Sede'));
    await userEvent.type(screen.getByPlaceholderText('ej: Sede Principal'), 'Sede Sur');
    await userEvent.type(screen.getByPlaceholderText('ej: Ciudad de México'), 'Guadalajara');
    await userEvent.click(screen.getByText('Crear Sede'));

    await waitFor(() =>
      expect(onSedeCreate).toHaveBeenCalledWith({
        nombre: 'Sede Sur',
        location: 'Guadalajara',
        status: 'activo',
      }),
    );
    await waitFor(() =>
      expect(
        screen.queryByText('Completa el formulario para crear una nueva sede'),
      ).not.toBeInTheDocument(),
    );
  });

  it('dado estado inactivo seleccionado cuando crea una sede entonces envia el status elegido', async () => {
    const { onSedeCreate } = renderComponent();
    await userEvent.click(screen.getByText('Nueva Sede'));
    await userEvent.type(screen.getByPlaceholderText('ej: Sede Principal'), 'Sede Este');
    await userEvent.type(screen.getByPlaceholderText('ej: Ciudad de México'), 'Puebla');
    await userEvent.click(screen.getByText('Inactivo'));
    await userEvent.click(screen.getByText('Crear Sede'));

    await waitFor(() =>
      expect(onSedeCreate).toHaveBeenCalledWith({
        nombre: 'Sede Este',
        location: 'Puebla',
        status: 'inactivo',
      }),
    );
  });

  it('dado editar una sede existente cuando abre el dialogo entonces precarga sus datos', async () => {
    renderComponent({ sedes: [SEDE_2] });
    const editButtons = screen.getAllByRole('button').filter((btn) => btn.querySelector('svg.lucide-pencil'));
    await userEvent.click(editButtons[0]);

    expect(screen.getByText('Modifica la información de la sede')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('ej: Sede Principal')).toHaveValue('Sede Norte');
    expect(screen.getByPlaceholderText('ej: Ciudad de México')).toHaveValue('Monterrey');
  });

  it('dado editar cuando guarda entonces usa el id de la sede para actualizar', async () => {
    const { onSedeUpdate } = renderComponent({ sedes: [SEDE_1] });
    const editButtons = screen.getAllByRole('button').filter((btn) => btn.querySelector('svg.lucide-pencil'));
    await userEvent.click(editButtons[0]);

    await userEvent.click(screen.getByText('Actualizar Sede'));

    await waitFor(() =>
      expect(onSedeUpdate).toHaveBeenCalledWith(1, {
        nombre: 'Sede Principal',
        location: 'Ciudad de México',
        status: 'activo',
      }),
    );
  });

  it('dado error al crear cuando onSedeCreate resuelve false entonces el dialogo permanece abierto', async () => {
    const onSedeCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ onSedeCreate });
    await userEvent.click(screen.getByText('Nueva Sede'));
    await userEvent.type(screen.getByPlaceholderText('ej: Sede Principal'), 'Sede Fallida');
    await userEvent.type(screen.getByPlaceholderText('ej: Ciudad de México'), 'Toluca');
    await userEvent.click(screen.getByText('Crear Sede'));

    await waitFor(() => expect(onSedeCreate).toHaveBeenCalled());
    expect(screen.getByText('Completa el formulario para crear una nueva sede')).toBeInTheDocument();
  });

  it('dado eliminar una sede cuando se hace click entonces llama a la API con el id correcto', async () => {
    const { onSedeDelete } = renderComponent({ sedes: [SEDE_1, SEDE_2] });
    const deleteButtons = screen.getAllByRole('button').filter((btn) => btn.querySelector('svg.lucide-trash2'));
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => expect(onSedeDelete).toHaveBeenCalledWith(1));
  });

  it('dado eliminacion en progreso cuando aun no resuelve entonces deshabilita los botones de eliminar', async () => {
    let resolveDelete: () => void = () => {};
    const onSedeDelete = vi.fn().mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveDelete = resolve;
        }),
    );
    renderComponent({ sedes: [SEDE_1, SEDE_2], onSedeDelete });
    const deleteButtons = screen.getAllByRole('button').filter((btn) => btn.querySelector('svg.lucide-trash2'));
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => expect(deleteButtons[1]).toBeDisabled());

    resolveDelete();
    await waitFor(() => expect(deleteButtons[1]).not.toBeDisabled());
  });

  it('dado cancelar cuando el dialogo esta abierto entonces lo cierra sin llamar a crear', async () => {
    const { onSedeCreate } = renderComponent();
    await userEvent.click(screen.getByText('Nueva Sede'));
    await userEvent.type(screen.getByPlaceholderText('ej: Sede Principal'), 'Descartada');
    await userEvent.click(screen.getByText('Cancelar'));

    expect(screen.queryByText('Completa el formulario para crear una nueva sede')).not.toBeInTheDocument();
    expect(onSedeCreate).not.toHaveBeenCalled();
  });
});
