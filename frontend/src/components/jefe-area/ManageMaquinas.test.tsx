import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ManageMaquinas } from './ManageMaquinas';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
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

const MAQUINA_1 = {
  id: 1,
  nombre: 'Tintura 1',
  estado: 'operativa',
  capacidad_maxima: '500.00',
  eficiencia_ideal: '0.85',
  producto_merma: null,
  bodega_merma: null,
  producto_merma_detail: null,
};

function renderComponent(props: Partial<{ areaId: number }> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ManageMaquinas {...props} />
    </QueryClientProvider>,
  );
}

function mockFetch(maquinas: any[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url.startsWith('/maquinas/')) return Promise.resolve({ data: { results: maquinas } });
    if (url.startsWith('/productos/')) return Promise.resolve({ data: { results: [] } });
    if (url === '/bodegas/') return Promise.resolve({ data: { results: [] } });
    return Promise.resolve({ data: { results: [] } });
  });
}

describe('ManageMaquinas', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado sin maquinas cuando carga entonces muestra mensaje vacio', async () => {
    mockFetch([]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('No hay máquinas registradas')).toBeInTheDocument());
  });

  it('dado maquinas existentes cuando carga entonces las lista con su estado y capacidad', async () => {
    mockFetch([MAQUINA_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());
    expect(screen.getByText('operativa')).toBeInTheDocument();
    expect(screen.getByText('500.00 kg')).toBeInTheDocument();
    expect(screen.getByText('Sin configurar')).toBeInTheDocument();
  });

  it('dado maquina con producto de merma cuando carga entonces muestra el codigo del producto', async () => {
    mockFetch([{ ...MAQUINA_1, producto_merma: 9, producto_merma_detail: { codigo: 'MERMA-01' } }]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('MERMA-01')).toBeInTheDocument());
  });

  it('dado areaId cuando monta entonces filtra maquinas por area en la query', async () => {
    mockFetch([]);
    renderComponent({ areaId: 7 });
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/maquinas/?area=7'));
  });

  it('dado nueva maquina cuando abre el dialogo entonces el boton guardar esta deshabilitado sin nombre', async () => {
    mockFetch([]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('No hay máquinas registradas')).toBeInTheDocument());

    await userEvent.click(screen.getByText('+ Nueva Máquina'));

    expect(screen.getByText('Nueva Máquina')).toBeInTheDocument();
    expect(screen.getByText('Guardar')).toBeDisabled();
  });

  it('dado datos validos cuando crea una maquina entonces envia el payload correcto', async () => {
    mockFetch([]);
    mockPost.mockResolvedValueOnce({ data: { id: 5 } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('No hay máquinas registradas')).toBeInTheDocument());

    await userEvent.click(screen.getByText('+ Nueva Máquina'));
    await userEvent.type(screen.getByPlaceholderText('Ej: Máquina de Hilado 01'), 'Secadora 1');
    await userEvent.click(screen.getByText('Guardar'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/maquinas/', expect.objectContaining({
      nombre: 'Secadora 1',
      estado: 'operativa',
      producto_merma: null,
      bodega_merma: null,
    })));
    expect(toastSuccessMock).toHaveBeenCalledWith('Máquina creada');
  });

  it('dado editar una maquina existente cuando abre el dialogo entonces precarga sus datos', async () => {
    mockFetch([MAQUINA_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Editar'));

    expect(screen.getByText('Editar Máquina')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ej: Máquina de Hilado 01')).toHaveValue('Tintura 1');
  });

  it('dado editar cuando guarda entonces usa PATCH con el id de la maquina', async () => {
    mockFetch([MAQUINA_1]);
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Editar'));
    await userEvent.click(screen.getByText('Guardar'));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/maquinas/1/', expect.objectContaining({
      nombre: 'Tintura 1',
    })));
    expect(toastSuccessMock).toHaveBeenCalledWith('Máquina actualizada');
  });

  it('dado error al guardar cuando falla la API entonces muestra toast de error', async () => {
    mockFetch([]);
    mockPost.mockRejectedValueOnce(new Error('500'));
    renderComponent();
    await waitFor(() => expect(screen.getByText('No hay máquinas registradas')).toBeInTheDocument());

    await userEvent.click(screen.getByText('+ Nueva Máquina'));
    await userEvent.type(screen.getByPlaceholderText('Ej: Máquina de Hilado 01'), 'X');
    await userEvent.click(screen.getByText('Guardar'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al guardar la máquina'));
  });

  it('dado eliminar cuando la justificacion tiene menos de 10 caracteres entonces el boton eliminar esta deshabilitado', async () => {
    mockFetch([MAQUINA_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Eliminar'));
    await userEvent.type(screen.getByPlaceholderText('Ingrese el motivo de la eliminación...'), 'corta');

    // Dos botones "Eliminar" coexisten: el de la fila y el AlertDialogAction
    // del diálogo (portal, se agrega después en el DOM) — el último es el del diálogo.
    const botonesEliminar = screen.getAllByRole('button', { name: 'Eliminar' });
    expect(botonesEliminar.at(-1)).toBeDisabled();
  });

  it('dado justificacion valida cuando confirma eliminar entonces llama a la API', async () => {
    mockFetch([MAQUINA_1]);
    mockDelete.mockResolvedValueOnce({});
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Eliminar'));
    await userEvent.type(
      screen.getByPlaceholderText('Ingrese el motivo de la eliminación...'),
      'Máquina dada de baja definitivamente',
    );
    const botonesEliminar = screen.getAllByRole('button', { name: 'Eliminar' });
    await userEvent.click(botonesEliminar.at(-1)!);

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/maquinas/1/', {
      data: { justificacion: 'Máquina dada de baja definitivamente' },
    }));
    expect(toastSuccessMock).toHaveBeenCalledWith('Máquina eliminada');
  });
});
