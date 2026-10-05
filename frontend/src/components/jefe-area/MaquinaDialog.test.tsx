import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MaquinaDialog } from './MaquinaDialog';
import type { User } from '../../lib/types';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
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

// Select de Radix reemplazado por botones: cada opción llama a onValueChange del Select que la contiene.
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
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const OPERARIO_1 = { id: 5, username: 'operario1' } as User;
const OPERARIO_2 = { id: 6, username: 'operario2' } as User;

const MAQUINA = {
  id: 1,
  nombre: 'Tintura 1',
  estado: 'operativa' as const,
  capacidad_maxima: '500.00',
  eficiencia_ideal: '0.85',
  operarios: [5],
  producto_merma: 9,
  bodega_merma: 3,
};

function mockCatalogos() {
  mockGet.mockImplementation((url: string) => {
    if (url.startsWith('/productos/')) {
      return Promise.resolve({ data: { results: [{ id: 9, codigo: 'MERMA-01', descripcion: 'Borra de algodón', tipo: 'subproducto' }] } });
    }
    if (url === '/bodegas/') return Promise.resolve({ data: { results: [{ id: 3, nombre: 'Bodega Merma' }] } });
    return Promise.resolve({ data: { results: [] } });
  });
}

function renderDialog(props: Partial<React.ComponentProps<typeof MaquinaDialog>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
  const onOpenChange = vi.fn();
  const onSaved = vi.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <MaquinaDialog
        open
        onOpenChange={onOpenChange}
        maquina={null}
        operarios={[OPERARIO_1, OPERARIO_2]}
        areaId={2}
        onSaved={onSaved}
        {...props}
      />
    </QueryClientProvider>,
  );
  return { onOpenChange, onSaved, invalidateSpy };
}

describe('MaquinaDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCatalogos();
  });

  it('dado una maquina nueva cuando abre el dialogo entonces muestra el titulo de creacion y Guardar deshabilitado', () => {
    renderDialog();

    expect(screen.getByText('Nueva Máquina')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled();
  });

  it('dado un nombre solo con espacios cuando completa la capacidad entonces Guardar sigue deshabilitado', async () => {
    renderDialog();

    await userEvent.type(screen.getByLabelText('Nombre de la Máquina'), '   ');
    await userEvent.type(screen.getByLabelText(/Capacidad/), '100');

    expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled();
  });

  it.each([
    ['0', 'capacidad en el limite inferior (0)'],
    ['-5', 'capacidad negativa'],
  ])('dado capacidad %s cuando valida el formulario entonces Guardar queda deshabilitado (%s)', async (capacidad) => {
    renderDialog();

    await userEvent.type(screen.getByLabelText('Nombre de la Máquina'), 'Secadora 1');
    await userEvent.type(screen.getByLabelText(/Capacidad/), capacidad);

    expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled();
  });

  it.each([
    ['1.01', true],
    ['-0.01', true],
    ['1', false],
    ['0', false],
  ])('dado eficiencia ideal %s cuando valida el formulario entonces Guardar deshabilitado es %s', async (eficiencia, deshabilitado) => {
    renderDialog();

    await userEvent.type(screen.getByLabelText('Nombre de la Máquina'), 'Secadora 1');
    await userEvent.type(screen.getByLabelText(/Capacidad/), '100');
    const eficienciaInput = screen.getByLabelText(/Eficiencia ideal/);
    await userEvent.clear(eficienciaInput);
    await userEvent.type(eficienciaInput, eficiencia);

    const guardar = screen.getByRole('button', { name: 'Guardar' });
    if (deshabilitado) expect(guardar).toBeDisabled();
    else expect(guardar).toBeEnabled();
  });

  it('dado datos validos cuando crea una maquina entonces envia POST con todos los campos, refresca y cierra', async () => {
    mockPost.mockResolvedValueOnce({ data: { id: 7 } });
    const { onOpenChange, onSaved, invalidateSpy } = renderDialog();

    await userEvent.type(screen.getByLabelText('Nombre de la Máquina'), '  Secadora 1  ');
    await userEvent.type(screen.getByLabelText(/Capacidad/), '120.5');
    await userEvent.click(screen.getByLabelText('operario2'));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/maquinas/', {
      nombre: 'Secadora 1',
      estado: 'operativa',
      capacidad_maxima: '120.5',
      eficiencia_ideal: '0.85',
      operarios: [6],
      producto_merma: null,
      bodega_merma: null,
      area: 2,
    }));
    expect(toastSuccessMock).toHaveBeenCalledWith('Máquina creada');
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['maquinas'] });
    expect(onSaved).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('dado sin areaId cuando crea una maquina entonces el payload no incluye area', async () => {
    mockPost.mockResolvedValueOnce({ data: { id: 7 } });
    renderDialog({ areaId: undefined });

    await userEvent.type(screen.getByLabelText('Nombre de la Máquina'), 'Secadora 1');
    await userEvent.type(screen.getByLabelText(/Capacidad/), '100');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    expect(mockPost.mock.calls[0][1]).not.toHaveProperty('area');
  });

  it('dado una maquina existente cuando abre el dialogo entonces precarga datos, operarios y merma', async () => {
    renderDialog({ maquina: MAQUINA });

    expect(screen.getByText('Editar Máquina')).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre de la Máquina')).toHaveValue('Tintura 1');
    expect(screen.getByLabelText(/Capacidad/)).toHaveValue(500);
    expect(screen.getByLabelText(/Eficiencia ideal/)).toHaveValue(0.85);
    expect(screen.getByLabelText('operario1')).toBeChecked();
    expect(screen.getByLabelText('operario2')).not.toBeChecked();
    await waitFor(() => expect(screen.getByText('MERMA-01 — Borra de algodón')).toBeInTheDocument());
  });

  it('dado una maquina con merma y operarios cuando guarda sin tocarlos entonces el PATCH los conserva', async () => {
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderDialog({ maquina: MAQUINA });

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/maquinas/1/', expect.objectContaining({
      nombre: 'Tintura 1',
      capacidad_maxima: '500.00',
      operarios: [5],
      producto_merma: 9,
      bodega_merma: 3,
    })));
    expect(toastSuccessMock).toHaveBeenCalledWith('Máquina actualizada');
  });

  it('dado una maquina sin campos de merma cargados cuando guarda entonces el PATCH no los envia', async () => {
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderDialog({
      maquina: {
        id: 1, nombre: 'Tintura 1', estado: 'operativa',
        capacidad_maxima: 500, eficiencia_ideal: 0.85, operarios: [5],
      },
    });

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockPatch).toHaveBeenCalled());
    const payload = mockPatch.mock.calls[0][1];
    expect(payload).not.toHaveProperty('producto_merma');
    expect(payload).not.toHaveProperty('bodega_merma');
  });

  it('dado merma configurada cuando elige Sin merma vendible y Sin bodega entonces envia ambos en null', async () => {
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderDialog({ maquina: MAQUINA });

    await userEvent.click(screen.getByRole('button', { name: 'Sin merma vendible' }));
    await userEvent.click(screen.getByRole('button', { name: 'Sin bodega asignada' }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/maquinas/1/', expect.objectContaining({
      producto_merma: null,
      bodega_merma: null,
    })));
  });

  it('dado una maquina sin merma cuando elige producto y bodega de merma entonces envia sus ids', async () => {
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderDialog({ maquina: { ...MAQUINA, producto_merma: null, bodega_merma: null } });

    await userEvent.click(await screen.findByRole('button', { name: 'MERMA-01 — Borra de algodón' }));
    await userEvent.click(screen.getByRole('button', { name: 'Bodega Merma' }));
    await userEvent.click(screen.getByRole('button', { name: 'Mantenimiento' }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/maquinas/1/', expect.objectContaining({
      producto_merma: 9,
      bodega_merma: 3,
      estado: 'mantenimiento',
    })));
  });

  it('dado un operario asignado cuando desmarca su checkbox entonces lo quita del guardado', async () => {
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderDialog({ maquina: MAQUINA });

    await userEvent.click(screen.getByLabelText('operario1'));
    expect(screen.getByLabelText('operario1')).not.toBeChecked();
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/maquinas/1/', expect.objectContaining({ operarios: [] })));
  });

  it('dado un rechazo 400 del backend cuando guarda entonces muestra su mensaje y no cierra', async () => {
    mockPatch.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'Nombre duplicado en el área.' } } });
    const { onOpenChange, onSaved } = renderDialog({ maquina: MAQUINA });

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Nombre duplicado en el área.'));
    expect(onSaved).not.toHaveBeenCalled();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it('dado un error sin respuesta clasificable cuando guarda entonces muestra el mensaje generico', async () => {
    mockPost.mockRejectedValueOnce(new Error('boom'));
    renderDialog();

    await userEvent.type(screen.getByLabelText('Nombre de la Máquina'), 'X');
    await userEvent.type(screen.getByLabelText(/Capacidad/), '10');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al guardar la máquina.'));
  });

  it('dado el dialogo abierto cuando hace clic en Cancelar entonces cierra sin llamar a la API', async () => {
    const { onOpenChange } = renderDialog({ maquina: MAQUINA });

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockPatch).not.toHaveBeenCalled();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado ningun operario en el area cuando abre el dialogo entonces muestra el aviso', () => {
    renderDialog({ operarios: [] });

    expect(screen.getByText('No hay operarios en esta área.')).toBeInTheDocument();
  });

  it('dado el dialogo cerrado cuando monta entonces no consulta los catalogos de merma', () => {
    renderDialog({ open: false });

    expect(mockGet).not.toHaveBeenCalled();
  });
});
