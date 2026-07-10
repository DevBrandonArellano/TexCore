import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ComponenteMezclaPanel } from './ComponenteMezclaPanel';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    delete: (...args: any[]) => mockDelete(...args),
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

const PRODUCTO = { id: 1, codigo: 'QUIM-A' };
const BODEGA = { id: 2, nombre: 'Bodega Químicos' };

const COMPONENTE_1 = {
  id: 10,
  orden: 5,
  producto: 1,
  bodega: 2,
  porcentaje: '60.00',
  producto_detail: { codigo: 'QUIM-A' },
  bodega_detail: { nombre: 'Bodega Químicos' },
};

function renderComponent(props: Partial<{ ordenId: number; pesoNeto: number; readonly: boolean }> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ComponenteMezclaPanel ordenId={5} pesoNeto={100} {...props} />
    </QueryClientProvider>,
  );
}

function mockFetch(componentes: any[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url.startsWith('/componentes-mezcla/')) return Promise.resolve({ data: { results: componentes } });
    if (url === '/productos/') return Promise.resolve({ data: { results: [PRODUCTO] } });
    if (url === '/bodegas/') return Promise.resolve({ data: { results: [BODEGA] } });
    return Promise.resolve({ data: { results: [] } });
  });
}

describe('ComponenteMezclaPanel', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado sin componentes cuando carga entonces muestra mensaje vacio y total 0%', async () => {
    mockFetch([]);
    renderComponent();
    await waitFor(() => expect(screen.getByText(/Sin componentes/)).toBeInTheDocument());
    expect(screen.getByText('Total: 0.0% (debe ser 100%)')).toBeInTheDocument();
  });

  it('dado componentes que suman 100% cuando carga entonces marca el total como valido', async () => {
    mockFetch([COMPONENTE_1, { ...COMPONENTE_1, id: 11, porcentaje: '40.00' }]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Total: 100.0% ✓')).toBeInTheDocument());
  });

  it('dado un componente cuando carga entonces muestra su producto bodega y peso estimado', async () => {
    mockFetch([COMPONENTE_1]);
    renderComponent({ pesoNeto: 200 });
    // "QUIM-A" aparece dos veces: en la fila de la lista y en el <SelectItem>
    // del formulario de agregar (no readonly). El de la lista es el primero.
    await waitFor(() => expect(screen.getAllByText('QUIM-A')[0]).toBeInTheDocument());
    expect(screen.getByText(/desde Bodega Químicos/)).toBeInTheDocument();
    expect(screen.getByText('60.00%')).toBeInTheDocument();
    // 60% de 200kg = 120.0 kg
    expect(screen.getByText(/≈ 120\.0 kg/)).toBeInTheDocument();
  });

  it('dado modo readonly cuando renderiza entonces no muestra el formulario ni el boton de eliminar', async () => {
    mockFetch([COMPONENTE_1]);
    renderComponent({ readonly: true });
    // En readonly no se renderiza el formulario, así que "QUIM-A" es único.
    await waitFor(() => expect(screen.getByText('QUIM-A')).toBeInTheDocument());
    expect(screen.queryByText('+')).not.toBeInTheDocument();
    expect(screen.queryByText('✕')).not.toBeInTheDocument();
  });

  it('dado boton agregar deshabilitado cuando faltan campos entonces no permite agregar', async () => {
    mockFetch([]);
    renderComponent();
    await waitFor(() => expect(screen.getByText(/Sin componentes/)).toBeInTheDocument());
    expect(screen.getByText('+')).toBeDisabled();
  });

  it('dado datos completos cuando agrega un componente entonces llama a la API y notifica exito', async () => {
    mockFetch([]);
    mockPost.mockResolvedValueOnce({ data: { id: 20 } });
    renderComponent();
    await waitFor(() => expect(screen.getByText(/Sin componentes/)).toBeInTheDocument());

    // Con la lista vacía "QUIM-A"/"Bodega Químicos" son únicos, pero las
    // queries de productos/bodegas resuelven de forma independiente — se
    // espera explícitamente a que la opción exista antes de hacer click.
    await userEvent.click(await screen.findByText('QUIM-A'));
    await userEvent.click(await screen.findByText('Bodega Químicos'));
    await userEvent.type(screen.getByPlaceholderText('50'), '75');

    expect(screen.getByText('+')).not.toBeDisabled();
    await userEvent.click(screen.getByText('+'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/componentes-mezcla/', {
      orden: 5,
      producto: 1,
      bodega: 2,
      porcentaje: '75',
    }));
    expect(toastSuccessMock).toHaveBeenCalledWith('Componente agregado');
  });

  it('dado error del backend con non_field_errors cuando agrega entonces muestra ese mensaje', async () => {
    mockFetch([]);
    mockPost.mockRejectedValueOnce({ response: { data: { non_field_errors: ['La suma supera el 100%.'] } } });
    renderComponent();
    await waitFor(() => expect(screen.getByText(/Sin componentes/)).toBeInTheDocument());

    await userEvent.click(await screen.findByText('QUIM-A'));
    await userEvent.click(await screen.findByText('Bodega Químicos'));
    await userEvent.type(screen.getByPlaceholderText('50'), '150');
    await userEvent.click(screen.getByText('+'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('La suma supera el 100%.'));
  });

  it('dado eliminar un componente cuando se hace click entonces llama a la API con la justificacion', async () => {
    mockFetch([COMPONENTE_1]);
    mockDelete.mockResolvedValueOnce({});
    renderComponent();
    await waitFor(() => expect(screen.getAllByText('QUIM-A')[0]).toBeInTheDocument());

    await userEvent.click(screen.getByText('✕'));

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/componentes-mezcla/10/', {
      data: { justificacion: 'Eliminado por jefe de área' },
    }));
    expect(toastSuccessMock).toHaveBeenCalledWith('Componente eliminado');
  });

  it('dado error al eliminar cuando falla la API entonces muestra toast de error', async () => {
    mockFetch([COMPONENTE_1]);
    mockDelete.mockRejectedValueOnce(new Error('500'));
    renderComponent();
    await waitFor(() => expect(screen.getAllByText('QUIM-A')[0]).toBeInTheDocument());

    await userEvent.click(screen.getByText('✕'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar'));
  });
});
