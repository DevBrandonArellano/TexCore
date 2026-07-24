import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InventoryForm } from './InventoryForm';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
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

const PRODUCTOS = [
  { id: 1, codigo: 'ALG-01', descripcion: 'Algodón Crudo' },
  { id: 2, codigo: 'TEL-02', descripcion: 'Tela Procesada' },
];
const BODEGAS = [
  { id: 10, nombre: 'Bodega Central' },
  { id: 20, nombre: 'Bodega Norte' },
];

function mockFetch(productos: any[] = PRODUCTOS, bodegas: any[] = BODEGAS) {
  mockGet.mockImplementation((url: string) => {
    if (url === '/productos/') return Promise.resolve({ data: productos });
    if (url === '/bodegas/') return Promise.resolve({ data: bodegas });
    return Promise.resolve({ data: [] });
  });
}

function renderComponent(onMovementCreated = vi.fn()) {
  render(<InventoryForm onMovementCreated={onMovementCreated} />);
  return { onMovementCreated };
}

async function llenarFormularioValido() {
  await userEvent.click(screen.getByText('Algodón Crudo'));
  await userEvent.click(screen.getByText('Bodega Central'));
  await userEvent.click(screen.getByText('ENTRADA (Ingreso a Bodega)'));
  await userEvent.click(screen.getByText('Entrada - Compra de Material'));
  await userEvent.type(screen.getByLabelText('Cantidad'), '15');
}

describe('InventoryForm', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado carga inicial cuando monta entonces muestra estado de carga y luego el formulario', async () => {
    mockFetch();
    renderComponent();

    expect(screen.getByText('Cargando datos del formulario...')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'Registrar Movimiento' })).toBeInTheDocument();
    expect(screen.getByText('Producto')).toBeInTheDocument();
    expect(screen.getByText('Bodega')).toBeInTheDocument();
    expect(screen.getByText('Acción')).toBeInTheDocument();
    expect(screen.getByText('Motivo del Movimiento')).toBeInTheDocument();
    expect(screen.getByLabelText('Documento de Referencia (Opcional)')).toBeInTheDocument();
    expect(screen.getByText('Algodón Crudo')).toBeInTheDocument();
    expect(screen.getByText('Bodega Central')).toBeInTheDocument();
  });

  it('dado error al cargar datos iniciales entonces muestra un toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    renderComponent();

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar datos para el formulario.'),
    );
  });

  it('dado formulario vacio cuando se envia entonces muestra errores de validacion y no llama a la API', async () => {
    mockFetch();
    renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Registrar Movimiento' }));

    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos.');
    expect(screen.getByText('Selecciona un producto.')).toBeInTheDocument();
    expect(screen.getByText('Selecciona una bodega.')).toBeInTheDocument();
    expect(screen.getByText('Selecciona si es ENTRADA o SALIDA.')).toBeInTheDocument();
    expect(screen.getByText('Selecciona el motivo del movimiento.')).toBeInTheDocument();
    expect(screen.getByText('Ingresa una cantidad válida mayor a 0.')).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado cantidad igual a cero cuando se envia entonces muestra error de cantidad invalida', async () => {
    mockFetch();
    renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Algodón Crudo'));
    await userEvent.click(screen.getByText('Bodega Central'));
    await userEvent.click(screen.getByText('ENTRADA (Ingreso a Bodega)'));
    await userEvent.click(screen.getByText('Entrada - Compra de Material'));
    await userEvent.type(screen.getByLabelText('Cantidad'), '0');
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Movimiento' }));

    expect(screen.getByText('Ingresa una cantidad válida mayor a 0.')).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado datos validos de entrada cuando se envia entonces llama a la API con el payload correcto y muestra exito', async () => {
    mockFetch();
    mockPost.mockResolvedValueOnce({ data: { id: 99 } });
    const { onMovementCreated } = renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await llenarFormularioValido();
    await userEvent.type(
      screen.getByLabelText('Documento de Referencia (Opcional)'),
      'FAC-001',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Movimiento' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith('/inventory/movimientos/', {
        producto: '1',
        cantidad: '15',
        tipo_movimiento: 'COMPRA',
        bodega_origen: null,
        bodega_destino: '10',
        documento_ref: 'FAC-001',
      }),
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Movimiento registrado con éxito.');
    expect(onMovementCreated).toHaveBeenCalledWith({ id: 99 });
  });

  it('dado datos validos de salida cuando se envia entonces asigna la bodega como origen', async () => {
    mockFetch();
    mockPost.mockResolvedValueOnce({ data: { id: 100 } });
    renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Tela Procesada'));
    await userEvent.click(screen.getByText('Bodega Norte'));
    await userEvent.click(screen.getByText('SALIDA (Egreso de Bodega)'));
    await userEvent.click(screen.getByText('Salida - Venta'));
    await userEvent.type(screen.getByLabelText('Cantidad'), '5');
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Movimiento' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith('/inventory/movimientos/', {
        producto: '2',
        cantidad: '5',
        tipo_movimiento: 'VENTA',
        bodega_origen: '20',
        bodega_destino: null,
        documento_ref: '',
      }),
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Movimiento registrado con éxito.');
  });

  it('dado envio exitoso entonces limpia el formulario', async () => {
    mockFetch();
    mockPost.mockResolvedValueOnce({ data: { id: 99 } });
    renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await llenarFormularioValido();
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Movimiento' }));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    expect((screen.getByLabelText('Cantidad') as HTMLInputElement).value).toBe('');
  });

  it('dado fallo de la API con datos de error cuando se envia entonces muestra un toast con el detalle', async () => {
    mockFetch();
    mockPost.mockRejectedValueOnce({ response: { data: { producto: ['Este campo es requerido.'] } } });
    renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await llenarFormularioValido();
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Movimiento' }));

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith(
        'Error al registrar',
        expect.objectContaining({ description: expect.anything() }),
      ),
    );
  });

  it('dado fallo de red sin respuesta del servidor cuando se envia entonces muestra un toast de error generico', async () => {
    mockFetch();
    mockPost.mockRejectedValueOnce(new Error('network error'));
    renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await llenarFormularioValido();
    await userEvent.click(screen.getByRole('button', { name: 'Registrar Movimiento' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error de red o servidor.'));
  });

  it('dado clic en limpiar cuando hay datos escritos entonces reinicia el formulario', async () => {
    mockFetch();
    renderComponent();
    await waitFor(() => expect(screen.getByLabelText('Cantidad')).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText('Cantidad'), '42');
    await userEvent.type(
      screen.getByLabelText('Documento de Referencia (Opcional)'),
      'algo',
    );
    await userEvent.click(screen.getByText('Limpiar'));

    expect((screen.getByLabelText('Cantidad') as HTMLInputElement).value).toBe('');
    expect(
      (screen.getByLabelText('Documento de Referencia (Opcional)') as HTMLTextAreaElement).value,
    ).toBe('');
  });
});
