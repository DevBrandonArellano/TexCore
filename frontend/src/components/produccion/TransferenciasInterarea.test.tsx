import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TransferenciasInterarea } from './TransferenciasInterarea';

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

// Select de Radix no funciona bien en jsdom; se reemplaza por un mock simple
// que usa Context para no mezclar el onValueChange entre selects distintos
// que coexisten en el mismo render (origen y destino).
const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => {
  return {
    Select: ({ children, value, onValueChange }: any) => (
      <SelectCtx.Provider value={onValueChange}>
        <div data-testid="mock-select" data-value={value}>{children}</div>
      </SelectCtx.Provider>
    ),
    SelectTrigger: ({ children, id }: any) => <div data-testid={`trigger-${id}`}>{children}</div>,
    SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
    SelectContent: ({ children }: any) => <div>{children}</div>,
    SelectItem: ({ children, value }: any) => {
      const onValueChange = React.useContext(SelectCtx);
      return (
        <button onClick={() => onValueChange(value)}>{children}</button>
      );
    },
  };
});

const ORDEN_1 = { id: 1, codigo: 'OP-0001', area: 10, area_nombre: 'Tintura' };
const ORDEN_2 = { id: 2, codigo: 'OP-0002', area: 20, area_nombre: 'Empaque' };

const TRANSFERENCIA_1 = {
  id: 100,
  orden_area_origen: 1,
  orden_area_destino: 2,
  orden_area_origen_detail: ORDEN_1,
  orden_area_destino_detail: ORDEN_2,
  cantidad_transferida: 50,
  bodega_origen_nombre: 'Bodega Tintura',
  bodega_destino_nombre: 'Bodega Empaque',
  fecha_transferencia: '2026-01-15T10:00:00Z',
  usuario_responsable_nombre: 'Juan Pérez',
  observaciones: 'Sin novedades',
};

describe('TransferenciasInterarea', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado carga inicial cuando monta entonces muestra estado de carga', () => {
    mockGet.mockReturnValue(new Promise(() => {})); // nunca resuelve
    render(<TransferenciasInterarea areaId={10} />);
    expect(screen.getByText('Cargando transferencias...')).toBeInTheDocument();
  });

  it('dado sin transferencias cuando carga entonces muestra mensaje vacio', async () => {
    mockGet.mockResolvedValue({ data: { results: [] } });
    render(<TransferenciasInterarea areaId={10} />);
    await waitFor(() => expect(screen.getByText('No hay transferencias registradas aún')).toBeInTheDocument());
  });

  it('dado transferencias existentes cuando carga entonces las muestra formateadas', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/transferencias-interarea/') return Promise.resolve({ data: { results: [TRANSFERENCIA_1] } });
      return Promise.resolve({ data: { results: [] } });
    });

    render(<TransferenciasInterarea areaId={10} />);

    await waitFor(() => expect(screen.getByText(/OP-0001.*OP-0002/)).toBeInTheDocument());
    expect(screen.getByText('50 kg')).toBeInTheDocument();
    expect(screen.getByText(/De Bodega Tintura a Bodega Empaque/)).toBeInTheDocument();
    expect(screen.getByText(/Juan Pérez/)).toBeInTheDocument();
    expect(screen.getByText(/Sin novedades/)).toBeInTheDocument();
  });

  it('dado areaId cuando filtra entonces solo muestra transferencias que se originan en esa area', async () => {
    const otraTransferencia = {
      ...TRANSFERENCIA_1,
      id: 101,
      orden_area_origen_detail: { ...ORDEN_1, area: 999 },
    };
    mockGet.mockImplementation((url: string) => {
      if (url === '/transferencias-interarea/') {
        return Promise.resolve({ data: { results: [TRANSFERENCIA_1, otraTransferencia] } });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<TransferenciasInterarea areaId={10} />);

    await waitFor(() => expect(screen.getAllByText(/OP-0001.*OP-0002/)).toHaveLength(1));
  });

  it('dado error al cargar cuando falla el fetch entonces muestra toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    render(<TransferenciasInterarea areaId={10} />);
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar transferencias'));
  });

  it('dado modo jefe de area cuando abre el dialogo entonces muestra su orden fija (no select)', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/transferencias-interarea/') return Promise.resolve({ data: { results: [] } });
      if (url === '/ordenes-produccion/?area=10') return Promise.resolve({ data: { results: [ORDEN_1] } });
      return Promise.resolve({ data: { results: [ORDEN_2] } });
    });

    render(<TransferenciasInterarea areaId={10} />);
    await waitFor(() => expect(screen.getByText('No hay transferencias registradas aún')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Transferencia'));

    expect(screen.getByText('De tu Orden')).toBeInTheDocument();
    expect(screen.getByText('OP-0001')).toBeInTheDocument();
  });

  it('dado campos incompletos cuando transfiere entonces muestra error y no llama a la API', async () => {
    mockGet.mockResolvedValue({ data: { results: [] } });
    render(<TransferenciasInterarea areaId={10} />);
    await waitFor(() => expect(screen.getByText('No hay transferencias registradas aún')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Transferencia'));
    await userEvent.click(screen.getByText('Transferir'));

    expect(toastErrorMock).toHaveBeenCalledWith('Completa todos los campos');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado datos validos en modo jefe de area cuando transfiere entonces registra la transferencia', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/transferencias-interarea/') return Promise.resolve({ data: { results: [] } });
      if (url === '/ordenes-produccion/?area=10') return Promise.resolve({ data: { results: [ORDEN_1] } });
      if (url === '/ordenes-produccion/') return Promise.resolve({ data: { results: [ORDEN_2] } });
      if (url === '/ordenes-produccion/1/') return Promise.resolve({ data: { bodega_salida: 5 } });
      if (url === '/ordenes-produccion/2/') return Promise.resolve({ data: { bodega_entrada: 8 } });
      return Promise.resolve({ data: {} });
    });
    mockPost.mockResolvedValue({ data: { id: 200 } });

    render(<TransferenciasInterarea areaId={10} />);
    await waitFor(() => expect(screen.getByText('No hay transferencias registradas aún')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Transferencia'));

    // Selecciona la orden destino (único Select visible en modo jefe_area)
    await userEvent.click(screen.getByText('OP-0002 (Empaque)'));

    const cantidadInput = screen.getByPlaceholderText('100.50');
    await userEvent.type(cantidadInput, '75.5');

    await userEvent.click(screen.getByText('Transferir'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/transferencias-interarea/', {
      orden_area_origen: 1,
      orden_area_destino: 2,
      bodega_origen: 5,
      bodega_destino: 8,
      cantidad_transferida: 75.5,
      observaciones: '',
    }));
    expect(toastSuccessMock).toHaveBeenCalledWith('Transferencia registrada correctamente');
  });

  it('dado error del servidor cuando transfiere entonces muestra toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/transferencias-interarea/') return Promise.resolve({ data: { results: [] } });
      if (url === '/ordenes-produccion/?area=10') return Promise.resolve({ data: { results: [ORDEN_1] } });
      if (url === '/ordenes-produccion/') return Promise.resolve({ data: { results: [ORDEN_2] } });
      if (url === '/ordenes-produccion/1/') return Promise.resolve({ data: { bodega_salida: 5 } });
      if (url === '/ordenes-produccion/2/') return Promise.resolve({ data: { bodega_entrada: 8 } });
      return Promise.resolve({ data: {} });
    });
    mockPost.mockRejectedValue(new Error('500'));

    render(<TransferenciasInterarea areaId={10} />);
    await waitFor(() => expect(screen.getByText('No hay transferencias registradas aún')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Transferencia'));
    await userEvent.click(screen.getByText('OP-0002 (Empaque)'));
    await userEvent.type(screen.getByPlaceholderText('100.50'), '10');
    await userEvent.click(screen.getByText('Transferir'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al registrar transferencia'));
  });

  it('dado modo jefe de planta (sin areaId) cuando carga entonces muestra select de origen tambien', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/transferencias-interarea/') return Promise.resolve({ data: { results: [] } });
      return Promise.resolve({ data: { results: [ORDEN_1, ORDEN_2] } });
    });

    render(<TransferenciasInterarea />);
    await waitFor(() => expect(screen.getByText('No hay transferencias registradas aún')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Nueva Transferencia'));

    expect(screen.getByText('Orden de Origen')).toBeInTheDocument();
    expect(screen.getByText('Área Destino (Nueva Orden)')).toBeInTheDocument();
  });
});
