import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ManageQuimicos } from './ManageQuimicos';

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

const QUIMICO_1 = {
  id: 1,
  codigo: 'QM-001',
  descripcion: 'Soda Cáustica',
  tipo: 'quimico',
  unidad_medida: 'kg',
  presentacion: 'Saco 25kg',
  precio_base: 12.5,
};

const QUIMICO_2 = {
  id: 2,
  codigo: 'QM-002',
  descripcion: 'Colorante Azul',
  tipo: 'quimico',
  unidad_medida: 'l',
  presentacion: '',
  precio_base: 0,
};

function renderComponent(props: Partial<{
  quimicos: any[];
  onChemicalCreate: (data: any) => Promise<boolean>;
  onChemicalUpdate: (id: number, data: any) => Promise<boolean>;
  onChemicalDelete: (id: number) => void;
  loading: boolean;
}> = {}) {
  const defaults = {
    quimicos: [],
    onChemicalCreate: vi.fn().mockResolvedValue(true),
    onChemicalUpdate: vi.fn().mockResolvedValue(true),
    onChemicalDelete: vi.fn(),
    loading: false,
  };
  const merged = { ...defaults, ...props };
  return {
    ...render(
      <MemoryRouter>
        <ManageQuimicos {...merged} />
      </MemoryRouter>,
    ),
    props: merged,
  };
}

function getRowFor(text: string) {
  const cell = screen.getByText(text);
  return cell.closest('tr') as HTMLElement;
}

describe('ManageQuimicos', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin quimicos cuando no esta cargando entonces no muestra filas de datos', () => {
    renderComponent({ quimicos: [], loading: false });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(1);
  });

  it('dado loading cuando carga entonces muestra filas de skeleton', () => {
    const { container } = renderComponent({ quimicos: [], loading: true });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(6);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('dado quimicos existentes cuando carga entonces los lista con sus datos', () => {
    renderComponent({ quimicos: [QUIMICO_1] });
    expect(screen.getByText('QM-001')).toBeInTheDocument();
    expect(screen.getByText('Soda Cáustica')).toBeInTheDocument();
    expect(screen.getByText('Saco 25kg')).toBeInTheDocument();
    expect(screen.getByText('kg')).toBeInTheDocument();
  });

  it('dado quimico sin presentacion cuando lista entonces muestra guion', () => {
    renderComponent({ quimicos: [QUIMICO_2] });
    expect(screen.getByText('QM-002')).toBeInTheDocument();
    expect(screen.getByText('-')).toBeInTheDocument();
  });

  it('dado busqueda por codigo cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ quimicos: [QUIMICO_1, QUIMICO_2] });
    expect(screen.getByText('QM-002')).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Buscar por código o nombre...'), 'Soda');

    expect(screen.getByText('QM-001')).toBeInTheDocument();
    expect(screen.queryByText('QM-002')).not.toBeInTheDocument();
  });

  it('dado mas de 20 quimicos cuando carga entonces pagina de 20 en 20', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1,
      codigo: `QM-${String(i + 1).padStart(3, '0')}`,
      descripcion: `Quimico ${i + 1}`,
      tipo: 'quimico',
      unidad_medida: 'kg',
      presentacion: '',
      precio_base: 0,
    }));
    renderComponent({ quimicos: muchos });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('QM-001')).toBeInTheDocument();
    expect(screen.queryByText('QM-021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Siguiente'));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('QM-021')).toBeInTheDocument();
    expect(screen.queryByText('QM-001')).not.toBeInTheDocument();
  });

  it('dado mas de 20 quimicos cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, codigo: `QM-${String(i + 1).padStart(3, '0')}`, descripcion: `Quimico ${i + 1}`,
      tipo: 'quimico', unidad_medida: 'kg', presentacion: '', precio_base: 0,
    }));
    renderComponent({ quimicos: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado mas de 20 quimicos cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, codigo: `QM-${String(i + 1).padStart(3, '0')}`, descripcion: `Quimico ${i + 1}`,
      tipo: 'quimico', unidad_medida: 'kg', presentacion: '', precio_base: 0,
    }));
    renderComponent({ quimicos: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado nuevo quimico cuando guarda sin llenar campos requeridos entonces muestra errores de validacion', async () => {
    const onChemicalCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onChemicalCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Químico' }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Químico' }));

    expect(screen.getByText('El código es requerido')).toBeInTheDocument();
    expect(screen.getByText('La descripción es requerida')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onChemicalCreate).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando crea un quimico entonces envia el payload correcto', async () => {
    const onChemicalCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onChemicalCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Químico' }));
    await userEvent.type(screen.getByLabelText(/Código/), 'QM-010');
    await userEvent.type(screen.getByLabelText(/Descripción/), 'Blanqueador');
    await userEvent.type(screen.getByLabelText(/Presentación/), 'Bidón 20L');
    await userEvent.clear(screen.getByLabelText(/Precio Base/));
    await userEvent.type(screen.getByLabelText(/Precio Base/), '30.5');
    await userEvent.click(screen.getByText('Litros (l)'));

    await userEvent.click(screen.getByRole('button', { name: 'Crear Químico' }));

    await waitFor(() => expect(onChemicalCreate).toHaveBeenCalledWith({
      codigo: 'QM-010',
      descripcion: 'Blanqueador',
      unidad_medida: 'l',
      presentacion: 'Bidón 20L',
      precio_base: 30.5,
      tipo: 'quimico',
    }));
  });

  it('dado creacion exitosa cuando la API responde true entonces cierra el dialogo y limpia el formulario', async () => {
    const onChemicalCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onChemicalCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Químico' }));
    await userEvent.type(screen.getByLabelText(/Código/), 'QM-010');
    await userEvent.type(screen.getByLabelText(/Descripción/), 'Blanqueador');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Químico' }));

    await waitFor(() => expect(screen.queryByText('Completa el formulario para crear un nuevo químico')).not.toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Químico' }));
    expect(screen.getByLabelText(/Código/)).toHaveValue('');
  });

  it('dado creacion fallida cuando la API responde false entonces mantiene el dialogo abierto', async () => {
    const onChemicalCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ onChemicalCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Químico' }));
    await userEvent.type(screen.getByLabelText(/Código/), 'QM-010');
    await userEvent.type(screen.getByLabelText(/Descripción/), 'Blanqueador');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Químico' }));

    await waitFor(() => expect(onChemicalCreate).toHaveBeenCalled());
    expect(screen.getByText('Completa el formulario para crear un nuevo químico')).toBeInTheDocument();
  });

  it('dado editar un quimico existente cuando abre el dialogo entonces precarga sus datos', async () => {
    renderComponent({ quimicos: [QUIMICO_1] });

    const row = getRowFor('QM-001');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    expect(screen.getByText('Editar Químico')).toBeInTheDocument();
    expect(screen.getByLabelText(/Código/)).toHaveValue('QM-001');
    expect(screen.getByLabelText(/Descripción/)).toHaveValue('Soda Cáustica');
    expect(screen.getByLabelText(/Presentación/)).toHaveValue('Saco 25kg');
    expect(screen.getByLabelText(/Precio Base/)).toHaveValue(12.5);
  });

  it('dado editar cuando guarda entonces llama onChemicalUpdate con el id y los datos', async () => {
    const onChemicalUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ quimicos: [QUIMICO_1], onChemicalUpdate });

    const row = getRowFor('QM-001');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    await userEvent.clear(screen.getByLabelText(/Descripción/));
    await userEvent.type(screen.getByLabelText(/Descripción/), 'Soda Cáustica 50%');
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Químico' }));

    await waitFor(() => expect(onChemicalUpdate).toHaveBeenCalledWith(1, expect.objectContaining({
      codigo: 'QM-001',
      descripcion: 'Soda Cáustica 50%',
      unidad_medida: 'kg',
      tipo: 'quimico',
    })));
  });

  it('dado eliminar cuando se hace click en el boton de eliminar entonces llama a onChemicalDelete con el id', async () => {
    const onChemicalDelete = vi.fn();
    renderComponent({ quimicos: [QUIMICO_1], onChemicalDelete });

    const row = getRowFor('QM-001');
    const deleteButton = within(row).getAllByRole('button')[1];
    await userEvent.click(deleteButton);

    expect(onChemicalDelete).toHaveBeenCalledWith(1);
  });

  it('dado cancelar cuando se hace click entonces cierra el dialogo sin guardar', async () => {
    const onChemicalCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onChemicalCreate });

    await userEvent.click(screen.getByRole('button', { name: 'Nuevo Químico' }));
    await userEvent.type(screen.getByLabelText(/Código/), 'QM-999');
    await userEvent.click(screen.getByText('Cancelar'));

    await waitFor(() => expect(screen.queryByText('Completa el formulario para crear un nuevo químico')).not.toBeInTheDocument());
    expect(onChemicalCreate).not.toHaveBeenCalled();
  });
});
