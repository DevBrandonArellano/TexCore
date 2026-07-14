import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TintoreroDashboard } from './TintoreroDashboard';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    put: (...args: any[]) => mockPut(...args),
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

vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: { user: { id: 1, username: 'tintorero1' } } }),
}));

vi.mock('./FormulaQuimica', () => ({
  FormulaQuimica: (props: any) => (
    <div data-testid="formula-quimica-mock">
      <span>formulas-count:{props.formulas.length}</span>
      <span>quimicos-count:{props.quimicos.length}</span>
      <span>loading:{String(props.loading)}</span>
      <span>can-delete:{String(props.canDelete)}</span>
      <button onClick={() => props.onFormulaCreate({ codigo: 'F1', nombre_color: 'Rojo', estado: 'ACTIVO', fases: [] })}>
        crear-formula
      </button>
      <button onClick={() => props.onFormulaUpdate(1, { codigo: 'F1', nombre_color: 'Rojo', estado: 'ACTIVO', fases: [] })}>
        actualizar-formula
      </button>
      <button onClick={() => props.onFormulaDuplicate(1)}>duplicar-formula</button>
      <button onClick={() => props.onFormulaDelete(1)}>eliminar-formula</button>
      <button onClick={() => props.onExportDosificador(1)}>exportar-formula</button>
    </div>
  ),
}));

vi.mock('./StockQuimicosDashboard', () => ({
  StockQuimicosDashboard: () => <div data-testid="stock-quimicos-mock">Stock Mock</div>,
}));

const FORMULA_1 = { id: 1, codigo: 'F1', nombre_color: 'Rojo Carmesí' };
const QUIMICO_1 = { id: 1, codigo: 'Q1', descripcion: 'Soda Cáustica' };

function mockFetch(formulas: any = [], quimicos: any = []) {
  mockGet.mockImplementation((url: string) => {
    if (url.startsWith('/formula-colors/')) return Promise.resolve({ data: formulas });
    if (url === '/chemicals/') return Promise.resolve({ data: quimicos });
    return Promise.resolve({ data: [] });
  });
}

describe('TintoreroDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPut.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  const renderAt = (path: string) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <TintoreroDashboard />
      </MemoryRouter>,
    );

  it('dado que el perfil esta cargado cuando monta entonces muestra el saludo con el nombre de usuario', async () => {
    mockFetch([], []);
    renderAt('/tintoreria');

    expect(screen.getByText(/Bienvenido, tintorero1/)).toBeInTheDocument();
  });

  it('dado datos aun no resueltos cuando monta entonces pasa loading en true al hijo FormulaQuimica', async () => {
    mockGet.mockImplementation(() => new Promise(() => {}));
    renderAt('/tintoreria');

    expect(screen.getByText('loading:true')).toBeInTheDocument();
    expect(screen.getByText('formulas-count:0')).toBeInTheDocument();
    expect(screen.getByText('quimicos-count:0')).toBeInTheDocument();
  });

  it('dado formulas y quimicos existentes cuando carga entonces los pasa al hijo FormulaQuimica y desactiva loading', async () => {
    mockFetch([FORMULA_1], [QUIMICO_1]);
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    expect(screen.getByText('formulas-count:1')).toBeInTheDocument();
    expect(screen.getByText('quimicos-count:1')).toBeInTheDocument();
    expect(screen.getByText('can-delete:false')).toBeInTheDocument();
  });

  it('dado respuesta paginada con resultados cuando carga entonces extrae el arreglo results', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/formula-colors/')) return Promise.resolve({ data: { results: [FORMULA_1, FORMULA_1] } });
      if (url === '/chemicals/') return Promise.resolve({ data: { results: [QUIMICO_1] } });
      return Promise.resolve({ data: [] });
    });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('formulas-count:2')).toBeInTheDocument());
    expect(screen.getByText('quimicos-count:1')).toBeInTheDocument();
  });

  it('dado error en la peticion cuando falla la API entonces muestra un toast de error y deja de cargar', async () => {
    mockGet.mockRejectedValue(new Error('500'));
    renderAt('/tintoreria');

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudieron cargar los datos.'));
    expect(screen.getByText('loading:false')).toBeInTheDocument();
    expect(screen.getByText('formulas-count:0')).toBeInTheDocument();
  });

  it('dado filtros de estado y sustrato en la url cuando carga entonces los envia como query params al endpoint de formulas', async () => {
    mockFetch([], []);
    renderAt('/tintoreria?estado=ACTIVO&sustrato=ALGODON');

    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith('/formula-colors/?estado=ACTIVO&tipo_sustrato=ALGODON'),
    );
  });

  it('dado pathname sin stock cuando monta entonces la pestaña activa es formulas y se muestra su contenido', async () => {
    mockFetch([], []);
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    expect(screen.getByRole('tab', { name: 'Fórmulas Químicas' })).toHaveAttribute('data-state', 'active');
    expect(screen.getByRole('tab', { name: 'Stock Disponible' })).toHaveAttribute('data-state', 'inactive');
    expect(screen.getByTestId('formula-quimica-mock')).toBeInTheDocument();
  });

  it('dado pathname que contiene stock cuando monta entonces la pestaña activa es stock y se muestra su contenido', async () => {
    mockFetch([], []);
    renderAt('/tintoreria/stock');

    await waitFor(() => expect(screen.getByTestId('stock-quimicos-mock')).toBeInTheDocument());
    expect(screen.getByRole('tab', { name: 'Stock Disponible' })).toHaveAttribute('data-state', 'active');
    expect(screen.getByRole('tab', { name: 'Fórmulas Químicas' })).toHaveAttribute('data-state', 'inactive');
    expect(screen.getByTestId('stock-quimicos-mock')).toBeInTheDocument();
  });

  it('dado clic en crear formula cuando la peticion tiene exito entonces muestra toast y refresca los datos', async () => {
    mockFetch([], []);
    mockPost.mockResolvedValueOnce({ data: {} });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    mockGet.mockClear();

    screen.getByText('crear-formula').click();

    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Formula creada exitosamente.'));
    expect(mockPost).toHaveBeenCalledWith('/formula-colors/', expect.objectContaining({ codigo: 'F1' }));
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it('dado clic en crear formula cuando la peticion falla entonces muestra un toast de error con el detalle', async () => {
    mockFetch([], []);
    mockPost.mockRejectedValueOnce({ response: { data: { codigo: ['ya existe'] } } });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('crear-formula').click();

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith(JSON.stringify({ codigo: ['ya existe'] })),
    );
  });

  it('dado clic en actualizar formula cuando la peticion tiene exito entonces muestra toast y refresca los datos', async () => {
    mockFetch([], []);
    mockPut.mockResolvedValueOnce({ data: {} });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('actualizar-formula').click();

    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Formula actualizada exitosamente.'));
    expect(mockPut).toHaveBeenCalledWith('/formula-colors/1/', expect.objectContaining({ codigo: 'F1' }));
  });

  it('dado clic en duplicar formula cuando la peticion tiene exito entonces refresca los datos', async () => {
    mockFetch([], []);
    mockPost.mockResolvedValueOnce({ data: {} });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    mockGet.mockClear();

    screen.getByText('duplicar-formula').click();

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/formula-colors/1/duplicar/'));
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it('dado clic en eliminar formula cuando el usuario confirma entonces elimina y muestra un toast de exito', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockFetch([], []);
    mockDelete.mockResolvedValueOnce({ data: {} });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('eliminar-formula').click();

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/formula-colors/1/'));
    expect(toastSuccessMock).toHaveBeenCalledWith('Formula eliminada.');
  });

  it('dado clic en eliminar formula cuando el usuario cancela entonces no elimina nada', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    mockFetch([], []);
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('eliminar-formula').click();

    await waitFor(() => expect(mockDelete).not.toHaveBeenCalled());
  });

  it('dado clic en exportar dosificador cuando la peticion tiene exito entonces muestra un toast de exito', async () => {
    mockFetch([], []);
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/formula-colors/') && url.includes('exportar-dosificador')) {
        return Promise.resolve({ data: { foo: 'bar' } });
      }
      if (url.startsWith('/formula-colors/')) return Promise.resolve({ data: [] });
      if (url === '/chemicals/') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    const createObjectURL = vi.fn(() => 'blob:mock-url');
    const revokeObjectURL = vi.fn();
    window.URL.createObjectURL = createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURL;

    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('exportar-formula').click();

    await waitFor(() =>
      expect(toastSuccessMock).toHaveBeenCalledWith('Archivo exportado para Dosificadora (Infotint).'),
    );
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('dado clic en crear formula cuando la peticion falla sin detalle entonces muestra un toast de error generico', async () => {
    mockFetch([], []);
    mockPost.mockRejectedValueOnce(new Error('fallo de red'));
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('crear-formula').click();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear la formula.'));
  });

  it('dado clic en actualizar formula cuando la peticion falla entonces muestra un toast de error con el detalle', async () => {
    mockFetch([], []);
    mockPut.mockRejectedValueOnce({ response: { data: { estado: ['invalido'] } } });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('actualizar-formula').click();

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith(JSON.stringify({ estado: ['invalido'] })),
    );
  });

  it('dado clic en actualizar formula cuando la peticion falla sin detalle entonces muestra un toast de error generico', async () => {
    mockFetch([], []);
    mockPut.mockRejectedValueOnce(new Error('fallo de red'));
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('actualizar-formula').click();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar la formula.'));
  });

  it('dado clic en duplicar formula cuando la peticion falla entonces muestra un toast de error', async () => {
    mockFetch([], []);
    mockPost.mockRejectedValueOnce(new Error('fallo de red'));
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('duplicar-formula').click();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al duplicar la formula.'));
  });

  it('dado clic en eliminar formula cuando la peticion falla entonces muestra un toast de error', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockFetch([], []);
    mockDelete.mockRejectedValueOnce(new Error('fallo de red'));
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('eliminar-formula').click();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar la formula.'));
  });

  it('dado clic en exportar dosificador cuando la peticion falla entonces muestra un toast de error', async () => {
    mockFetch([], []);
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/formula-colors/') && url.includes('exportar-dosificador')) {
        return Promise.reject(new Error('fallo de red'));
      }
      if (url.startsWith('/formula-colors/')) return Promise.resolve({ data: [] });
      if (url === '/chemicals/') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    screen.getByText('exportar-formula').click();

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith('Error al exportar datos al dosificador.'),
    );
  });

  it('dado respuesta de formulas y quimicos sin arreglo ni resultados cuando carga entonces usa arreglos vacios por defecto', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/formula-colors/')) return Promise.resolve({ data: {} });
      if (url === '/chemicals/') return Promise.resolve({ data: {} });
      return Promise.resolve({ data: [] });
    });
    renderAt('/tintoreria');

    await waitFor(() => expect(screen.getByText('loading:false')).toBeInTheDocument());
    expect(screen.getByText('formulas-count:0')).toBeInTheDocument();
    expect(screen.getByText('quimicos-count:0')).toBeInTheDocument();
  });
});
