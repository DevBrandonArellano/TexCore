import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HistorialOrdenesTintoreria } from './HistorialOrdenesTintoreria';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: any[]) => toastErrorMock(...args), success: vi.fn() },
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

const MAQUINA_1 = { id: 4, nombre: 'Tintura #1' };
const FORMULA_1 = { id: 2, codigo: 'FORM-ROJO-001' };

const ORDEN_1 = {
  id: 1, codigo: 'OP-001', estado: 'en_proceso', formula_color_nombre: 'Rojo Intenso',
  peso_neto_requerido: '100.00', litros_bano: '1000.00', relacion_bano: '10.0000', version_formula: 2,
};
const ORDEN_2 = {
  id: 2, codigo: 'OP-002', estado: 'pendiente', formula_color_nombre: null,
  peso_neto_requerido: null, litros_bano: null, relacion_bano: null, version_formula: null,
};

const DESCARGA_1 = {
  id: 9, fecha_descarga: '2026-09-25T10:00:00Z', producto_descripcion: 'Colorante Rojo',
  cantidad_calculada_kg: '2.500000', estado: 'aplicada',
};

function mockApi({ ordenes = [ORDEN_1], maquinas = [MAQUINA_1], formulas = [FORMULA_1], descargas = [DESCARGA_1] }: any = {}) {
  mockGet.mockImplementation((url: string) => {
    if (url === '/maquinas/') return Promise.resolve({ data: maquinas });
    if (url === '/formula-colors/') return Promise.resolve({ data: formulas });
    if (url.includes('/descargas-quimico/')) return Promise.resolve({ data: descargas });
    if (url.includes('/ordenes-produccion/historial/')) return Promise.resolve({ data: ordenes });
    return Promise.reject(new Error('url no esperada: ' + url));
  });
}

describe('HistorialOrdenesTintoreria', () => {
  beforeEach(() => { mockGet.mockReset(); toastErrorMock.mockReset(); });

  it('dado ordenes existentes cuando monta entonces las lista con sus datos de bano y version', async () => {
    mockApi();
    render(<HistorialOrdenesTintoreria />);

    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
    expect(screen.getByText('Rojo Intenso')).toBeInTheDocument();
    expect(screen.getByText('1:10.00')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
    expect(screen.getByText('1 orden(es)')).toBeInTheDocument();
  });

  it('dado una orden sin datos de bano cuando lista entonces muestra guiones', async () => {
    mockApi({ ordenes: [ORDEN_2] });
    render(<HistorialOrdenesTintoreria />);

    await waitFor(() => expect(screen.getByText('OP-002')).toBeInTheDocument());
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('dado sin ordenes cuando carga entonces muestra el mensaje vacio', async () => {
    mockApi({ ordenes: [] });
    render(<HistorialOrdenesTintoreria />);

    await waitFor(() => expect(screen.getByText('Sin órdenes para los filtros seleccionados')).toBeInTheDocument());
  });

  it('dado error del backend cuando carga entonces muestra un toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/maquinas/' || url === '/formula-colors/') return Promise.resolve({ data: [] });
      return Promise.reject(new Error('500'));
    });
    render(<HistorialOrdenesTintoreria />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo cargar el historial de órdenes.'));
  });

  it('dado un filtro de fecha desde cuando cambia entonces reconsulta con ese parametro', async () => {
    mockApi();
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
    mockGet.mockClear();
    mockApi();

    const inputs = document.querySelectorAll('input[type="date"]');
    await userEvent.type(inputs[0] as HTMLInputElement, '2026-01-01');

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining('fecha_desde=2026-01-01')));
  });

  it('dado seleccionar una maquina cuando cambia el filtro entonces reconsulta con maquina_asignada', async () => {
    mockApi();
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
    mockGet.mockClear();
    mockApi();

    await userEvent.click(screen.getByRole('button', { name: 'Tintura #1' }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining('maquina_asignada=4')));
  });

  it('dado seleccionar una formula cuando cambia el filtro entonces reconsulta con formula_color', async () => {
    mockApi();
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
    mockGet.mockClear();
    mockApi();

    await userEvent.click(screen.getByRole('button', { name: 'FORM-ROJO-001' }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining('formula_color=2')));
  });

  it('dado seleccionar un estado cuando cambia el filtro entonces reconsulta con ese estado', async () => {
    mockApi();
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
    mockGet.mockClear();
    mockApi();

    await userEvent.click(screen.getByRole('button', { name: 'En Proceso' }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining('estado=en_proceso')));
  });

  it('dado click en actualizar cuando hace click entonces vuelve a pedir la misma pagina', async () => {
    mockApi();
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());
    mockGet.mockClear();
    mockApi();

    await userEvent.click(screen.getByRole('button', { name: /Actualizar/i }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('/ordenes-produccion/historial/')));
  });

  it('dado respuesta paginada con next y previous cuando lista entonces habilita los botones correspondientes', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/maquinas/') return Promise.resolve({ data: [] });
      if (url === '/formula-colors/') return Promise.resolve({ data: [] });
      if (url.includes('/ordenes-produccion/historial/')) {
        return Promise.resolve({ data: { count: 30, next: 'http://x/next', previous: 'http://x/prev', results: [ORDEN_1] } });
      }
      return Promise.reject(new Error('url no esperada'));
    });
    render(<HistorialOrdenesTintoreria />);

    await waitFor(() => expect(screen.getByText('30 orden(es)')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Anterior/i })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /Siguiente/i })).not.toBeDisabled();

    mockGet.mockClear();
    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('http://x/next'));
  });

  it('dado click en ver descargas de una orden cuando abre entonces muestra sus descargas', async () => {
    mockApi();
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Ver descargas de OP-001' }));

    await waitFor(() => expect(screen.getByText('Colorante Rojo')).toBeInTheDocument());
    expect(screen.getByText('2.500')).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith('/ordenes-produccion/1/descargas-quimico/');
  });

  it('dado una orden sin descargas cuando abre el dialogo entonces muestra el mensaje vacio', async () => {
    mockApi({ descargas: [] });
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Ver descargas de OP-001' }));

    await waitFor(() => expect(screen.getByText('Sin descargas registradas')).toBeInTheDocument());
  });

  it('dado error al cargar descargas cuando abre el dialogo entonces muestra un toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/maquinas/' || url === '/formula-colors/') return Promise.resolve({ data: [] });
      if (url.includes('/descargas-quimico/')) return Promise.reject(new Error('500'));
      if (url.includes('/ordenes-produccion/historial/')) return Promise.resolve({ data: [ORDEN_1] });
      return Promise.reject(new Error('url no esperada'));
    });
    render(<HistorialOrdenesTintoreria />);
    await waitFor(() => expect(screen.getByText('OP-001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Ver descargas de OP-001' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudieron cargar las descargas de la orden.'));
  });
});
