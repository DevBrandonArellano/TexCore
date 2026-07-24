import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { StockQuimicosDashboard } from './StockQuimicosDashboard';

const mockGet = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
  },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: vi.fn(),
  },
}));

vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: { user: { id: 1, sede: 3 } } }),
}));

const QUIMICO_OK = {
  producto_id: 1,
  producto_codigo: 'QUI-001',
  producto_descripcion: 'Soda Cáustica',
  cantidad: 120.5,
  stock_minimo: 50,
  alerta: false,
  bodega_nombre: 'Bodega Principal',
};

const QUIMICO_ALERTA = {
  producto_id: 2,
  producto_codigo: 'QUI-002',
  producto_descripcion: 'Sulfato de Sodio',
  cantidad: 10,
  stock_minimo: 30,
  alerta: true,
  bodega_nombre: 'Bodega Principal',
};

describe('StockQuimicosDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    toastErrorMock.mockReset();
  });

  it('dado que carga cuando la peticion esta pendiente entonces muestra estado de carga', async () => {
    mockGet.mockImplementation(() => new Promise(() => {}));
    render(<StockQuimicosDashboard />);

    expect(screen.getByText('Cargando...')).toBeInTheDocument();
  });

  it('dado sin quimicos cuando carga entonces muestra mensaje vacio', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    render(<StockQuimicosDashboard />);

    await waitFor(() => expect(screen.getByText('Sin químicos registrados')).toBeInTheDocument());
  });

  it('dado quimicos existentes cuando carga entonces lista codigo, descripcion, disponible y minimo reales', async () => {
    mockGet.mockResolvedValueOnce({ data: [QUIMICO_OK] });
    render(<StockQuimicosDashboard />);

    await waitFor(() => expect(screen.getByText('QUI-001')).toBeInTheDocument());
    expect(screen.getByText('Soda Cáustica')).toBeInTheDocument();
    expect(screen.getByText('120.500')).toBeInTheDocument();
    expect(screen.getByText('50.000')).toBeInTheDocument();
    expect(screen.queryByText('NaN')).not.toBeInTheDocument();
  });

  it('dado un quimico sin alerta cuando carga entonces muestra badge OK', async () => {
    mockGet.mockResolvedValueOnce({ data: [QUIMICO_OK] });
    render(<StockQuimicosDashboard />);

    await waitFor(() => expect(screen.getByText('QUI-001')).toBeInTheDocument());
    expect(screen.getByText('OK')).toBeInTheDocument();
    expect(screen.queryByText('STOCK BAJO')).not.toBeInTheDocument();
  });

  it('dado un quimico con alerta cuando carga entonces muestra badge de stock bajo y contador', async () => {
    mockGet.mockResolvedValueOnce({ data: [QUIMICO_ALERTA] });
    render(<StockQuimicosDashboard />);

    await waitFor(() => expect(screen.getByText('QUI-002')).toBeInTheDocument());
    expect(screen.getByText('STOCK BAJO')).toBeInTheDocument();
    expect(screen.getByText(/1 químicos con stock bajo/)).toBeInTheDocument();
  });

  it('dado mezcla de quimicos cuando carga entonces las tarjetas resumen reflejan el conteo correcto', async () => {
    mockGet.mockResolvedValueOnce({ data: [QUIMICO_OK, QUIMICO_ALERTA] });
    render(<StockQuimicosDashboard />);

    await waitFor(() => expect(screen.getByText('QUI-001')).toBeInTheDocument());
    expect(screen.getByText('Total Químicos').closest('div')?.parentElement?.textContent).toContain('2');
  });

  it('dado error en la peticion cuando falla la API entonces muestra estado vacio y toast de error', async () => {
    mockGet.mockRejectedValueOnce(new Error('500'));
    render(<StockQuimicosDashboard />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo cargar el stock de químicos.'));
    expect(screen.getByText('Sin químicos registrados')).toBeInTheDocument();
  });
});
