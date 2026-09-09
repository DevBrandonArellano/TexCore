import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ManageProveedores } from './ManageProveedores';
import { Proveedor } from '../../lib/types';

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: vi.fn(),
  },
}));

const PROVEEDOR_1: Proveedor = { id: 1, nombre: 'Textiles del Norte', sede: 3 };

function renderComponent(props: Partial<{
  proveedores: Proveedor[];
  onProveedorCreate: (data: any) => Promise<boolean>;
  onProveedorUpdate: (id: number, data: any) => Promise<boolean>;
  onProveedorDelete: (id: number) => void;
  loading: boolean;
}> = {}) {
  const defaultProps = {
    proveedores: [] as Proveedor[],
    onProveedorCreate: vi.fn().mockResolvedValue(true),
    onProveedorUpdate: vi.fn().mockResolvedValue(true),
    onProveedorDelete: vi.fn(),
    loading: false,
  };
  const merged = { ...defaultProps, ...props };
  const utils = render(
    <MemoryRouter>
      <ManageProveedores {...merged} />
    </MemoryRouter>,
  );
  return { ...utils, props: merged };
}

describe('ManageProveedores', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado sin proveedores cuando carga entonces no muestra filas en la tabla', () => {
    renderComponent({ proveedores: [] });
    expect(screen.queryAllByRole('row')).toHaveLength(1);
    expect(screen.getByText('Página 1 de 1')).toBeInTheDocument();
  });

  it('dado proveedores existentes cuando carga entonces los lista con su nombre', () => {
    renderComponent({ proveedores: [PROVEEDOR_1] });
    expect(screen.getByText('Textiles del Norte')).toBeInTheDocument();
  });

  it('dado nuevo proveedor cuando intenta guardar sin nombre entonces muestra error y no crea', async () => {
    const onProveedorCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onProveedorCreate });

    await userEvent.click(screen.getByText('Nuevo Proveedor'));
    expect(screen.getByText('Nuevo Proveedor', { selector: '[data-slot="dialog-title"], h2' })).toBeInTheDocument();

    await userEvent.click(screen.getByText('Crear Proveedor'));

    expect(screen.getByText('El nombre es requerido')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onProveedorCreate).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando crea un proveedor entonces llama a onProveedorCreate con el payload correcto', async () => {
    const onProveedorCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onProveedorCreate });

    await userEvent.click(screen.getByText('Nuevo Proveedor'));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Hilos y Fibras SA');
    await userEvent.click(screen.getByText('Crear Proveedor'));

    await waitFor(() => expect(onProveedorCreate).toHaveBeenCalledWith({
      nombre: 'Hilos y Fibras SA',
      sede: '',
    }));

    await waitFor(() => expect(screen.queryByText('Crear Proveedor')).not.toBeInTheDocument());
  });

  it('dado editar un proveedor existente cuando abre el dialogo entonces precarga su nombre', async () => {
    renderComponent({ proveedores: [PROVEEDOR_1] });

    const row = screen.getByText('Textiles del Norte').closest('tr') as HTMLElement;
    const [editButton] = within(row).getAllByRole('button');
    await userEvent.click(editButton);

    expect(screen.getByText('Editar Proveedor')).toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre/)).toHaveValue('Textiles del Norte');
  });

  it('dado editar cuando guarda entonces llama a onProveedorUpdate con el id y los datos', async () => {
    const onProveedorUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ proveedores: [PROVEEDOR_1], onProveedorUpdate });

    const row = screen.getByText('Textiles del Norte').closest('tr') as HTMLElement;
    const [editButton] = within(row).getAllByRole('button');
    await userEvent.click(editButton);

    const input = screen.getByLabelText(/Nombre/);
    await userEvent.clear(input);
    await userEvent.type(input, 'Textiles del Sur');
    await userEvent.click(screen.getByText('Actualizar Proveedor'));

    await waitFor(() => expect(onProveedorUpdate).toHaveBeenCalledWith(1, {
      nombre: 'Textiles del Sur',
      sede: '3',
    }));
  });

  it('dado guardado fallido cuando onProveedorCreate resuelve false entonces el dialogo permanece abierto', async () => {
    const onProveedorCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ onProveedorCreate });

    await userEvent.click(screen.getByText('Nuevo Proveedor'));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Proveedor Fallido');
    await userEvent.click(screen.getByText('Crear Proveedor'));

    await waitFor(() => expect(onProveedorCreate).toHaveBeenCalled());
    expect(screen.getByText('Crear Proveedor')).toBeInTheDocument();
  });

  it('dado eliminar cuando se hace clic en el boton entonces llama a onProveedorDelete con el id', async () => {
    const onProveedorDelete = vi.fn();
    renderComponent({ proveedores: [PROVEEDOR_1], onProveedorDelete });

    const row = screen.getByText('Textiles del Norte').closest('tr') as HTMLElement;
    const buttons = within(row).getAllByRole('button');
    await userEvent.click(buttons[1]);

    expect(onProveedorDelete).toHaveBeenCalledWith(1);
  });

  it('dado un termino de busqueda cuando se escribe entonces filtra la lista por nombre', async () => {
    const proveedores: Proveedor[] = [
      PROVEEDOR_1,
      { id: 2, nombre: 'Algodones Pacifico', sede: null },
    ];
    renderComponent({ proveedores });

    expect(screen.getByText('Textiles del Norte')).toBeInTheDocument();
    expect(screen.getByText('Algodones Pacifico')).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Buscar por nombre...'), 'algodones');

    expect(screen.queryByText('Textiles del Norte')).not.toBeInTheDocument();
    expect(screen.getByText('Algodones Pacifico')).toBeInTheDocument();
  });

  it('dado loading en true entonces muestra filas de esqueleto en vez de datos', () => {
    renderComponent({ proveedores: [PROVEEDOR_1], loading: true });
    expect(screen.queryByText('Textiles del Norte')).not.toBeInTheDocument();
    const rows = screen.getAllByRole('row');
    expect(rows.length).toBe(6);
  });

  it('dado mas de 20 proveedores cuando avanza con Siguiente entonces pagina los resultados', async () => {
    const proveedores: Proveedor[] = Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      nombre: `Proveedor ${i + 1}`,
      sede: null,
    }));
    renderComponent({ proveedores });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('Proveedor 1')).toBeInTheDocument();
    expect(screen.queryByText('Proveedor 21')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Proveedor 21')).toBeInTheDocument();
    expect(screen.queryByText('Proveedor 1')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Anterior/ }));
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado mas de 20 proveedores cuando escribe una pagina en Ir a entonces navega a esa pagina', async () => {
    const proveedores: Proveedor[] = Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      nombre: `Proveedor ${i + 1}`,
      sede: null,
    }));
    renderComponent({ proveedores });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2');
    await userEvent.tab(); // dispara onBlur

    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Proveedor 21')).toBeInTheDocument();
  });

  it('dado un termino de busqueda cuando filtra a menos de una pagina entonces vuelve a la pagina 1', async () => {
    const proveedores: Proveedor[] = Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      nombre: `Proveedor ${i + 1}`,
      sede: null,
    }));
    renderComponent({ proveedores });

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Buscar por nombre...'), 'Proveedor 1');
    expect(screen.getByText('Página 1 de 1')).toBeInTheDocument();
  });
});
