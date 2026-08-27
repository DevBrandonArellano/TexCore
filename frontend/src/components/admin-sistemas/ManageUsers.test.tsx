import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ManageUsers } from './ManageUsers';

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
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const SEDE_NORTE = { id: 1, nombre: 'Sede Norte', location: 'Bogotá', status: 'activo' };
const SEDE_SUR = { id: 2, nombre: 'Sede Sur', location: 'Cali', status: 'activo' };

const AREA_TINTORERIA = { id: 1, nombre: 'Tintorería', sede: 1 };
const AREA_CORTE = { id: 2, nombre: 'Corte', sede: 2 };

const GROUP_OPERARIO = { id: 1, name: 'operario' };
const GROUP_JEFE_AREA = { id: 2, name: 'jefe_area' };
const GROUP_ADMIN_SISTEMAS = { id: 3, name: 'admin_sistemas' };
const GROUP_JEFE_PLANTA = { id: 4, name: 'jefe_planta' };

const USER_OPERARIO = {
  id: 1,
  username: 'jdoe',
  first_name: 'Juan',
  last_name: 'Doe',
  email: 'jdoe@test.com',
  area: 1,
  sede: 1,
  groups: [1],
  permissions: [],
  bodegas_asignadas: [],
};

const USER_ADMIN_SISTEMAS = {
  id: 2,
  username: 'msmith',
  first_name: 'Maria',
  last_name: 'Smith',
  email: 'msmith@test.com',
  area: null,
  sede: null,
  groups: [3],
  permissions: [],
  bodegas_asignadas: [],
};

function renderComponent(props: Partial<{
  users: any[];
  sedes: any[];
  areas: any[];
  groups: any[];
  selectedSedeId?: string;
  onUserCreate: (data: any) => Promise<boolean>;
  onUserUpdate: (id: number, data: any) => Promise<boolean>;
  onUserDelete: (id: number) => void;
  loading: boolean;
}> = {}) {
  const defaults = {
    users: [],
    sedes: [SEDE_NORTE, SEDE_SUR],
    areas: [AREA_TINTORERIA, AREA_CORTE],
    groups: [GROUP_OPERARIO, GROUP_JEFE_AREA, GROUP_ADMIN_SISTEMAS, GROUP_JEFE_PLANTA],
    selectedSedeId: undefined,
    onUserCreate: vi.fn().mockResolvedValue(true),
    onUserUpdate: vi.fn().mockResolvedValue(true),
    onUserDelete: vi.fn(),
    loading: false,
  };
  const merged = { ...defaults, ...props };
  return {
    ...render(
      <MemoryRouter>
        <ManageUsers {...merged} />
      </MemoryRouter>,
    ),
    props: merged,
  };
}

function getRowFor(text: string) {
  const cell = screen.getByText(text);
  return cell.closest('tr') as HTMLElement;
}

function openCreateDialog() {
  return userEvent.click(screen.getByRole('button', { name: 'Nuevo Usuario' }));
}

describe('ManageUsers', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin usuarios cuando no esta cargando entonces no muestra filas de datos', () => {
    renderComponent({ users: [], loading: false });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(1);
  });

  it('dado loading cuando carga entonces muestra filas de skeleton', () => {
    const { container } = renderComponent({ users: [], loading: true });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(6);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('dado usuarios existentes cuando carga entonces los lista con su rol, sede y area', () => {
    renderComponent({ users: [USER_OPERARIO] });
    expect(screen.getByText('Juan Doe')).toBeInTheDocument();
    expect(screen.getByText('jdoe')).toBeInTheDocument();
    expect(screen.getByText('jdoe@test.com')).toBeInTheDocument();
    expect(screen.getByText('Operario')).toBeInTheDocument();
    expect(screen.getByText('Sede Norte')).toBeInTheDocument();
    expect(screen.getByText('Tintorería')).toBeInTheDocument();
  });

  it('dado usuario sin sede ni area asignada cuando lista entonces muestra guion', () => {
    renderComponent({ users: [USER_ADMIN_SISTEMAS] });
    const row = getRowFor('msmith');
    expect(within(row).getAllByText('-')).toHaveLength(2);
    expect(within(row).getByText('Administrador de Sistemas')).toBeInTheDocument();
  });

  it('dado usuario con un grupo que no existe en la lista de grupos cuando lista entonces muestra rol desconocido', () => {
    renderComponent({ users: [{ ...USER_OPERARIO, groups: [999] }] });
    expect(screen.getByText('Rol Desconocido')).toBeInTheDocument();
  });

  it('dado usuario sin grupos asignados cuando lista entonces muestra N/A', () => {
    renderComponent({ users: [{ ...USER_OPERARIO, groups: [] }] });
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('dado busqueda cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ users: [USER_OPERARIO, USER_ADMIN_SISTEMAS] });
    expect(screen.getByText('msmith')).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Buscar por nombre, usuario, email...'), 'jdoe');

    expect(screen.getByText('jdoe')).toBeInTheDocument();
    expect(screen.queryByText('msmith')).not.toBeInTheDocument();
  });

  it('dado mas de 20 usuarios cuando carga entonces pagina de 20 en 20', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      ...USER_OPERARIO,
      id: i + 1,
      username: `user${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ users: muchos });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('user001')).toBeInTheDocument();
    expect(screen.queryByText('user021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Siguiente'));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('user021')).toBeInTheDocument();
    expect(screen.queryByText('user001')).not.toBeInTheDocument();
  });

  it('dado mas de 20 usuarios cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      ...USER_OPERARIO, id: i + 1, username: `user${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ users: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado mas de 20 usuarios cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      ...USER_OPERARIO, id: i + 1, username: `user${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ users: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado nuevo usuario cuando guarda sin llenar campos requeridos entonces muestra errores de validacion', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate });

    await openCreateDialog();
    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    expect(screen.getByText('El usuario es requerido')).toBeInTheDocument();
    expect(screen.getByText('La contraseña es requerida')).toBeInTheDocument();
    expect(screen.getByText('El nombre es requerido')).toBeInTheDocument();
    expect(screen.getByText('El apellido es requerido')).toBeInTheDocument();
    expect(screen.getByText('El rol es requerido')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onUserCreate).not.toHaveBeenCalled();
  });

  it('dado rol operario cuando guarda sin seleccionar area entonces muestra error de area', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, selectedSedeId: '1' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Clave123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Usuario');
    await userEvent.click(within(dialog).getByText('Operario'));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    expect(screen.getByText('El área es requerida para este rol')).toBeInTheDocument();
    expect(screen.queryByText('La sede es requerida para este rol')).not.toBeInTheDocument();
    expect(onUserCreate).not.toHaveBeenCalled();
  });

  it('dado rol que requiere sede cuando no hay sedes disponibles entonces muestra error de sede', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, sedes: [] });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Clave123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Usuario');
    await userEvent.click(within(dialog).getByText('Jefe de Planta'));

    expect(within(dialog).getByText('Selecciona una sede en el menú lateral')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    expect(screen.getByText('La sede es requerida para este rol')).toBeInTheDocument();
    expect(onUserCreate).not.toHaveBeenCalled();
  });

  it('dado email con formato invalido cuando guarda entonces muestra error de email', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, selectedSedeId: '1' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Clave123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Usuario');
    await userEvent.type(within(dialog).getByLabelText('Email'), 'no-es-un-email');
    await userEvent.click(within(dialog).getByText('Jefe de Planta'));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    expect(screen.getByText('El email no es válido')).toBeInTheDocument();
    expect(onUserCreate).not.toHaveBeenCalled();
  });

  it('dado datos validos con rol jefe de planta cuando crea un usuario entonces envia el payload correcto', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, selectedSedeId: '2' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'nuser');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Secreta123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Usuario');
    await userEvent.type(within(dialog).getByLabelText('Email'), 'nuevo@test.com');
    await userEvent.click(within(dialog).getByText('Jefe de Planta'));

    expect(document.getElementById('sede')).toHaveTextContent('Sede Sur');

    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    await waitFor(() => expect(onUserCreate).toHaveBeenCalledWith({
      username: 'nuser',
      password: 'Secreta123',
      first_name: 'Nuevo',
      last_name: 'Usuario',
      email: 'nuevo@test.com',
      groups: [4],
      sede: 2,
      area: null,
    }));
  });

  it('dado datos validos con rol operario cuando crea un usuario entonces filtra el area por la sede y envia el payload correcto', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, selectedSedeId: '1' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'operario1');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Clave123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Ope');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Rario');
    await userEvent.click(within(dialog).getByText('Operario'));

    expect(within(dialog).getByText('Tintorería')).toBeInTheDocument();
    expect(within(dialog).queryByText('Corte')).not.toBeInTheDocument();

    await userEvent.click(within(dialog).getByText('Tintorería'));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    await waitFor(() => expect(onUserCreate).toHaveBeenCalledWith({
      username: 'operario1',
      password: 'Clave123',
      first_name: 'Ope',
      last_name: 'Rario',
      email: '',
      groups: [1],
      sede: 1,
      area: 1,
    }));
  });

  it('dado rol administrador de sistemas cuando abre el formulario entonces oculta los campos de sede y area', async () => {
    renderComponent({ selectedSedeId: '1' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.click(within(dialog).getByText('Administrador de Sistemas'));

    expect(within(dialog).queryByText(/^Sede/)).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/^Área/)).not.toBeInTheDocument();
  });

  it('dado rol administrador de sistemas cuando crea un usuario entonces igual envia la sede preseleccionada de forma oculta', async () => {
    // La sede se precarga al abrir el diálogo (para roles que la requieren) y el
    // estado no se limpia al elegir un rol que no la necesita: el payload la sigue
    // incluyendo aunque el campo esté oculto en la UI.
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, selectedSedeId: '1' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'admin1');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Clave123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Admin');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Sistemas');
    await userEvent.click(within(dialog).getByText('Administrador de Sistemas'));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    await waitFor(() => expect(onUserCreate).toHaveBeenCalledWith(expect.objectContaining({
      groups: [3],
      sede: 1,
      area: null,
    })));
  });

  it('dado creacion exitosa cuando la API responde true entonces cierra el dialogo y limpia el formulario', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, selectedSedeId: '2' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'nuser');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Secreta123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Usuario');
    await userEvent.click(within(dialog).getByText('Jefe de Planta'));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    await openCreateDialog();
    expect(within(screen.getByRole('dialog')).getByLabelText(/Usuario/)).toHaveValue('');
  });

  it('dado creacion fallida cuando la API responde false entonces mantiene el dialogo abierto', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ onUserCreate, selectedSedeId: '2' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'nuser');
    await userEvent.type(within(dialog).getByLabelText(/Contraseña/), 'Secreta123');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Nuevo');
    await userEvent.type(within(dialog).getByLabelText(/Apellido/), 'Usuario');
    await userEvent.click(within(dialog).getByText('Jefe de Planta'));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Usuario' }));

    await waitFor(() => expect(onUserCreate).toHaveBeenCalled());
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('dado editar un usuario existente cuando abre el dialogo entonces precarga sus datos sin la contraseña', async () => {
    renderComponent({ users: [USER_OPERARIO] });

    const row = getRowFor('jdoe');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    expect(screen.getByText('Editar Usuario')).toBeInTheDocument();
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByLabelText(/Usuario/)).toHaveValue('jdoe');
    expect(within(dialog).getByLabelText(/Nueva Contraseña/)).toHaveValue('');
    expect(within(dialog).getByLabelText(/Nombre/)).toHaveValue('Juan');
    expect(within(dialog).getByLabelText(/Apellido/)).toHaveValue('Doe');
    expect(within(dialog).getByLabelText('Email')).toHaveValue('jdoe@test.com');
    expect(document.getElementById('sede')).toHaveTextContent('Sede Norte');
  });

  it('dado editar un usuario sin cambiar la contraseña cuando guarda entonces no envia contraseña', async () => {
    const onUserUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ users: [USER_OPERARIO], onUserUpdate });

    const row = getRowFor('jdoe');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Usuario' }));

    await waitFor(() => expect(onUserUpdate).toHaveBeenCalled());
    const [id, payload] = onUserUpdate.mock.calls[0];
    expect(id).toBe(1);
    expect(payload.password).toBeUndefined();
    expect(payload).toEqual(expect.objectContaining({
      username: 'jdoe',
      first_name: 'Juan',
      last_name: 'Doe',
      email: 'jdoe@test.com',
      groups: [1],
      sede: 1,
      area: 1,
    }));
  });

  it('dado editar un usuario y escribir una nueva contraseña cuando guarda entonces la envia', async () => {
    const onUserUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ users: [USER_OPERARIO], onUserUpdate });

    const row = getRowFor('jdoe');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Nueva Contraseña/), 'NuevaClave123');
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Usuario' }));

    await waitFor(() => expect(onUserUpdate).toHaveBeenCalledWith(1, expect.objectContaining({
      password: 'NuevaClave123',
    })));
  });

  it('dado editar un usuario y cambiar su rol a administrador de sistemas cuando guarda entonces conserva la sede y area previas de forma oculta', async () => {
    // Documenta un comportamiento potencialmente riesgoso: al reasignar el rol de un
    // usuario a admin_sistemas, los campos de sede/área quedan ocultos en el formulario
    // pero su valor previo no se limpia y se sigue enviando en el payload.
    const onUserUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ users: [USER_OPERARIO], onUserUpdate });

    const row = getRowFor('jdoe');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);
    const dialog = screen.getByRole('dialog');
    await userEvent.click(within(dialog).getByText('Administrador de Sistemas'));

    expect(within(dialog).queryByText(/^Sede/)).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/^Área/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Usuario' }));

    await waitFor(() => expect(onUserUpdate).toHaveBeenCalledWith(1, expect.objectContaining({
      groups: [3],
      sede: 1,
      area: 1,
    })));
  });

  it('dado eliminar cuando se hace click en el boton de eliminar entonces llama a onUserDelete con el id', async () => {
    const onUserDelete = vi.fn();
    renderComponent({ users: [USER_OPERARIO], onUserDelete });

    const row = getRowFor('jdoe');
    const deleteButton = within(row).getAllByRole('button')[1];
    await userEvent.click(deleteButton);

    expect(onUserDelete).toHaveBeenCalledWith(1);
  });

  it('dado cancelar cuando se hace click entonces cierra el dialogo sin guardar', async () => {
    const onUserCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onUserCreate, selectedSedeId: '1' });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Usuario/), 'descartado');
    await userEvent.click(within(dialog).getByText('Cancelar'));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(onUserCreate).not.toHaveBeenCalled();
  });
});
