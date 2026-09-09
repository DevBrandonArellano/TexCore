import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ManageClientes } from './ManageClientes';
import { Cliente } from '../../lib/types';

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: vi.fn(),
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

const CLIENTE_1: Cliente = {
  id: 1,
  ruc_cedula: '0102030405',
  nombre_razon_social: 'Textiles Andinos SA',
  direccion_envio: 'Av. Amazonas 123',
  nivel_precio: 'normal',
  tiene_beneficio: false,
  saldo_pendiente: 0,
  limite_credito: 5000,
  plazo_credito_dias: 30,
  is_active: true,
};

const CLIENTE_2: Cliente = {
  id: 2,
  ruc_cedula: '0607080901',
  nombre_razon_social: 'Comercial Mayorista Ltda',
  direccion_envio: 'Calle 10 y Guayas',
  nivel_precio: 'mayorista',
  tiene_beneficio: true,
  saldo_pendiente: 100,
  limite_credito: 20000,
  plazo_credito_dias: 60,
  is_active: true,
};

function renderComponent(props: Partial<{
  clientes: Cliente[];
  onClienteCreate: (data: any) => Promise<boolean>;
  onClienteUpdate: (id: number, data: any) => Promise<boolean>;
  onClienteDelete: (id: number) => void;
  loading: boolean;
}> = {}) {
  const defaults = {
    clientes: [] as Cliente[],
    onClienteCreate: vi.fn().mockResolvedValue(true),
    onClienteUpdate: vi.fn().mockResolvedValue(true),
    onClienteDelete: vi.fn(),
    loading: false,
  };
  const merged = { ...defaults, ...props };
  return {
    ...render(
      <MemoryRouter>
        <ManageClientes {...merged} />
      </MemoryRouter>,
    ),
    props: merged,
  };
}

function getRowFor(text: string) {
  return screen.getByText(text).closest('tr') as HTMLElement;
}

describe('ManageClientes', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin clientes cuando no esta cargando entonces no muestra filas de datos', () => {
    renderComponent({ clientes: [] });
    expect(screen.getAllByRole('row')).toHaveLength(1);
    expect(screen.getByText('Página 1 de 1')).toBeInTheDocument();
  });

  it('dado loading true cuando carga entonces muestra filas de esqueleto', () => {
    renderComponent({ clientes: [], loading: true });
    expect(screen.getAllByRole('row')).toHaveLength(6);
  });

  it('dado clientes existentes cuando carga entonces los lista con sus datos', () => {
    renderComponent({ clientes: [CLIENTE_1, CLIENTE_2] });
    expect(screen.getByText(CLIENTE_1.ruc_cedula)).toBeInTheDocument();
    expect(screen.getByText(CLIENTE_1.nombre_razon_social)).toBeInTheDocument();
    expect(screen.getByText(CLIENTE_1.direccion_envio)).toBeInTheDocument();
    expect(screen.getByText('normal')).toBeInTheDocument();
    expect(screen.getByText(CLIENTE_2.nombre_razon_social)).toBeInTheDocument();
    expect(screen.getByText('mayorista')).toBeInTheDocument();
  });

  it('dado nuevo cliente cuando intenta guardar sin completar campos entonces muestra errores y no llama a onClienteCreate', async () => {
    const onClienteCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onClienteCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Cliente' }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Cliente' }));

    expect(screen.getByText('El RUC/Cédula es requerido')).toBeInTheDocument();
    expect(screen.getByText('El Nombre/Razón Social es requerido')).toBeInTheDocument();
    expect(screen.getByText('La dirección es requerida')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onClienteCreate).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando crea un cliente entonces llama a onClienteCreate con el payload correcto', async () => {
    const onClienteCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onClienteCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Cliente' }));
    await userEvent.type(screen.getByLabelText(/RUC\/Cédula/), '0102030405');
    await userEvent.type(screen.getByLabelText(/Nombre \/ Razón Social/), 'Textiles Andinos SA');
    await userEvent.type(screen.getByLabelText(/Dirección de Envío/), 'Av. Amazonas 123');
    await userEvent.click(screen.getByText('Mayorista'));
    await userEvent.clear(screen.getByLabelText(/Límite de Crédito/));
    await userEvent.type(screen.getByLabelText(/Límite de Crédito/), '5000');
    await userEvent.clear(screen.getByLabelText(/Plazo Crédito/));
    await userEvent.type(screen.getByLabelText(/Plazo Crédito/), '30');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Cliente' }));

    await waitFor(() => expect(onClienteCreate).toHaveBeenCalledWith({
      ruc_cedula: '0102030405',
      nombre_razon_social: 'Textiles Andinos SA',
      direccion_envio: 'Av. Amazonas 123',
      nivel_precio: 'mayorista',
      limite_credito: 5000,
      plazo_credito_dias: 30,
      _justificacion_auditoria: '',
    }));
    await waitFor(() => expect(screen.queryByLabelText(/RUC\/Cédula/)).not.toBeInTheDocument());
  });

  it('dado creacion fallida cuando la API responde false entonces mantiene el dialogo abierto', async () => {
    const onClienteCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ onClienteCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Cliente' }));
    await userEvent.type(screen.getByLabelText(/RUC\/Cédula/), '0102030405');
    await userEvent.type(screen.getByLabelText(/Nombre \/ Razón Social/), 'Textiles Andinos SA');
    await userEvent.type(screen.getByLabelText(/Dirección de Envío/), 'Av. Amazonas 123');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Cliente' }));

    await waitFor(() => expect(onClienteCreate).toHaveBeenCalled());
    expect(screen.getByLabelText(/RUC\/Cédula/)).toBeInTheDocument();
  });

  it('dado editar un cliente existente cuando abre el dialogo entonces precarga sus datos', async () => {
    renderComponent({ clientes: [CLIENTE_1] });
    const row = getRowFor(CLIENTE_1.ruc_cedula);
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    expect(screen.getByText('Editar Cliente')).toBeInTheDocument();
    expect(screen.getByLabelText(/RUC\/Cédula/)).toHaveValue(CLIENTE_1.ruc_cedula);
    expect(screen.getByLabelText(/Nombre \/ Razón Social/)).toHaveValue(CLIENTE_1.nombre_razon_social);
    expect(screen.getByLabelText(/Dirección de Envío/)).toHaveValue(CLIENTE_1.direccion_envio);
    expect(screen.getByLabelText(/Límite de Crédito/)).toHaveValue(CLIENTE_1.limite_credito);
    expect(screen.getByLabelText(/Plazo Crédito/)).toHaveValue(CLIENTE_1.plazo_credito_dias);
    expect(screen.getByLabelText(/Justificación del Cambio/)).toHaveValue('');
  });

  it('dado editar un cliente cuando guarda sin justificacion entonces muestra error y no llama a onClienteUpdate', async () => {
    const onClienteUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ clientes: [CLIENTE_1], onClienteUpdate });
    const row = getRowFor(CLIENTE_1.ruc_cedula);
    await userEvent.click(within(row).getAllByRole('button')[0]);

    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Cliente' }));

    expect(screen.getByText('La justificación es obligatoria para editar datos críticos')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onClienteUpdate).not.toHaveBeenCalled();
  });

  it('dado editar cuando completa la justificacion y guarda entonces llama a onClienteUpdate con el id y el payload correcto', async () => {
    const onClienteUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ clientes: [CLIENTE_1], onClienteUpdate });
    const row = getRowFor(CLIENTE_1.ruc_cedula);
    await userEvent.click(within(row).getAllByRole('button')[0]);

    const nombreInput = screen.getByLabelText(/Nombre \/ Razón Social/);
    await userEvent.clear(nombreInput);
    await userEvent.type(nombreInput, 'Textiles Andinos SA Actualizado');
    await userEvent.type(screen.getByLabelText(/Justificación del Cambio/), 'Actualizacion de datos de contacto');
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Cliente' }));

    await waitFor(() => expect(onClienteUpdate).toHaveBeenCalledWith(CLIENTE_1.id, {
      ruc_cedula: CLIENTE_1.ruc_cedula,
      nombre_razon_social: 'Textiles Andinos SA Actualizado',
      direccion_envio: CLIENTE_1.direccion_envio,
      nivel_precio: CLIENTE_1.nivel_precio,
      limite_credito: CLIENTE_1.limite_credito,
      plazo_credito_dias: CLIENTE_1.plazo_credito_dias,
      _justificacion_auditoria: 'Actualizacion de datos de contacto',
    }));
    await waitFor(() => expect(screen.queryByText('Editar Cliente')).not.toBeInTheDocument());
  });

  it('dado dialogo abierto cuando se cancela entonces se cierra sin llamar a onClienteCreate', async () => {
    const onClienteCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onClienteCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Cliente' }));
    await userEvent.type(screen.getByLabelText(/RUC\/Cédula/), '9999999999');
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => expect(screen.queryByLabelText(/RUC\/Cédula/)).not.toBeInTheDocument());
    expect(onClienteCreate).not.toHaveBeenCalled();
  });

  it('dado eliminar cuando hace click en el boton eliminar entonces llama a onClienteDelete con el id', async () => {
    const onClienteDelete = vi.fn();
    renderComponent({ clientes: [CLIENTE_1], onClienteDelete });
    const row = getRowFor(CLIENTE_1.ruc_cedula);
    await userEvent.click(within(row).getAllByRole('button')[1]);

    expect(onClienteDelete).toHaveBeenCalledWith(CLIENTE_1.id);
  });

  it('dado un termino de busqueda cuando escribe entonces filtra la lista por ruc o nombre', async () => {
    renderComponent({ clientes: [CLIENTE_1, CLIENTE_2] });
    expect(screen.getByText(CLIENTE_1.nombre_razon_social)).toBeInTheDocument();
    expect(screen.getByText(CLIENTE_2.nombre_razon_social)).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Buscar por RUC/Cédula o nombre...'), 'comercial');

    expect(screen.queryByText(CLIENTE_1.nombre_razon_social)).not.toBeInTheDocument();
    expect(screen.getByText(CLIENTE_2.nombre_razon_social)).toBeInTheDocument();
  });

  it('dado mas de 20 clientes cuando carga entonces pagina de 20 en 20', async () => {
    const muchos: Cliente[] = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1,
      ruc_cedula: `RUC-${String(i + 1).padStart(3, '0')}`,
      nombre_razon_social: `Cliente ${i + 1}`,
      direccion_envio: 'Dirección genérica',
      nivel_precio: 'normal',
      tiene_beneficio: false,
      saldo_pendiente: 0,
      limite_credito: 0,
      plazo_credito_dias: 0,
      is_active: true,
    }));
    renderComponent({ clientes: muchos });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('RUC-001')).toBeInTheDocument();
    expect(screen.queryByText('RUC-021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('RUC-021')).toBeInTheDocument();
    expect(screen.queryByText('RUC-001')).not.toBeInTheDocument();
  });

  it('dado mas de 20 clientes cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const muchos: Cliente[] = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, ruc_cedula: `RUC-${String(i + 1).padStart(3, '0')}`, nombre_razon_social: `Cliente ${i + 1}`,
      direccion_envio: 'Dirección genérica', nivel_precio: 'normal', tiene_beneficio: false,
      saldo_pendiente: 0, limite_credito: 0, plazo_credito_dias: 0, is_active: true,
    })) as Cliente[];
    renderComponent({ clientes: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado mas de 20 clientes cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const muchos: Cliente[] = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, ruc_cedula: `RUC-${String(i + 1).padStart(3, '0')}`, nombre_razon_social: `Cliente ${i + 1}`,
      direccion_envio: 'Dirección genérica', nivel_precio: 'normal', tiene_beneficio: false,
      saldo_pendiente: 0, limite_credito: 0, plazo_credito_dias: 0, is_active: true,
    })) as Cliente[];
    renderComponent({ clientes: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });
});
