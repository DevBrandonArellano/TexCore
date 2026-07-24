import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ManageLineas } from './ManageLineas';

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
  SelectValue: ({ placeholder }: any) => <span>{placeholder ?? ''}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const MAQUINA_1 = { id: 1, nombre: 'Tintura 01', estado: 'operativa', capacidad_maxima: '500.00', eficiencia_ideal: '0.85', area: 1 };
const MAQUINA_2 = { id: 2, nombre: 'Lavado 01', estado: 'operativa', capacidad_maxima: '300.00', eficiencia_ideal: '0.90', area: 1 };

const LINEA_1 = {
  id: 10,
  nombre: 'Línea Tintura',
  descripcion: 'Proceso de tintura',
  estado: 'activa',
  area: 1,
  maquinas: [1],
  maquinas_detail: [{ id: 1, nombre: 'Tintura 01', estado: 'operativa', compartida: false }],
};

function renderComponent(props: Partial<{ areaId: number; onChange: () => void }> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ManageLineas {...props} />
    </QueryClientProvider>,
  );
}

function mockFetch(lineas: any[] = [], maquinas: any[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url.startsWith('/lineas-produccion/')) return Promise.resolve({ data: { results: lineas } });
    if (url.startsWith('/maquinas/')) return Promise.resolve({ data: { results: maquinas } });
    return Promise.resolve({ data: { results: [] } });
  });
}

describe('ManageLineas', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch();
  });

  describe('lista de líneas', () => {
    it('dado sin lineas cuando monta entonces muestra mensaje vacio', async () => {
      renderComponent();

      await waitFor(() =>
        expect(screen.getByText('No hay líneas de producción registradas')).toBeInTheDocument(),
      );
    });

    it('dado lineas existentes cuando monta entonces las muestra con nombre y estado', async () => {
      mockFetch([LINEA_1]);
      renderComponent();

      await waitFor(() => expect(screen.getByText('Línea Tintura')).toBeInTheDocument());
      expect(screen.getByText('activa')).toBeInTheDocument();
    });

    it('dado lineas con maquinas_detail cuando monta entonces muestra los nombres de las maquinas', async () => {
      mockFetch([LINEA_1]);
      renderComponent();

      await waitFor(() => expect(screen.getByText('Tintura 01')).toBeInTheDocument());
    });

    it('dado linea sin maquinas_detail cuando monta entonces muestra el texto Sin maquinas', async () => {
      const lineaSinMaquinas = { ...LINEA_1, maquinas: [], maquinas_detail: [] };
      mockFetch([lineaSinMaquinas]);
      renderComponent();

      await waitFor(() => expect(screen.getByText('Sin máquinas')).toBeInTheDocument());
    });

    it('dado areaId cuando monta entonces pasa el filtro en la url', async () => {
      renderComponent({ areaId: 5 });

      await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/lineas-produccion/?area=5'));
    });
  });

  describe('crear línea', () => {
    it('dado clic en Nueva Linea cuando se abre el dialogo entonces muestra el formulario', async () => {
      renderComponent();

      await waitFor(() => expect(screen.getByRole('button', { name: /Nueva Línea/ })).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Línea/ }));

      expect(screen.getByText('Nueva Línea de Producción')).toBeInTheDocument();
    });

    it('dado nombre y area cuando se guarda entonces envia el POST con los datos correctos', async () => {
      mockFetch([], [MAQUINA_1, MAQUINA_2]);
      mockPost.mockResolvedValueOnce({ data: LINEA_1 });
      const onChange = vi.fn();
      renderComponent({ areaId: 1, onChange });

      await waitFor(() => expect(screen.getByRole('button', { name: /Nueva Línea/ })).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Línea/ }));

      await userEvent.type(screen.getByPlaceholderText(/Línea de Tintura A/), 'Mi Línea');

      // Marcar la primera máquina vía checkbox
      await waitFor(() => expect(screen.getByLabelText('Tintura 01')).toBeInTheDocument());
      await userEvent.click(screen.getByLabelText('Tintura 01'));

      mockGet.mockClear();
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith(
          '/lineas-produccion/',
          expect.objectContaining({ nombre: 'Mi Línea', area: 1, maquinas: [1] }),
        ),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Línea creada');
      expect(onChange).toHaveBeenCalled();
    });

    it('dado error al guardar cuando falla el POST entonces muestra toast de error', async () => {
      mockPost.mockRejectedValueOnce(new Error('400'));
      renderComponent({ areaId: 1 });

      await waitFor(() => expect(screen.getByRole('button', { name: /Nueva Línea/ })).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: /Nueva Línea/ }));
      await userEvent.type(screen.getByPlaceholderText(/Línea de Tintura A/), 'Línea X');
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al guardar la línea'));
    });

    it('dado boton guardar cuando nombre esta vacio entonces esta deshabilitado', async () => {
      renderComponent();

      await userEvent.click(screen.getByRole('button', { name: /Nueva Línea/ }));

      expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled();
    });

    it('dado checkbox de maquina cuando se marca y se desmarca entonces alterna la seleccion', async () => {
      mockFetch([], [MAQUINA_1]);
      renderComponent({ areaId: 1 });

      await userEvent.click(screen.getByRole('button', { name: /Nueva Línea/ }));

      await waitFor(() => expect(screen.getByLabelText('Tintura 01')).toBeInTheDocument());
      const checkbox = screen.getByLabelText('Tintura 01');

      expect(checkbox).not.toBeChecked();
      await userEvent.click(checkbox);
      expect(checkbox).toBeChecked();
      await userEvent.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });

    it('dado maquina ya en otra linea cuando se marca el checkbox entonces sigue habilitado y acepta la seleccion', async () => {
      // Una máquina puede estar en varias líneas (célula flexible) — el checkbox NO se deshabilita
      mockFetch([], [MAQUINA_1]);
      renderComponent({ areaId: 1 });

      await userEvent.click(screen.getByRole('button', { name: /Nueva Línea/ }));

      await waitFor(() => expect(screen.getByLabelText('Tintura 01')).toBeInTheDocument());
      const checkbox = screen.getByLabelText('Tintura 01');

      expect(checkbox).not.toBeDisabled();
      await userEvent.click(checkbox);
      expect(checkbox).toBeChecked();
    });
  });

  describe('editar línea', () => {
    it('dado clic en Editar cuando se abre el dialogo entonces precarga los datos de la linea', async () => {
      mockFetch([LINEA_1], [MAQUINA_1]);
      renderComponent({ areaId: 1 });

      await waitFor(() => expect(screen.getByText('Línea Tintura')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: 'Editar' }));

      expect(screen.getByText('Editar Línea')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Línea Tintura')).toBeInTheDocument();
    });

    it('dado edicion de nombre cuando se guarda entonces envia PATCH con datos actualizados', async () => {
      mockFetch([LINEA_1], [MAQUINA_1]);
      mockPatch.mockResolvedValueOnce({ data: {} });
      renderComponent({ areaId: 1 });

      await waitFor(() => expect(screen.getByText('Línea Tintura')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: 'Editar' }));

      const nombreInput = screen.getByDisplayValue('Línea Tintura');
      await userEvent.clear(nombreInput);
      await userEvent.type(nombreInput, 'Línea Tintura Actualizada');

      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

      await waitFor(() =>
        expect(mockPatch).toHaveBeenCalledWith(
          `/lineas-produccion/${LINEA_1.id}/`,
          expect.objectContaining({ nombre: 'Línea Tintura Actualizada' }),
        ),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Línea actualizada');
    });
  });

  describe('eliminar línea', () => {
    it('dado clic en Eliminar cuando se confirma entonces envia DELETE y muestra toast', async () => {
      mockFetch([LINEA_1]);
      mockDelete.mockResolvedValueOnce({ data: {} });
      const onChange = vi.fn();
      renderComponent({ areaId: 1, onChange });

      await waitFor(() => expect(screen.getByText('Línea Tintura')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }));

      expect(screen.getByText(/Esta acción eliminará "Línea Tintura"/)).toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: /^Eliminar$/ }));

      await waitFor(() =>
        expect(mockDelete).toHaveBeenCalledWith(`/lineas-produccion/${LINEA_1.id}/`),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Línea eliminada');
      expect(onChange).toHaveBeenCalled();
    });

    it('dado clic en Cancelar en el dialogo de eliminar cuando cancela entonces no llama al DELETE', async () => {
      mockFetch([LINEA_1]);
      renderComponent({ areaId: 1 });

      await waitFor(() => expect(screen.getByText('Línea Tintura')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }));
      await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

      expect(mockDelete).not.toHaveBeenCalled();
    });

    it('dado error al eliminar cuando falla el DELETE entonces muestra toast de error', async () => {
      mockFetch([LINEA_1]);
      mockDelete.mockRejectedValueOnce(new Error('500'));
      renderComponent({ areaId: 1 });

      await waitFor(() => expect(screen.getByText('Línea Tintura')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }));
      await userEvent.click(screen.getByRole('button', { name: /^Eliminar$/ }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar'));
    });
  });
});
