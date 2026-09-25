import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DescargasQuimicosTintoreria } from './DescargasQuimicosTintoreria';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: any[]) => toastErrorMock(...args), success: vi.fn() },
}));

let mockProfile: any = { user: { id: 1, username: 'tintorero1', sede: 2 } };
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: mockProfile }),
}));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const QUIMICO_1 = { producto_id: 19, producto_codigo: 'QMC-DET-001', producto_descripcion: 'Detergente Industrial', cantidad: 100, stock_minimo: 10, alerta: false, bodega_nombre: 'Bodega Químicos' };

const DESCARGA_1 = {
  id: 8, orden_produccion: 3, bodega_nombre: 'Bodega Químicos', cantidad_calculada_kg: '2.400000',
  estado: 'aplicada', fecha_descarga: '2026-09-25T10:00:00Z',
};

function mockApi({ quimicos = [QUIMICO_1], descargas = [DESCARGA_1] }: any = {}) {
  mockGet.mockImplementation((url: string) => {
    if (url.includes('/stock-quimicos/')) return Promise.resolve({ data: quimicos });
    if (url.includes('/descargas-quimico/')) return Promise.resolve({ data: descargas });
    return Promise.reject(new Error('url no esperada: ' + url));
  });
}

describe('DescargasQuimicosTintoreria', () => {
  beforeEach(() => {
    mockGet.mockReset();
    toastErrorMock.mockReset();
    mockProfile = { user: { id: 1, username: 'tintorero1', sede: 2 } };
  });

  it('dado sin sede en el perfil cuando monta entonces no consulta el catalogo de quimicos', () => {
    mockProfile = { user: { id: 1, username: 'sin-sede', sede: null } };
    mockApi();
    render(<DescargasQuimicosTintoreria />);
    expect(mockGet).not.toHaveBeenCalled();
    expect(screen.getByText('Elige un químico arriba para consultar sus descargas.')).toBeInTheDocument();
  });

  it('dado sin quimico seleccionado cuando monta entonces pide el catalogo y muestra el estado vacio', async () => {
    mockApi();
    render(<DescargasQuimicosTintoreria />);

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/ordenes-produccion/stock-quimicos/?sede_id=2'));
    expect(screen.getByText('Selecciona un químico para ver su historial')).toBeInTheDocument();
  });

  it('dado error al cargar el catalogo cuando falla entonces muestra un toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/stock-quimicos/')) return Promise.reject(new Error('500'));
      return Promise.reject(new Error('url no esperada'));
    });
    render(<DescargasQuimicosTintoreria />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo cargar el catálogo de químicos.'));
  });

  it('dado seleccionar un quimico cuando elige entonces consulta y lista sus descargas', async () => {
    mockApi();
    render(<DescargasQuimicosTintoreria />);
    await waitFor(() => expect(screen.getByRole('button', { name: /Detergente Industrial/ })).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Detergente Industrial/ }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      '/ordenes-produccion/descargas-quimico/?producto_id=19&sede_id=2&limit=100'));
    expect(await screen.findByText('1 descarga(s) aplicada(s)')).toBeInTheDocument();
    expect(screen.getByText('2.400')).toBeInTheDocument();
    expect(screen.getByText('Bodega Químicos')).toBeInTheDocument();
  });

  it('dado un quimico sin descargas cuando consulta entonces muestra el mensaje vacio', async () => {
    mockApi({ descargas: [] });
    render(<DescargasQuimicosTintoreria />);
    await waitFor(() => expect(screen.getByRole('button', { name: /Detergente Industrial/ })).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Detergente Industrial/ }));

    await waitFor(() => expect(screen.getByText('Sin descargas registradas para este químico')).toBeInTheDocument());
  });

  it('dado error al cargar descargas cuando falla entonces muestra un toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/stock-quimicos/')) return Promise.resolve({ data: [QUIMICO_1] });
      if (url.includes('/descargas-quimico/')) return Promise.reject(new Error('500'));
      return Promise.reject(new Error('url no esperada'));
    });
    render(<DescargasQuimicosTintoreria />);
    await waitFor(() => expect(screen.getByRole('button', { name: /Detergente Industrial/ })).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Detergente Industrial/ }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudieron cargar las descargas.'));
  });

  it('dado un quimico seleccionado cuando hace click en actualizar entonces vuelve a consultar', async () => {
    mockApi();
    render(<DescargasQuimicosTintoreria />);
    await waitFor(() => expect(screen.getByRole('button', { name: /Detergente Industrial/ })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /Detergente Industrial/ }));
    await waitFor(() => expect(screen.getByText('1 descarga(s) aplicada(s)')).toBeInTheDocument());

    mockGet.mockClear();
    mockApi();
    await userEvent.click(screen.getByRole('button', { name: /Actualizar/i }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('/descargas-quimico/')));
  });

  it('dado sin quimico seleccionado cuando renderiza entonces el boton actualizar esta deshabilitado', async () => {
    mockApi();
    render(<DescargasQuimicosTintoreria />);
    await waitFor(() => expect(screen.getByRole('button', { name: /Detergente Industrial/ })).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Actualizar/i })).toBeDisabled();
  });
});
