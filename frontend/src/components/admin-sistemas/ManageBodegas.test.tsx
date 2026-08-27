import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ManageBodegas } from './ManageBodegas';

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastErrorMock(...args),
  },
}));

const SEDE_NORTE = { id: 1, nombre: 'Sede Norte', location: 'Bogotá', status: 'activo' };
const SEDE_SUR = { id: 2, nombre: 'Sede Sur', location: 'Cali', status: 'activo' };

const USER_NORTE = {
  id: 1,
  username: 'jdoe',
  first_name: 'Juan',
  last_name: 'Doe',
  email: 'jdoe@test.com',
  area: null,
  sede: 1,
  groups: [],
  permissions: [],
  bodegas_asignadas: [],
};

const USER_SUR = {
  id: 2,
  username: 'msmith',
  first_name: 'Maria',
  last_name: 'Smith',
  email: 'msmith@test.com',
  area: null,
  sede: 2,
  groups: [],
  permissions: [],
  bodegas_asignadas: [],
};

const BODEGA_CENTRAL = { id: 1, nombre: 'Bodega Central', sede: 1, usuarios_asignados: [1] };
const BODEGA_SECUNDARIA = { id: 2, nombre: 'Bodega Secundaria', sede: 2, usuarios_asignados: [] };

function renderComponent(props: Partial<{
  bodegas: any[];
  sedes: any[];
  users: any[];
  selectedSedeId?: string;
  onBodegaCreate: (data: any) => Promise<boolean>;
  onBodegaUpdate: (id: number, data: any) => Promise<boolean>;
  onBodegaDelete: (id: number) => void;
  loading: boolean;
}> = {}) {
  const defaults = {
    bodegas: [],
    sedes: [SEDE_NORTE, SEDE_SUR],
    users: [USER_NORTE, USER_SUR],
    selectedSedeId: undefined,
    onBodegaCreate: vi.fn().mockResolvedValue(true),
    onBodegaUpdate: vi.fn().mockResolvedValue(true),
    onBodegaDelete: vi.fn(),
    loading: false,
  };
  const merged = { ...defaults, ...props };
  return {
    ...render(
      <MemoryRouter>
        <ManageBodegas {...merged} />
      </MemoryRouter>,
    ),
    props: merged,
  };
}

function getRowFor(text: string) {
  const cell = screen.getByText(text);
  return cell.closest('tr') as HTMLElement;
}

describe('ManageBodegas', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin bodegas cuando no esta cargando entonces no muestra filas de datos', () => {
    renderComponent({ bodegas: [], loading: false });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(1);
  });

  it('dado loading cuando carga entonces muestra filas de skeleton', () => {
    const { container } = renderComponent({ bodegas: [], loading: true });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(6);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('dado bodegas existentes cuando carga entonces las lista con su nombre y sede', () => {
    renderComponent({ bodegas: [BODEGA_CENTRAL, BODEGA_SECUNDARIA] });
    expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    expect(screen.getByText('Sede Norte')).toBeInTheDocument();
    expect(screen.getByText('Bodega Secundaria')).toBeInTheDocument();
    expect(screen.getByText('Sede Sur')).toBeInTheDocument();
  });

  it('dado busqueda por nombre cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ bodegas: [BODEGA_CENTRAL, BODEGA_SECUNDARIA] });
    expect(screen.getByText('Bodega Secundaria')).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Buscar por nombre o sede...'), 'Central');

    expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    expect(screen.queryByText('Bodega Secundaria')).not.toBeInTheDocument();
  });

  it('dado busqueda por sede cuando escribe en el buscador entonces filtra la lista por el nombre de la sede', async () => {
    renderComponent({ bodegas: [BODEGA_CENTRAL, BODEGA_SECUNDARIA] });

    await userEvent.type(screen.getByPlaceholderText('Buscar por nombre o sede...'), 'Sur');

    expect(screen.getByText('Bodega Secundaria')).toBeInTheDocument();
    expect(screen.queryByText('Bodega Central')).not.toBeInTheDocument();
  });

  it('dado mas de 20 bodegas cuando carga entonces pagina de 20 en 20', async () => {
    const muchas = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1,
      nombre: `Bodega ${String(i + 1).padStart(3, '0')}`,
      sede: 1,
      usuarios_asignados: [],
    }));
    renderComponent({ bodegas: muchas });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('Bodega 001')).toBeInTheDocument();
    expect(screen.queryByText('Bodega 021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Siguiente'));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('Bodega 021')).toBeInTheDocument();
    expect(screen.queryByText('Bodega 001')).not.toBeInTheDocument();
  });

  it('dado mas de 20 bodegas cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const muchas = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, nombre: `Bodega ${String(i + 1).padStart(3, '0')}`, sede: 1, usuarios_asignados: [],
    }));
    renderComponent({ bodegas: muchas });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado mas de 20 bodegas cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const muchas = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, nombre: `Bodega ${String(i + 1).padStart(3, '0')}`, sede: 1, usuarios_asignados: [],
    }));
    renderComponent({ bodegas: muchas });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado nueva bodega sin sedes disponibles cuando guarda sin llenar campos entonces muestra errores de validacion', async () => {
    const onBodegaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ sedes: [], onBodegaCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Bodega' }));

    expect(screen.getByText('El nombre es requerido')).toBeInTheDocument();
    expect(screen.getAllByText('Selecciona una sede en el menú lateral').length).toBeGreaterThanOrEqual(2);
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onBodegaCreate).not.toHaveBeenCalled();
  });

  it('dado sede seleccionada en el menu lateral cuando abre el formulario entonces la asigna automaticamente', async () => {
    renderComponent({ selectedSedeId: '2' });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));

    expect(document.getElementById('sede')).toHaveTextContent('Sede Sur');
  });

  it('dado datos validos cuando crea una bodega entonces envia el payload correcto', async () => {
    const onBodegaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ selectedSedeId: '2', onBodegaCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Bodega Nueva');
    await userEvent.click(screen.getByLabelText(/Maria Smith \(msmith\)/));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Bodega' }));

    await waitFor(() => expect(onBodegaCreate).toHaveBeenCalledWith({
      nombre: 'Bodega Nueva',
      sede: 2,
      usuarios_asignados: [2],
      _justificacion_auditoria: '',
    }));
  });

  it('dado usuarios de otra sede cuando abre el formulario entonces solo lista los usuarios de la sede asignada', async () => {
    renderComponent({ selectedSedeId: '2' });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));

    expect(screen.getByLabelText(/Maria Smith \(msmith\)/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Juan Doe \(jdoe\)/)).not.toBeInTheDocument();
  });

  it('dado sede sin usuarios cuando abre el formulario entonces muestra mensaje de que no hay usuarios', async () => {
    renderComponent({ sedes: [SEDE_NORTE], users: [USER_SUR] });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));

    expect(screen.getByText('No hay usuarios en esta sede.')).toBeInTheDocument();
  });

  it('dado creacion exitosa cuando la API responde true entonces cierra el dialogo y limpia el formulario', async () => {
    const onBodegaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ selectedSedeId: '1', onBodegaCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Bodega Nueva');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Bodega' }));

    await waitFor(() => expect(screen.queryByText('Completa el formulario para crear una nueva bodega')).not.toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));
    expect(screen.getByLabelText(/Nombre/)).toHaveValue('');
  });

  it('dado creacion fallida cuando la API responde false entonces mantiene el dialogo abierto', async () => {
    const onBodegaCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ selectedSedeId: '1', onBodegaCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Bodega Nueva');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Bodega' }));

    await waitFor(() => expect(onBodegaCreate).toHaveBeenCalled());
    expect(screen.getByText('Completa el formulario para crear una nueva bodega')).toBeInTheDocument();
  });

  it('dado editar una bodega existente cuando abre el dialogo entonces precarga sus datos', async () => {
    renderComponent({ bodegas: [BODEGA_CENTRAL] });

    const row = getRowFor('Bodega Central');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    expect(screen.getByText('Editar Bodega')).toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre/)).toHaveValue('Bodega Central');
    expect(document.getElementById('sede')).toHaveTextContent('Sede Norte');
    expect(screen.getByLabelText(/Juan Doe \(jdoe\)/)).toBeChecked();
    expect(screen.getByLabelText(/Justificación de auditoría/)).toBeInTheDocument();
  });

  it('dado editar sin justificacion cuando guarda entonces muestra error de validacion', async () => {
    const onBodegaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ bodegas: [BODEGA_CENTRAL], onBodegaUpdate });

    const row = getRowFor('Bodega Central');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Bodega' }));

    expect(screen.getByText('La justificación es obligatoria para editar la bodega')).toBeInTheDocument();
    expect(onBodegaUpdate).not.toHaveBeenCalled();
  });

  it('dado editar con justificacion cuando guarda entonces llama onBodegaUpdate con el id y los datos', async () => {
    const onBodegaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ bodegas: [BODEGA_CENTRAL], onBodegaUpdate });

    const row = getRowFor('Bodega Central');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    await userEvent.clear(screen.getByLabelText(/Nombre/));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Bodega Central Renovada');
    await userEvent.type(screen.getByLabelText(/Justificación de auditoría/), 'Reorganización de bodega por capacidad');
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Bodega' }));

    await waitFor(() => expect(onBodegaUpdate).toHaveBeenCalledWith(1, {
      nombre: 'Bodega Central Renovada',
      sede: 1,
      usuarios_asignados: [1],
      _justificacion_auditoria: 'Reorganización de bodega por capacidad',
    }));
  });

  it('dado desmarcar un usuario asignado cuando edita y guarda entonces envia la lista actualizada de usuarios', async () => {
    const onBodegaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ bodegas: [BODEGA_CENTRAL], onBodegaUpdate });

    const row = getRowFor('Bodega Central');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    await userEvent.click(screen.getByLabelText(/Juan Doe \(jdoe\)/));
    await userEvent.type(screen.getByLabelText(/Justificación de auditoría/), 'Cambio de bodeguero asignado');
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Bodega' }));

    await waitFor(() => expect(onBodegaUpdate).toHaveBeenCalledWith(1, expect.objectContaining({
      usuarios_asignados: [],
    })));
  });

  it('dado eliminar cuando se hace click en el boton de eliminar entonces llama a onBodegaDelete con el id', async () => {
    const onBodegaDelete = vi.fn();
    renderComponent({ bodegas: [BODEGA_CENTRAL], onBodegaDelete });

    const row = getRowFor('Bodega Central');
    const deleteButton = within(row).getAllByRole('button')[1];
    await userEvent.click(deleteButton);

    expect(onBodegaDelete).toHaveBeenCalledWith(1);
  });

  it('dado cancelar cuando se hace click entonces cierra el dialogo sin guardar', async () => {
    const onBodegaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ selectedSedeId: '1', onBodegaCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nueva Bodega' }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Bodega Descartada');
    await userEvent.click(screen.getByText('Cancelar'));

    await waitFor(() => expect(screen.queryByText('Completa el formulario para crear una nueva bodega')).not.toBeInTheDocument());
    expect(onBodegaCreate).not.toHaveBeenCalled();
  });
});
