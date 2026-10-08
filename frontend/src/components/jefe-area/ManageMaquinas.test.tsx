import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ManageMaquinas } from './ManageMaquinas';
import type { User } from '../../lib/types';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => toastErrorMock(...args),
    success: (...args: unknown[]) => toastSuccessMock(...args),
  },
}));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: import('react').ComponentProps<typeof import('../ui/select').Select>) => (
    <SelectCtx.Provider value={onValueChange ?? (() => {})}>
      <div>{children}</div>
    </SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectTrigger>) => <div>{children}</div>,
  SelectValue: ({ placeholder }: import('react').ComponentProps<typeof import('../ui/select').SelectValue>) => <span>{placeholder}</span>,
  SelectContent: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectContent>) => <div>{children}</div>,
  SelectItem: ({ children, value }: import('react').ComponentProps<typeof import('../ui/select').SelectItem>) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

// El diálogo de procesos tiene sus propias pruebas; aquí solo importa con qué máquina se abre.
vi.mock('./ProcesosMaquinaDialog', () => ({
  ProcesosMaquinaDialog: ({ maquina }: { maquina: { id: number; nombre: string } | null }) =>
    maquina ? <div data-testid="procesos-dialog">procesos de {maquina.nombre} ({maquina.id})</div> : null,
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
  operarios: [5],
};

const OPERARIO_1 = { id: 5, username: 'operario1' } as User;

function renderComponent(props: Partial<React.ComponentProps<typeof ManageMaquinas>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onChange = vi.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <ManageMaquinas operarios={[OPERARIO_1]} onChange={onChange} {...props} />
    </QueryClientProvider>,
  );
  return { onChange };
}

function mockFetch(maquinas: unknown[] = []) {
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

  it('dado una maquina cuando hace clic en Procesos entonces abre la asignacion de procesos de esa maquina', async () => {
    mockFetch([MAQUINA_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());
    expect(screen.queryByTestId('procesos-dialog')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Procesos' }));

    expect(screen.getByTestId('procesos-dialog')).toHaveTextContent('procesos de Tintura 1 (1)');
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

  it('dado datos validos cuando crea una maquina entonces envia el payload correcto y avisa al panel', async () => {
    mockFetch([]);
    mockPost.mockResolvedValueOnce({ data: { id: 5 } });
    const { onChange } = renderComponent({ areaId: 7 });
    await waitFor(() => expect(screen.getByText('No hay máquinas registradas')).toBeInTheDocument());

    await userEvent.click(screen.getByText('+ Nueva Máquina'));
    await userEvent.type(screen.getByPlaceholderText('Ej: Máquina de Hilado 01'), 'Secadora 1');
    await userEvent.type(screen.getByLabelText(/Capacidad/), '200');
    await userEvent.click(screen.getByLabelText('operario1'));
    await userEvent.click(screen.getByText('Guardar'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/maquinas/', expect.objectContaining({
      nombre: 'Secadora 1',
      estado: 'operativa',
      capacidad_maxima: '200',
      operarios: [5],
      producto_merma: null,
      bodega_merma: null,
      area: 7,
    })));
    expect(toastSuccessMock).toHaveBeenCalledWith('Máquina creada');
    expect(onChange).toHaveBeenCalled();
  });

  it('dado editar una maquina existente cuando abre el dialogo entonces precarga sus datos', async () => {
    mockFetch([MAQUINA_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Editar'));

    expect(screen.getByText('Editar Máquina')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ej: Máquina de Hilado 01')).toHaveValue('Tintura 1');
    expect(screen.getByLabelText(/Capacidad/)).toHaveValue(500);
    expect(screen.getByLabelText('operario1')).toBeChecked();
  });

  it('dado editar cuando guarda entonces usa PATCH con el id de la maquina, conserva sus operarios y avisa al panel', async () => {
    mockFetch([MAQUINA_1]);
    mockPatch.mockResolvedValueOnce({ data: {} });
    const { onChange } = renderComponent();
    await waitFor(() => expect(screen.getByText('Tintura 1')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Editar'));
    await userEvent.click(screen.getByText('Guardar'));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/maquinas/1/', expect.objectContaining({
      nombre: 'Tintura 1',
      operarios: [5],
      producto_merma: null,
    })));
    expect(toastSuccessMock).toHaveBeenCalledWith('Máquina actualizada');
    expect(onChange).toHaveBeenCalled();
  });

  it('dado error al guardar cuando falla la API entonces muestra toast de error', async () => {
    mockFetch([]);
    mockPost.mockRejectedValueOnce(new Error('500'));
    renderComponent();
    await waitFor(() => expect(screen.getByText('No hay máquinas registradas')).toBeInTheDocument());

    await userEvent.click(screen.getByText('+ Nueva Máquina'));
    await userEvent.type(screen.getByPlaceholderText('Ej: Máquina de Hilado 01'), 'X');
    await userEvent.type(screen.getByLabelText(/Capacidad/), '10');
    await userEvent.click(screen.getByText('Guardar'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al guardar la máquina.'));
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

  it('dado justificacion valida cuando confirma eliminar entonces llama a la API y avisa al panel', async () => {
    mockFetch([MAQUINA_1]);
    mockDelete.mockResolvedValueOnce({});
    const { onChange } = renderComponent();
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
    expect(onChange).toHaveBeenCalled();
  });
});
