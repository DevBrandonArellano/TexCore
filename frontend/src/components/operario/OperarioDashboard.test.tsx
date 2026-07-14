import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OperarioDashboard } from './OperarioDashboard';

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

const mockUseAuth = vi.fn();
vi.mock('../../lib/auth', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../produccion/TrazabilidadProducto', () => ({
  TrazabilidadProducto: ({ ordenId, allowRegister }: any) => (
    <div data-testid="mock-trazabilidad">
      Trazabilidad de orden {ordenId} - allowRegister:{String(allowRegister)}
    </div>
  ),
}));

const ORDEN_1 = {
  id: 1,
  codigo: 'OP-0001',
  producto: 10,
  formula_color: 20,
  peso_neto_requerido: 100,
  peso_producido: 50,
  estado: 'en_proceso',
  fecha_creacion: '2026-07-01T00:00:00Z',
  fecha_modificacion: '2026-07-01T00:00:00Z',
  sede: 1,
  producto_nombre: 'Tela Azul',
  formula_color_nombre: 'Azul Marino',
  inventario_descontado: false,
  maquina_asignada: 5,
  observaciones: 'Cuidado con la tensión del hilo',
  prioridad: 'normal',
};

const ORDEN_PENDIENTE = { ...ORDEN_1, id: 2, codigo: 'OP-0002', estado: 'pendiente' };
const ORDEN_FINALIZADA = { ...ORDEN_1, id: 3, codigo: 'OP-0003', estado: 'finalizada' };

const LOTE_1 = {
  id: 100,
  orden_produccion: 1,
  codigo_lote: 'LOTE-0100',
  peso_neto_producido: 25.5,
  operario: 1,
  maquina: 5,
  turno: 'Dia',
  hora_inicio: '2026-07-10T08:00:00Z',
  hora_final: '2026-07-10T09:00:00Z',
  unidades_empaque: 3,
  peso_merma: 0,
};

const LOTE_CON_MERMA = { ...LOTE_1, id: 101, codigo_lote: 'LOTE-0101', peso_merma: 2.5 };

const LOTE_MAS_ANTIGUO = {
  ...LOTE_1,
  id: 102,
  codigo_lote: 'LOTE-0102',
  hora_final: '2026-07-09T09:00:00Z',
};

const ORDEN_CON_MEZCLA = {
  ...ORDEN_1,
  componentes_mezcla: [
    { cantidad_kg: '10.5', producto: 30, producto_detail: { codigo: 'HILO-A' } },
    { cantidad_kg: '5', producto: 31 },
  ],
};

function mockFetch(ordenes: any[] = [], lotes: any[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url === '/ordenes-produccion/') return Promise.resolve({ data: ordenes });
    if (url === '/lotes-produccion/') return Promise.resolve({ data: lotes });
    return Promise.resolve({ data: [] });
  });
}

function renderComponent() {
  return render(<OperarioDashboard />);
}

describe('OperarioDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    mockUseAuth.mockReturnValue({ profile: { user: { id: 1, username: 'operario1' } } });
  });

  it('dado que las peticiones no han resuelto cuando monta entonces muestra el estado de carga', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    renderComponent();
    expect(screen.getByText('Cargando asignaciones...')).toBeInTheDocument();
  });

  it('dado sin ordenes asignadas cuando termina de cargar entonces muestra el mensaje de vacio', async () => {
    mockFetch([], []);
    renderComponent();
    await waitFor(() =>
      expect(screen.getByText('No tienes órdenes de producción asignadas en este momento.')).toBeInTheDocument(),
    );
  });

  it('dado el perfil del operario cuando renderiza entonces lo saluda por su username', async () => {
    mockFetch([], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText(/Bienvenido, operario1/)).toBeInTheDocument());
  });

  it('dado ordenes con distintos estados cuando carga entonces solo muestra las en_proceso', async () => {
    mockFetch([ORDEN_1, ORDEN_PENDIENTE, ORDEN_FINALIZADA], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());
    expect(screen.queryByText('OP: OP-0002')).not.toBeInTheDocument();
    expect(screen.queryByText('OP: OP-0003')).not.toBeInTheDocument();
  });

  it('dado una respuesta paginada con results cuando carga entonces extrae el arreglo de ordenes', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/ordenes-produccion/') return Promise.resolve({ data: { results: [ORDEN_1] } });
      return Promise.resolve({ data: [] });
    });
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());
  });

  it('dado un error al cargar ordenes cuando falla la peticion entonces notifica el error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/ordenes-produccion/') return Promise.reject(new Error('network error'));
      return Promise.resolve({ data: [] });
    });
    renderComponent();
    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith('No se pudieron cargar tus asignaciones.'),
    );
  });

  it('dado una orden cargada cuando renderiza entonces muestra sus datos principales', async () => {
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Tela Azul')).toBeInTheDocument());
    expect(screen.getByText('Azul Marino')).toBeInTheDocument();
    expect(screen.getByText('100 Kg')).toBeInTheDocument();
    expect(screen.getByText('"Cuidado con la tensión del hilo"')).toBeInTheDocument();
  });

  it('dado un avance del 50% cuando renderiza entonces muestra el porcentaje y el pendiente calculados', async () => {
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('50.0%')).toBeInTheDocument());
    expect(screen.getByText('50.00 Kg', { selector: '.text-green-700' })).toBeInTheDocument();
    expect(screen.getByText('50.00 Kg', { selector: '.text-red-600' })).toBeInTheDocument();
  });

  it('dado un avance mayor o igual a 90% y menor a 100% cuando renderiza entonces avisa que esta casi completa', async () => {
    mockFetch([{ ...ORDEN_1, peso_producido: 95 }], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText(/¡Casi completada!/)).toBeInTheDocument());
  });

  it('dado un avance de 100% o mas cuando renderiza entonces muestra que la meta fue alcanzada', async () => {
    mockFetch([{ ...ORDEN_1, peso_producido: 100 }], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Meta alcanzada')).toBeInTheDocument());
    expect(screen.queryByText(/¡Casi completada!/)).not.toBeInTheDocument();
  });

  it('dado clic en Avance cuando abre el dialogo entonces muestra el codigo y el pendiente de la orden', async () => {
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));

    expect(screen.getByRole('heading', { name: 'Registrar Producción' })).toBeInTheDocument();
    expect(screen.getByText('OP-0001', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.getByText('50.00 Kg', { selector: 'strong' })).toBeInTheDocument();
  });

  it('dado el dialogo de registro abierto cuando el peso neto esta vacio entonces el boton de confirmar esta deshabilitado', async () => {
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));

    expect(screen.getByRole('button', { name: 'Confirmar Registro' })).toBeDisabled();
  });

  it('dado un peso neto valido cuando confirma el registro entonces envia el payload correcto y notifica exito', async () => {
    mockFetch([ORDEN_1], []);
    mockPost.mockResolvedValueOnce({ data: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));
    await userEvent.type(screen.getByLabelText(/Peso Neto \(Kg\)/), '30');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Registro' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith(
        '/ordenes-produccion/1/registrar-lote/',
        expect.objectContaining({
          peso_neto_producido: 30,
          unidades_empaque: 1,
          maquina: 5,
          operario: 1,
          peso_merma: 0,
          tipo_merma: null,
        }),
      ),
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Lote registrado exitosamente');
  });

  it('dado un error del backend con detail cuando confirma el registro entonces muestra ese mensaje', async () => {
    mockFetch([ORDEN_1], []);
    mockPost.mockRejectedValueOnce({ response: { data: { detail: 'Máquina no disponible.' } } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));
    await userEvent.type(screen.getByLabelText(/Peso Neto \(Kg\)/), '30');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Registro' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Máquina no disponible.'));
  });

  it('dado clic en Transformacion cuando abre el dialogo entonces renderiza TrazabilidadProducto con el ordenId correcto', async () => {
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Transformación/ }));

    expect(screen.getByTestId('mock-trazabilidad')).toHaveTextContent('Trazabilidad de orden 1');
    expect(screen.getByTestId('mock-trazabilidad')).toHaveTextContent('allowRegister:true');
  });

  it('dado los lotes en proceso de carga cuando no han resuelto entonces muestra el estado de carga de ingresos', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/ordenes-produccion/') return Promise.resolve({ data: [] });
      if (url === '/lotes-produccion/') return new Promise(() => {});
      return Promise.resolve({ data: [] });
    });
    renderComponent();
    await waitFor(() => expect(screen.getByText('Cargando últimos ingresos...')).toBeInTheDocument());
  });

  it('dado sin lotes registrados cuando termina de cargar entonces muestra el mensaje de vacio', async () => {
    mockFetch([], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('No hay registros de producción aún.')).toBeInTheDocument());
  });

  it('dado lotes registrados cuando renderiza entonces muestra la tabla con sus datos', async () => {
    mockFetch([ORDEN_1], [LOTE_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());
    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    expect(within(row).getByText('OP-0001')).toBeInTheDocument();
    expect(within(row).getByText('25.50')).toBeInTheDocument();
    expect(within(row).getByText('3')).toBeInTheDocument();
    expect(within(row).getByText('✓ Sin merma')).toBeInTheDocument();
    expect(screen.getByText('1 registros')).toBeInTheDocument();
  });

  it('dado un lote sin orden cargada cuando renderiza entonces usa el codigo alternativo OP-<id>', async () => {
    mockFetch([], [LOTE_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());
    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    expect(within(row).getByText('OP-1')).toBeInTheDocument();
  });

  it('dado un lote con merma cuando renderiza entonces muestra el valor numerico de merma', async () => {
    mockFetch([], [LOTE_CON_MERMA]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0101')).toBeInTheDocument());
    const row = screen.getByText('LOTE-0101').closest('tr') as HTMLElement;
    expect(within(row).getByText('2.50')).toBeInTheDocument();
  });

  it('dado clic en editar un lote cuando cambia el peso neto y guarda entonces llama a la API con el payload correcto', async () => {
    mockFetch([], [LOTE_1]);
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Editar registro'));

    const pesoInput = within(row).getAllByRole('spinbutton')[0];
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '40');
    await userEvent.click(within(row).getByTitle('Guardar'));

    await waitFor(() =>
      expect(mockPatch).toHaveBeenCalledWith('/lotes-produccion/100/', {
        peso_neto_producido: 40,
        unidades_empaque: 3,
        peso_merma: 0,
      }),
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Lote actualizado correctamente');
  });

  it('dado un peso neto invalido cuando guarda la edicion entonces muestra error y no llama a la API', async () => {
    mockFetch([], [LOTE_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Editar registro'));

    const pesoInput = within(row).getAllByRole('spinbutton')[0];
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '0');
    await userEvent.click(within(row).getByTitle('Guardar'));

    expect(toastErrorMock).toHaveBeenCalledWith('El peso neto debe ser mayor a 0.');
    expect(mockPatch).not.toHaveBeenCalled();
  });

  it('dado clic en cancelar la edicion cuando estaba editando entonces descarta los cambios y vuelve al valor original', async () => {
    mockFetch([], [LOTE_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Editar registro'));
    await userEvent.click(within(row).getByTitle('Cancelar'));

    expect(within(row).getByText('25.50')).toBeInTheDocument();
    expect(within(row).queryByRole('spinbutton')).not.toBeInTheDocument();
  });

  it('dado clic en eliminar un lote cuando no se ha escrito justificacion entonces el boton de eliminar esta deshabilitado', async () => {
    mockFetch([], [LOTE_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Eliminar y revertir'));

    expect(screen.getByRole('heading', { name: /Eliminar Registro de Producción/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Eliminar y Revertir' })).toBeDisabled();
  });

  it('dado clic en eliminar un lote cuando confirma con justificacion entonces llama al endpoint de rechazo y notifica exito', async () => {
    mockFetch([], [LOTE_1]);
    mockPost.mockResolvedValueOnce({ data: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Eliminar y revertir'));

    await userEvent.type(
      screen.getByPlaceholderText('Ej: Error de registro, lote duplicado...'),
      'Error de digitación',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar y Revertir' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith('/lotes-produccion/100/rechazar/', {
        justificacion: 'Error de digitación',
      }),
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Lote LOTE-0100 eliminado y movimientos revertidos.');
  });

  it('dado un error del backend al eliminar cuando falla entonces muestra el mensaje de error', async () => {
    mockFetch([], [LOTE_1]);
    mockPost.mockRejectedValueOnce({ response: { data: { error: { message: 'No se puede revertir stock.' } } } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Eliminar y revertir'));
    await userEvent.type(
      screen.getByPlaceholderText('Ej: Error de registro, lote duplicado...'),
      'Duplicado',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar y Revertir' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se puede revertir stock.'));
  });

  it('dado que el perfil no tiene usuario cuando monta entonces no consulta los ultimos lotes', async () => {
    mockUseAuth.mockReturnValue({ profile: null });
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());
    expect(mockGet).not.toHaveBeenCalledWith('/lotes-produccion/', expect.anything());
  });

  it('dado un error al cargar los ultimos lotes cuando falla la peticion entonces no rompe la UI y muestra el mensaje de vacio', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/ordenes-produccion/') return Promise.resolve({ data: [] });
      if (url === '/lotes-produccion/') return Promise.reject(new Error('network error'));
      return Promise.resolve({ data: [] });
    });
    renderComponent();
    await waitFor(() =>
      expect(screen.getByText('No hay registros de producción aún.')).toBeInTheDocument(),
    );
  });

  it('dado varios lotes con distinta hora_final cuando renderiza entonces los ordena del mas reciente al mas antiguo', async () => {
    mockFetch([], [LOTE_MAS_ANTIGUO, LOTE_1]);
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());
    const rows = screen.getAllByRole('row').slice(1);
    expect(within(rows[0]).getByText('LOTE-0100')).toBeInTheDocument();
    expect(within(rows[1]).getByText('LOTE-0102')).toBeInTheDocument();
  });

  it('dado una orden con requerido en cero cuando renderiza entonces el avance es 0%', async () => {
    mockFetch([{ ...ORDEN_1, peso_neto_requerido: 0 }], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('0.0%')).toBeInTheDocument());
  });

  it('dado clic en cancelar en el dialogo de registro cuando estaba abierto entonces lo cierra', async () => {
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));
    expect(screen.getByRole('heading', { name: 'Registrar Producción' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    await waitFor(() =>
      expect(screen.queryByRole('heading', { name: 'Registrar Producción' })).not.toBeInTheDocument(),
    );
  });

  it('dado el dialogo de transformacion abierto cuando se cierra entonces desmonta TrazabilidadProducto', async () => {
    mockFetch([ORDEN_1], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Transformación/ }));
    expect(screen.getByTestId('mock-trazabilidad')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Close' }));

    await waitFor(() => expect(screen.queryByTestId('mock-trazabilidad')).not.toBeInTheDocument());
  });

  it('dado cambios en unidades y bobinas del formulario de registro cuando escribe entonces refleja los valores ingresados', async () => {
    mockFetch([ORDEN_1], []);
    mockPost.mockResolvedValueOnce({ data: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));
    await userEvent.type(screen.getByLabelText(/Peso Neto \(Kg\)/), '30');

    const bobinasInput = screen.getByLabelText(/Unidades/);
    await userEvent.clear(bobinasInput);
    await userEvent.type(bobinasInput, '7');
    expect(bobinasInput).toHaveValue(7);

    await userEvent.type(screen.getByLabelText(/Desperdicio \(Kg\)/), '2');
    expect(screen.getByLabelText(/Desperdicio \(Kg\)/)).toHaveValue(2);

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Registro' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith(
        '/ordenes-produccion/1/registrar-lote/',
        expect.objectContaining({
          peso_neto_producido: 30,
          unidades_empaque: 7,
          peso_merma: 2,
        }),
      ),
    );
  });

  it('dado un error del backend con non_field_errors cuando confirma el registro entonces muestra ese mensaje', async () => {
    mockFetch([ORDEN_1], []);
    mockPost.mockRejectedValueOnce({ response: { data: { non_field_errors: ['Ya existe un lote similar.'] } } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));
    await userEvent.type(screen.getByLabelText(/Peso Neto \(Kg\)/), '30');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Registro' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Ya existe un lote similar.'));
  });

  it('dado un error del backend sin detail ni non_field_errors cuando confirma el registro entonces muestra el mensaje generico', async () => {
    mockFetch([ORDEN_1], []);
    mockPost.mockRejectedValueOnce({ response: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));
    await userEvent.type(screen.getByLabelText(/Peso Neto \(Kg\)/), '30');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Registro' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al registrar la producción'));
  });

  it('dado una orden con componentes de mezcla cuando abre el dialogo entonces muestra los lotes de entrada y permite completarlos', async () => {
    mockFetch([ORDEN_CON_MEZCLA], []);
    mockPost.mockResolvedValueOnce({ data: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('OP: OP-0001')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Avance/ }));

    expect(screen.getByText('Lotes de Entrada (Mezcla)')).toBeInTheDocument();
    expect(screen.getByText(/HILO-A — ID lote origen/)).toBeInTheDocument();
    expect(screen.getByText(/Producto 31 — ID lote origen/)).toBeInTheDocument();

    const loteOrigenInputs = screen.getAllByPlaceholderText('ID del lote de origen');
    await userEvent.type(loteOrigenInputs[0], '200');
    await userEvent.type(loteOrigenInputs[1], '201');

    const cantidadInput = screen.getByDisplayValue('10.5');
    await userEvent.clear(cantidadInput);
    await userEvent.type(cantidadInput, '11');

    await userEvent.type(screen.getByLabelText(/Peso Neto \(Kg\)/), '30');
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar Registro' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith(
        '/ordenes-produccion/1/registrar-lote/',
        expect.objectContaining({
          consumos: [
            { lote_origen_id: 200, cantidad_kg: '11', genera_nuevo_lote: true },
            { lote_origen_id: 201, cantidad_kg: '5', genera_nuevo_lote: true },
          ],
        }),
      ),
    );
  });

  it('dado clic en editar un lote cuando cambia unidades y merma y guarda entonces envia esos valores en el payload', async () => {
    mockFetch([], [LOTE_1]);
    mockPatch.mockResolvedValueOnce({ data: {} });
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Editar registro'));

    const spinbuttons = within(row).getAllByRole('spinbutton');
    const unidadesInput = spinbuttons[1];
    const mermaInput = spinbuttons[2];

    await userEvent.clear(unidadesInput);
    await userEvent.type(unidadesInput, '9');
    await userEvent.clear(mermaInput);
    await userEvent.type(mermaInput, '1.5');

    await userEvent.click(within(row).getByTitle('Guardar'));

    await waitFor(() =>
      expect(mockPatch).toHaveBeenCalledWith('/lotes-produccion/100/', {
        peso_neto_producido: 25.5,
        unidades_empaque: 9,
        peso_merma: 1.5,
      }),
    );
  });

  it('dado un error del backend al guardar la edicion cuando falla entonces muestra el mensaje de error correspondiente', async () => {
    mockFetch([], [LOTE_1]);
    mockPatch.mockRejectedValueOnce({ response: { data: { peso_neto_producido: ['Valor fuera de rango.'] } } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('LOTE-0100')).toBeInTheDocument());

    const row = screen.getByText('LOTE-0100').closest('tr') as HTMLElement;
    await userEvent.click(within(row).getByTitle('Editar registro'));

    const pesoInput = within(row).getAllByRole('spinbutton')[0];
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '40');
    await userEvent.click(within(row).getByTitle('Guardar'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Valor fuera de rango.'));
  });
});
