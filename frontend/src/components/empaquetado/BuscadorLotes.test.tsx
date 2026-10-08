import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
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
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: { error: (...args: unknown[]) => toastErrorMock(...args), success: vi.fn() },
}));

// Los 3 modales de acción se mockean como cajas negras — ya tienen su propio
// test (ReimprimirModal/HistorialEtiquetasModal/ReetiquetarModal.test.tsx).
vi.mock('./ReimprimirModal', () => ({ ReimprimirModal: () => null }));
vi.mock('./HistorialEtiquetasModal', () => ({ HistorialEtiquetasModal: () => null }));
const reetiquetarProps: { onReetiquetado?: (zpl: string) => void } = {};
vi.mock('./ReetiquetarModal', () => ({
  ReetiquetarModal: (props: { onReetiquetado?: (zpl: string) => void }) => {
    reetiquetarProps.onReetiquetado = props.onReetiquetado;
    return null;
  },
}));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: import('react').ComponentProps<typeof import('../ui/select').Select>) => (
    <SelectCtx.Provider value={onValueChange ?? (() => {})}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectTrigger>) => <div>{children}</div>,
  SelectValue: ({ placeholder }: import('react').ComponentProps<typeof import('../ui/select').SelectValue>) => <span>{placeholder}</span>,
  SelectContent: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectContent>) => <div>{children}</div>,
  SelectItem: ({ children, value }: import('react').ComponentProps<typeof import('../ui/select').SelectItem>) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

/** Los controles de paginación se buscan dentro de su `nav`: `getByRole` sobre toda la
 * tabla calcula el nombre accesible de cada botón de fila y vuelve lenta la prueba. */
const paginacion = () => screen.getByRole('navigation', { name: 'Paginación' });

function makeLote(overrides: Record<string, unknown> = {}) {
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
      params: { page: 1, page_size: 120, ordering: '-hora_final' },
    }));
    expect(screen.getByText('No se encontraron lotes con esos filtros.')).toBeInTheDocument();
  });

  it('dado todos los filtros llenos cuando busca entonces los incluye en los params', async () => {
    mockGet.mockResolvedValue({ data: { count: 0, results: [] } });
    const { container } = render(<BuscadorLotes />);

    const [desde, hasta] = Array.from(container.querySelectorAll('input[type="date"]'));
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
        page: 1, page_size: 120, ordering: '-hora_final',
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

  it('dado resultados de un bloque cuando navega dentro de él entonces no vuelve a consultar', async () => {
    const lotes = Array.from({ length: 60 }, (_, i) => makeLote({ id: i + 1, codigo_lote: `L-${i + 1}` }));
    mockGet.mockResolvedValueOnce({ data: { count: 60, results: lotes } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText(/Página 1 de 2/)).toBeInTheDocument());

    await userEvent.click(within(paginacion()).getByRole('button', { name: /Siguiente/i }));
    expect(await screen.findByText('L-31')).toBeInTheDocument();
    await userEvent.click(within(paginacion()).getByRole('button', { name: /Anterior/i }));
    expect(await screen.findByText('L-1')).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it('dado mas de 120 resultados cuando llega a la ultima pagina del bloque entonces precarga el siguiente bloque', async () => {
    const bloque1 = Array.from({ length: 120 }, (_, i) => makeLote({ id: i + 1, codigo_lote: `L-${i + 1}` }));
    const bloque2 = Array.from({ length: 30 }, (_, i) => makeLote({ id: i + 121, codigo_lote: `L-${i + 121}` }));
    mockGet
      .mockResolvedValueOnce({ data: { count: 150, results: bloque1 } })
      .mockResolvedValueOnce({ data: { count: 150, results: bloque2 } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText(/Página 1 de 5/)).toBeInTheDocument());

    const irA = within(paginacion()).getByLabelText('Ir a la página');
    await userEvent.clear(irA);
    await userEvent.type(irA, '4{Enter}');

    await waitFor(() => expect(mockGet).toHaveBeenLastCalledWith('/lotes-produccion/', {
      params: { page: 2, page_size: 120, ordering: '-hora_final' },
    }));
    await userEvent.click(within(paginacion()).getByRole('button', { name: /Siguiente/i }));
    expect(await screen.findByText('L-121')).toBeInTheDocument();
  });

  it('dado una busqueda nueva cuando se pulsa Buscar otra vez entonces vuelve a consultar desde la pagina 1', async () => {
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote()] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it('dado click en ver ficha cuando hay resultados entonces abre la ficha del lote', async () => {
    mockGet.mockImplementation((url: string) => url.endsWith('/genealogia/')
      ? Promise.resolve({ data: {
          lote_codigo: 'L-001', producto: 'Hilo', peso_neto: 50, peso_merma: 0, tipo_merma: null, calidad: 'Primera',
          operario: null, maquina: null, fechas: { inicio: '', final: '' },
          orden_produccion: { codigo: null, formula_color: null }, quimicos_consumidos: [],
        } })
      : Promise.resolve({ data: { count: 1, results: [makeLote()] } }));
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Ver ficha' }));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/1/genealogia/'));
  });

  it('dado un reetiquetado exitoso cuando el modal avisa entonces recarga la página visible', async () => {
    mockGet.mockResolvedValue({ data: { count: 1, results: [makeLote()] } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());

    reetiquetarProps.onReetiquetado?.('ZPL');
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
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
    mockGet.mockRejectedValue({ response: { status: 400, data: { fecha_desde: ['Formato inválido'] } } });
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('fecha_desde: Formato inválido'));
  });

  it('dado error sin detalle especifico cuando falla la busqueda entonces muestra el mensaje generico', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    render(<BuscadorLotes />);
    await userEvent.click(screen.getByRole('button', { name: /^Buscar$/i }));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudieron cargar los datos.'));
  });
});
