import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BuscadorLotes } from './BuscadorLotes';

// Sin test propio hasta ahora — solo se ejercitaba indirectamente vía
// EmpaquetadoDashboard.test.tsx (role='empaquetado', que además nunca monta
// ReetiquetarModal porque no es supervisor). Aquí se monta el componente
// aislado y se cubren búsqueda, filtros, paginación y las acciones por fila.

const mockRole = { current: 'jefe_area' as string | null };
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({
    profile: mockRole.current ? { role: mockRole.current, user: { id: 1, username: 'u' } } : null,
  }),
}));

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: any[]) => toastErrorMock(...args), success: vi.fn() },
}));

// Los 3 modales de acción se mockean como cajas negras — ya tienen su propio
// test (ReimprimirModal/HistorialEtiquetasModal/ReetiquetarModal.test.tsx).
vi.mock('./ReimprimirModal', () => ({ ReimprimirModal: () => null }));
vi.mock('./HistorialEtiquetasModal', () => ({ HistorialEtiquetasModal: () => null }));
vi.mock('./ReetiquetarModal', () => ({ ReetiquetarModal: () => null }));

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

function makeLote(overrides: Partial<any> = {}) {
  return {
    id: 1, codigo_lote: 'L-001', hora_final: '2026-01-01T10:00:00Z',
    turno: 'Dia', peso_neto_producido: 50, clasificacion_calidad: 'primera',
    ...overrides,
  };
}

describe('BuscadorLotes', () => {
  beforeEach(() => {
    mockRole.current = 'jefe_area';
    mockGet.mockReset();
    toastErrorMock.mockReset();
  });

  it('dado sin busqueda cuando renderiza entonces no muestra tabla de resultados', () => {
    render(<BuscadorLotes />);
    expect(screen.queryByText('No se encontraron lotes con esos filtros.')).not.toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado click en Buscar sin filtros cuando busca entonces llama al endpoint con page 1', async () => {
    mockGet.mockResolvedValue({ data: { count: 0, results: [] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/', {
      params: { page: 1, page_size: 20, ordering: '-hora_final' },
    }));
    expect(screen.getByText('No se encontraron lotes con esos filtros.')).toBeInTheDocument();
  });

  it('dado todos los filtros llenos cuando busca entonces los incluye en los params', async () => {
    mockGet.mockResolvedValue({ data: { count: 0, results: [] } });
    const { container } = render(<BuscadorLotes />);

    const [desde, hasta] = container.querySelectorAll('input[type="date"]');
    const turno = screen.getByPlaceholderText('Dia, Noche...');
    const codigo = screen.getByPlaceholderText('OP-...');
    await userEvent.type(desde, '2026-01-01');
    await userEvent.type(hasta, '2026-01-31');
    await userEvent.type(turno, 'Noche');
    await userEvent.type(codigo, 'OP-99');
    await userEvent.click(screen.getByText('Segunda Calidad'));
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/', {
      params: {
        page: 1, page_size: 20, ordering: '-hora_final',
        fecha_desde: '2026-01-01', fecha_hasta: '2026-01-31',
        turno: 'Noche', codigo_lote: 'OP-99', clasificacion_calidad: 'segunda',
      },
    }));
  });

  it('dado resultados cuando llegan entonces muestra la tabla con los datos del lote', async () => {
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote()] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    expect(screen.getByText('Dia')).toBeInTheDocument();
    expect(screen.getByText('50 kg')).toBeInTheDocument();
  });

  it('dado lote sin clasificacion de calidad cuando renderiza entonces muestra guion', async () => {
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote({ clasificacion_calidad: '' })] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    expect(screen.getByText('-')).toBeInTheDocument();
  });

  it('dado rol no supervisor cuando hay resultados entonces no muestra el boton reetiquetar', async () => {
    mockRole.current = 'empaquetado';
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote()] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    expect(screen.queryByTitle('Reetiquetar')).not.toBeInTheDocument();
  });

  it('dado rol supervisor cuando hay resultados entonces muestra el boton reetiquetar', async () => {
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote()] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    expect(screen.getByTitle('Reetiquetar')).toBeInTheDocument();
  });

  it('dado click en reimprimir y en historial cuando se activan entonces abren sus respectivos modales', async () => {
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote()] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());

    // Los modales están mockeados a null; solo verificamos que el click no falla.
    await userEvent.click(screen.getByTitle('Reimprimir'));
    await userEvent.click(screen.getByTitle('Ver historial de etiquetas'));
    await userEvent.click(screen.getByTitle('Reetiquetar'));
  });

  it('dado mas de 20 resultados cuando pagina cuando avanza entonces llama buscar con la siguiente pagina', async () => {
    const lotes = Array.from({ length: 20 }, (_, i) => makeLote({ id: i + 1, codigo_lote: `L-${i + 1}` }));
    mockGet.mockResolvedValueOnce({ data: { count: 25, results: lotes } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText(/Página 1 de 2/)).toBeInTheDocument());

    mockGet.mockResolvedValueOnce({ data: { count: 25, results: [makeLote({ id: 21, codigo_lote: 'L-21' })] } });
    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));

    await waitFor(() => expect(mockGet).toHaveBeenLastCalledWith('/lotes-produccion/', {
      params: { page: 2, page_size: 20, ordering: '-hora_final' },
    }));
  });

  it('dado en la pagina 2 cuando retrocede entonces llama buscar con la pagina anterior', async () => {
    const lotes = Array.from({ length: 20 }, (_, i) => makeLote({ id: i + 1, codigo_lote: `L-${i + 1}` }));
    mockGet.mockResolvedValueOnce({ data: { count: 25, results: lotes } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText(/Página 1 de 2/)).toBeInTheDocument());

    mockGet.mockResolvedValueOnce({ data: { count: 25, results: [makeLote({ id: 21, codigo_lote: 'L-21' })] } });
    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));
    await waitFor(() => expect(screen.getByText(/Página 2 de 2/)).toBeInTheDocument());

    mockGet.mockResolvedValueOnce({ data: { count: 25, results: lotes } });
    await userEvent.click(screen.getByRole('button', { name: /Anterior/i }));
    await waitFor(() => expect(mockGet).toHaveBeenLastCalledWith('/lotes-produccion/', {
      params: { page: 1, page_size: 20, ordering: '-hora_final' },
    }));
  });

  it('dado click en Limpiar cuando hay resultados y filtros cargados entonces resetea todo', async () => {
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote()] } });
    render(<BuscadorLotes />);
    await userEvent.type(screen.getByPlaceholderText('OP-...'), 'OP-99');
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Limpiar/i }));

    expect(screen.queryByText('L-001')).not.toBeInTheDocument();
    expect(screen.queryByText('No se encontraron lotes con esos filtros.')).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText('OP-...')).toHaveValue('');
  });

  it('dado error con detalle de fecha_desde cuando falla la busqueda entonces muestra ese mensaje', async () => {
    mockGet.mockRejectedValue({ response: { data: { fecha_desde: ['Formato inválido'] } } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Formato inválido'));
  });

  it('dado error sin detalle especifico cuando falla la busqueda entonces muestra el mensaje generico', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al buscar lotes.'));
  });
});
