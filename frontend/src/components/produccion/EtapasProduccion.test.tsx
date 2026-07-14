import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EtapasProduccion } from './EtapasProduccion';

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

const MAQUINA = { id: 1, nombre: 'Máquina Tintura A' };
const BODEGA_ENTRADA = { id: 2, nombre: 'Bodega MP' };
const BODEGA_SALIDA = { id: 3, nombre: 'Bodega PT' };

const ETAPA_1 = {
  id: 10,
  area: 5,
  nombre: 'Teñido',
  orden: 1,
  maquina: { id: 1, nombre: 'Máquina Tintura A' },
  bodega_entrada: { id: 2, nombre: 'Bodega MP' },
  bodega_salida: { id: 3, nombre: 'Bodega PT' },
  tiempo_procesamiento_minutos: 90,
};

function mockFetchOk(etapas: any[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url.startsWith('/etapas-produccion/')) return Promise.resolve({ data: { results: etapas } });
    if (url.startsWith('/maquinas/')) return Promise.resolve({ data: { results: [MAQUINA] } });
    if (url === '/bodegas/') return Promise.resolve({ data: { results: [BODEGA_ENTRADA, BODEGA_SALIDA] } });
    return Promise.resolve({ data: { results: [] } });
  });
}

describe('EtapasProduccion', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado carga inicial cuando monta entonces muestra estado de carga', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<EtapasProduccion areaId={5} />);
    expect(screen.getByText('Cargando etapas...')).toBeInTheDocument();
  });

  it('dado sin etapas cuando carga entonces muestra mensaje vacio', async () => {
    mockFetchOk([]);
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(
      screen.getByText('No hay etapas configuradas. Crea la primera etapa para comenzar.'),
    ).toBeInTheDocument());
  });

  it('dado error al cargar cuando falla el fetch entonces muestra toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar etapas de producción'));
  });

  it('dado etapas existentes cuando carga entonces las muestra con sus detalles', async () => {
    mockFetchOk([ETAPA_1]);
    render(<EtapasProduccion areaId={5} />);

    await waitFor(() => expect(screen.getByText('Teñido')).toBeInTheDocument());
    expect(screen.getByText('Etapa 1')).toBeInTheDocument();
    expect(screen.getByText('Máquina Tintura A')).toBeInTheDocument();
    expect(screen.getByText('Bodega MP')).toBeInTheDocument();
    expect(screen.getByText('Bodega PT')).toBeInTheDocument();
    expect(screen.getByText('90 minutos')).toBeInTheDocument();
  });

  it('dado crear nueva etapa cuando abre el dialogo entonces sugiere el siguiente orden secuencial', async () => {
    mockFetchOk([ETAPA_1]);
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(screen.getByText('Teñido')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Etapa'));

    expect(screen.getByText('Nueva Etapa de Producción')).toBeInTheDocument();
    expect(screen.getByLabelText('Orden Secuencial')).toHaveValue(2);
  });

  it('dado datos validos cuando crea una etapa entonces envia el payload correcto', async () => {
    mockFetchOk([]);
    mockPost.mockResolvedValueOnce({ data: { id: 20 } });
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(screen.getByText(/No hay etapas configuradas/)).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Etapa'));
    await userEvent.type(screen.getByLabelText('Nombre de la Etapa'), 'Secado');
    await userEvent.click(screen.getByText('Máquina Tintura A'));
    await userEvent.click(screen.getAllByText('Bodega MP')[0]);
    await userEvent.click(screen.getAllByText('Bodega PT')[1]);
    await userEvent.click(screen.getByText('Crear Etapa'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/etapas-produccion/', expect.objectContaining({
      area: 5,
      nombre: 'Secado',
      maquina: 1,
      bodega_entrada: 2,
      bodega_salida: 3,
    })));
    expect(toastSuccessMock).toHaveBeenCalledWith('Etapa creada correctamente');
  });

  it('dado editar una etapa existente cuando abre el dialogo entonces precarga sus datos', async () => {
    mockFetchOk([ETAPA_1]);
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(screen.getByText('Teñido')).toBeInTheDocument());

    // El botón editar es el primer botón "ghost" dentro de la tarjeta de la etapa
    // (índice 1: el índice 0 es "Nueva Etapa" del header).
    const editarBtn = screen.getAllByRole('button')[1];
    await userEvent.click(editarBtn);

    expect(screen.getByText('Editar Etapa')).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre de la Etapa')).toHaveValue('Teñido');
  });

  it('dado guardar con error cuando falla la API entonces muestra toast de error', async () => {
    mockFetchOk([]);
    mockPost.mockRejectedValueOnce(new Error('500'));
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(screen.getByText(/No hay etapas configuradas/)).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Etapa'));
    await userEvent.type(screen.getByLabelText('Nombre de la Etapa'), 'Secado');
    await userEvent.click(screen.getByText('Crear Etapa'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al guardar la etapa'));
  });

  it('dado eliminar sin confirmar cuando se cancela el confirm entonces no llama a la API', async () => {
    mockFetchOk([ETAPA_1]);
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(screen.getByText('Teñido')).toBeInTheDocument());

    const botones = screen.getAllByRole('button');
    await userEvent.click(botones[botones.length - 1]);

    expect(mockDelete).not.toHaveBeenCalled();
  });

  it('dado eliminar confirmado cuando se acepta entonces elimina la etapa', async () => {
    mockFetchOk([ETAPA_1]);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockDelete.mockResolvedValueOnce({});
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(screen.getByText('Teñido')).toBeInTheDocument());

    const botones = screen.getAllByRole('button');
    await userEvent.click(botones[botones.length - 1]);

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/etapas-produccion/10/'));
    expect(toastSuccessMock).toHaveBeenCalledWith('Etapa eliminada correctamente');
  });

  it('dado cancelar en el dialogo cuando se presiona entonces lo cierra', async () => {
    mockFetchOk([]);
    render(<EtapasProduccion areaId={5} />);
    await waitFor(() => expect(screen.getByText(/No hay etapas configuradas/)).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Etapa'));
    await userEvent.click(screen.getByText('Cancelar'));

    expect(screen.queryByText('Nueva Etapa de Producción')).not.toBeInTheDocument();
  });
});
