import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ManageProductos } from './ManageProductos';

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

const PRODUCTO_1 = {
  id: 1,
  codigo: 'PR-001',
  descripcion: 'Hilo Algodón 30/1',
  tipo: 'hilo',
  unidad_medida: 'kg',
  stock_minimo: 50,
  precio_base: 8.75,
  presentacion: 'Cono 1kg',
  pais_origen: 'Perú',
  calidad: 'Primera',
};

const PRODUCTO_2 = {
  id: 2,
  codigo: 'PR-002',
  descripcion: 'Tela Jersey',
  tipo: 'tela',
  unidad_medida: 'metros',
  stock_minimo: 0,
  precio_base: 0,
  presentacion: '',
  pais_origen: '',
  calidad: '',
};

const PRODUCTO_MERMA = {
  id: 3,
  codigo: 'PR-003',
  descripcion: 'Retazo de Tela',
  tipo: 'merma',
  unidad_medida: 'kg',
  stock_minimo: 5,
  precio_base: 2.5,
  presentacion: 'Fardo',
  pais_origen: '',
  calidad: '',
};

function renderComponent(props: Partial<{
  productos: any[];
  onProductCreate: (data: any) => Promise<boolean>;
  onProductUpdate: (id: number, data: any) => Promise<boolean>;
  onProductDelete: (id: number) => void;
  loading: boolean;
}> = {}) {
  const defaults = {
    productos: [],
    onProductCreate: vi.fn().mockResolvedValue(true),
    onProductUpdate: vi.fn().mockResolvedValue(true),
    onProductDelete: vi.fn(),
    loading: false,
  };
  const merged = { ...defaults, ...props };
  return {
    ...render(
      <MemoryRouter>
        <ManageProductos {...merged} />
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
  return userEvent.click(screen.getByRole('button', { name: 'Nuevo Producto' }));
}

describe('ManageProductos', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin productos cuando no esta cargando entonces no muestra filas de datos', () => {
    renderComponent({ productos: [], loading: false });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(1);
  });

  it('dado loading cuando carga entonces muestra filas de skeleton', () => {
    const { container } = renderComponent({ productos: [], loading: true });
    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(6);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('dado productos existentes cuando carga entonces los lista con sus datos', () => {
    renderComponent({ productos: [PRODUCTO_1] });
    expect(screen.getByText('PR-001')).toBeInTheDocument();
    expect(screen.getByText('Hilo Algodón 30/1')).toBeInTheDocument();
    expect(screen.getByText('hilo')).toBeInTheDocument();
    expect(screen.getByText('Cono 1kg')).toBeInTheDocument();
    expect(screen.getByText('Perú')).toBeInTheDocument();
    expect(screen.getByText('Primera')).toBeInTheDocument();
    expect(screen.getByText('kg')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('$8.75')).toBeInTheDocument();
  });

  it('dado producto sin campos opcionales cuando lista entonces muestra guion', () => {
    renderComponent({ productos: [PRODUCTO_2] });
    const row = getRowFor('PR-002');
    expect(within(row).getAllByText('-')).toHaveLength(3);
  });

  it('dado producto tipo merma cuando lista entonces muestra el badge correspondiente', () => {
    renderComponent({ productos: [PRODUCTO_MERMA] });
    expect(screen.getByText('PR-003')).toBeInTheDocument();
    expect(screen.getByText('merma')).toBeInTheDocument();
  });

  it('dado busqueda por codigo cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ productos: [PRODUCTO_1, PRODUCTO_2] });
    expect(screen.getByText('PR-002')).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Buscar por código o descripción...'), 'Hilo');

    expect(screen.getByText('PR-001')).toBeInTheDocument();
    expect(screen.queryByText('PR-002')).not.toBeInTheDocument();
  });

  it('dado filtro por tipo cuando selecciona un tipo entonces filtra la lista', async () => {
    renderComponent({ productos: [PRODUCTO_1, PRODUCTO_MERMA] });
    expect(screen.getByText('PR-001')).toBeInTheDocument();
    expect(screen.getByText('PR-003')).toBeInTheDocument();

    await userEvent.click(screen.getByText('Merma'));

    expect(screen.queryByText('PR-001')).not.toBeInTheDocument();
    expect(screen.getByText('PR-003')).toBeInTheDocument();
  });

  it('dado mas de 20 productos cuando carga entonces pagina de 20 en 20', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1,
      codigo: `PR-${String(i + 1).padStart(3, '0')}`,
      descripcion: `Producto ${i + 1}`,
      tipo: 'hilo',
      unidad_medida: 'kg',
      stock_minimo: 0,
      precio_base: 0,
      presentacion: '',
      pais_origen: '',
      calidad: '',
    }));
    renderComponent({ productos: muchos });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('PR-001')).toBeInTheDocument();
    expect(screen.queryByText('PR-021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Siguiente'));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('PR-021')).toBeInTheDocument();
    expect(screen.queryByText('PR-001')).not.toBeInTheDocument();
  });

  it('dado mas de 20 productos cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, codigo: `PR-${String(i + 1).padStart(3, '0')}`, descripcion: `Producto ${i + 1}`,
      tipo: 'hilo', unidad_medida: 'kg', stock_minimo: 0, precio_base: 0,
      presentacion: '', pais_origen: '', calidad: '',
    }));
    renderComponent({ productos: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado mas de 20 productos cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const muchos = Array.from({ length: 25 }).map((_, i) => ({
      id: i + 1, codigo: `PR-${String(i + 1).padStart(3, '0')}`, descripcion: `Producto ${i + 1}`,
      tipo: 'hilo', unidad_medida: 'kg', stock_minimo: 0, precio_base: 0,
      presentacion: '', pais_origen: '', calidad: '',
    }));
    renderComponent({ productos: muchos });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado nuevo producto cuando guarda sin llenar campos requeridos entonces muestra errores de validacion', async () => {
    const onProductCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onProductCreate });

    await openCreateDialog();
    await userEvent.click(screen.getByRole('button', { name: 'Crear Producto' }));

    expect(screen.getByText('El código es requerido')).toBeInTheDocument();
    expect(screen.getByText('La descripción es requerida')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onProductCreate).not.toHaveBeenCalled();
  });

  it('dado datos minimos validos cuando crea un producto entonces envia el payload con los valores por defecto', async () => {
    const onProductCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onProductCreate });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Código/), 'PR-010');
    await userEvent.type(within(dialog).getByLabelText(/Descripción/), 'Nuevo Producto Test');

    await userEvent.click(screen.getByRole('button', { name: 'Crear Producto' }));

    await waitFor(() => expect(onProductCreate).toHaveBeenCalledWith({
      codigo: 'PR-010',
      descripcion: 'Nuevo Producto Test',
      tipo: 'hilo',
      unidad_medida: 'kg',
      stock_minimo: 0,
      precio_base: 0,
      presentacion: '',
      pais_origen: '',
      calidad: '',
    }));
  });

  it('dado datos completos incluyendo tipo merma cuando crea un producto entonces envia el payload correcto', async () => {
    const onProductCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onProductCreate });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Código/), 'PR-020');
    await userEvent.type(within(dialog).getByLabelText(/Descripción/), 'Retazo Sobrante');
    await userEvent.click(within(dialog).getByText('Merma / Desperdicio Vendible'));
    await userEvent.click(within(dialog).getByText('Libras (lb)'));
    await userEvent.clear(within(dialog).getByLabelText('Stock Mínimo'));
    await userEvent.type(within(dialog).getByLabelText('Stock Mínimo'), '15');
    await userEvent.clear(within(dialog).getByLabelText('Precio Base Unitario'));
    await userEvent.type(within(dialog).getByLabelText('Precio Base Unitario'), '3.25');
    await userEvent.type(within(dialog).getByLabelText('Presentación'), 'Bulto 20kg');
    await userEvent.type(within(dialog).getByLabelText('País de Origen'), 'Colombia');
    await userEvent.type(within(dialog).getByLabelText('Calidad'), 'Segunda');

    await userEvent.click(screen.getByRole('button', { name: 'Crear Producto' }));

    await waitFor(() => expect(onProductCreate).toHaveBeenCalledWith({
      codigo: 'PR-020',
      descripcion: 'Retazo Sobrante',
      tipo: 'merma',
      unidad_medida: 'lb',
      stock_minimo: 15,
      precio_base: 3.25,
      presentacion: 'Bulto 20kg',
      pais_origen: 'Colombia',
      calidad: 'Segunda',
    }));
  });

  it('dado creacion exitosa cuando la API responde true entonces cierra el dialogo y limpia el formulario', async () => {
    const onProductCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onProductCreate });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Código/), 'PR-010');
    await userEvent.type(within(dialog).getByLabelText(/Descripción/), 'Nuevo Producto Test');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Producto' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    await openCreateDialog();
    expect(screen.getByLabelText(/Código/)).toHaveValue('');
  });

  it('dado creacion fallida cuando la API responde false entonces mantiene el dialogo abierto', async () => {
    const onProductCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ onProductCreate });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Código/), 'PR-010');
    await userEvent.type(within(dialog).getByLabelText(/Descripción/), 'Nuevo Producto Test');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Producto' }));

    await waitFor(() => expect(onProductCreate).toHaveBeenCalled());
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('dado editar un producto existente cuando abre el dialogo entonces precarga sus datos', async () => {
    renderComponent({ productos: [PRODUCTO_1] });

    const row = getRowFor('PR-001');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    expect(screen.getByText('Editar Producto')).toBeInTheDocument();
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByLabelText(/Código/)).toHaveValue('PR-001');
    expect(within(dialog).getByLabelText(/Descripción/)).toHaveValue('Hilo Algodón 30/1');
    expect(within(dialog).getByLabelText('Stock Mínimo')).toHaveValue(50);
    expect(within(dialog).getByLabelText('Precio Base Unitario')).toHaveValue(8.75);
    expect(within(dialog).getByLabelText('Presentación')).toHaveValue('Cono 1kg');
    expect(within(dialog).getByLabelText('País de Origen')).toHaveValue('Perú');
    expect(within(dialog).getByLabelText('Calidad')).toHaveValue('Primera');
  });

  it('dado editar cuando guarda entonces llama onProductUpdate con el id y los datos', async () => {
    const onProductUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ productos: [PRODUCTO_1], onProductUpdate });

    const row = getRowFor('PR-001');
    const editButton = within(row).getAllByRole('button')[0];
    await userEvent.click(editButton);

    const dialog = screen.getByRole('dialog');
    await userEvent.clear(within(dialog).getByLabelText(/Descripción/));
    await userEvent.type(within(dialog).getByLabelText(/Descripción/), 'Hilo Algodón 30/1 Blanqueado');
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Producto' }));

    await waitFor(() => expect(onProductUpdate).toHaveBeenCalledWith(1, expect.objectContaining({
      codigo: 'PR-001',
      descripcion: 'Hilo Algodón 30/1 Blanqueado',
      tipo: 'hilo',
      unidad_medida: 'kg',
      stock_minimo: 50,
      precio_base: 8.75,
    })));
  });

  it('dado eliminar cuando se hace click en el boton de eliminar entonces llama a onProductDelete con el id', async () => {
    const onProductDelete = vi.fn();
    renderComponent({ productos: [PRODUCTO_1], onProductDelete });

    const row = getRowFor('PR-001');
    const deleteButton = within(row).getAllByRole('button')[1];
    await userEvent.click(deleteButton);

    expect(onProductDelete).toHaveBeenCalledWith(1);
  });

  it('dado cancelar cuando se hace click entonces cierra el dialogo sin guardar', async () => {
    const onProductCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onProductCreate });

    await openCreateDialog();
    const dialog = screen.getByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Código/), 'PR-999');
    await userEvent.click(within(dialog).getByText('Cancelar'));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(onProductCreate).not.toHaveBeenCalled();
  });
});
