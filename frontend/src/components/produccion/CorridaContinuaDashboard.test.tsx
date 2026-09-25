import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CorridaContinuaDashboard } from './CorridaContinuaDashboard';

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
    success: (...args: any[]) => toastSuccessMock(...args),
    error: (...args: any[]) => toastErrorMock(...args),
  },
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

const CORRIDA_ACTIVA = {
  id: 1,
  codigo: 'CORR-2026-001',
  modalidad: 'CONTINUA',
  estado: 'en_proceso',
  turno: 'Mañana',
  fecha_jornada: '2026-09-17',
  area: 1,
  area_nombre: 'Tintorería Continua',
  maquina_principal: 1,
  maquina_principal_nombre: 'Rama 01',
  operaciones_count: 1,
};

const CORRIDA_PAUSADA = { ...CORRIDA_ACTIVA, id: 2, codigo: 'CORR-2026-002', estado: 'pausada' };

const OPERACIONES = [
  {
    id: 10,
    corrida: 1,
    numero_secuencia: 1,
    maquina: 1,
    maquina_nombre: 'Rama 01',
    operario: 2,
    operario_nombre: 'Carlos Perez',
    hora_inicio: '2026-09-17T08:00:00Z',
    estado: 'completada',
    consumos: [
      { id: 1, producto: 1, bodega_origen: 1, cantidad_consumida: '100.000', producto_codigo: 'TEL-CRUD' },
    ],
    salidas: [
      { id: 2, producto: 2, bodega_destino: 2, cantidad_neta: '95.000', lote_generado_codigo: 'LOT-ACAB-01' },
    ],
    mermas: [
      { id: 3, peso_merma: '5.000' },
    ],
  },
];

const AREAS = [{ id: 1, nombre: 'Tintorería Continua' }];
const MAQUINAS = [{ id: 1, nombre: 'Rama 01' }];
const BODEGAS = [{ id: 1, nombre: 'Bodega Materia Prima' }, { id: 2, nombre: 'Bodega Producto Terminado' }];
const PRODUCTOS = [
  { id: 1, codigo: 'TEL-CRUD', descripcion: 'Tela Cruda', tipo: 'hilo' },
  { id: 2, codigo: 'TEL-ACAB', descripcion: 'Tela Acabada', tipo: 'tela' },
];

function mockApi({
  corridas = [CORRIDA_ACTIVA], operaciones = OPERACIONES, areas = AREAS, maquinas = MAQUINAS,
  bodegas = BODEGAS, productos = PRODUCTOS,
}: any = {}) {
  mockGet.mockImplementation((url: string) => {
    if (url.includes('/corridas-produccion/')) return Promise.resolve({ data: { results: corridas } });
    if (url.includes('/operaciones-produccion/')) return Promise.resolve({ data: { results: operaciones } });
    if (url.includes('/areas/')) return Promise.resolve({ data: areas });
    if (url.includes('/maquinas/')) return Promise.resolve({ data: maquinas });
    if (url.includes('/bodegas/')) return Promise.resolve({ data: bodegas });
    if (url.includes('/productos/')) return Promise.resolve({ data: productos });
    return Promise.resolve({ data: { results: [] } });
  });
}

describe('CorridaContinuaDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    mockApi();
  });

  it('dado renderizado inicial cuando carga corrida activa entonces muestra codigo y estado', async () => {
    render(<CorridaContinuaDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Producción Continua \(MES\)/i)).toBeDefined();
      expect(screen.getByText(/CORR-2026-001/i)).toBeDefined();
      expect(screen.getByText(/EN_PROCESO/i)).toBeDefined();
    });
  });

  it('dado operaciones existentes cuando se renderiza entonces lista lote generado y cantidades', async () => {
    render(<CorridaContinuaDashboard />);

    await waitFor(() => {
      expect(screen.getByText('LOT-ACAB-01')).toBeDefined();
      expect(screen.getByText(/Carlos Perez/i)).toBeDefined();
    });
  });

  it('dado sin operaciones cuando carga entonces muestra el mensaje vacio', async () => {
    mockApi({ operaciones: [] });
    render(<CorridaContinuaDashboard />);

    await waitFor(() => expect(screen.getByText('No hay operaciones registradas aún en esta corrida.')).toBeInTheDocument());
  });

  it('dado error al cargar catalogos cuando falla entonces muestra un toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/areas/')) return Promise.reject(new Error('500'));
      if (url.includes('/corridas-produccion/')) return Promise.resolve({ data: { results: [] } });
      return Promise.resolve({ data: { results: [] } });
    });
    render(<CorridaContinuaDashboard />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar catálogos base'));
  });

  it('dado error al cargar corridas cuando falla entonces muestra un toast de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/corridas-produccion/')) return Promise.reject(new Error('500'));
      return Promise.resolve({ data: [] });
    });
    render(<CorridaContinuaDashboard />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar corridas de producción'));
  });

  it('dado varias corridas cuando hace click en otra entonces la selecciona como activa', async () => {
    mockApi({ corridas: [CORRIDA_ACTIVA, CORRIDA_PAUSADA] });
    render(<CorridaContinuaDashboard />);
    await waitFor(() => expect(screen.getByText('Otras corridas:')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /CORR-2026-002 \(pausada\)/i }));

    await waitFor(() => expect(screen.getByText('Corrida Actual: CORR-2026-002')).toBeInTheDocument());
  });

  describe('Modal Iniciar Corrida', () => {
    it('dado sin area seleccionada cuando confirma entonces muestra un error y no llama al backend', async () => {
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Nueva Corrida/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Iniciar Corrida' }));

      expect(toastErrorMock).toHaveBeenCalledWith('Seleccione un área productiva.');
      expect(mockPost).not.toHaveBeenCalled();
    });

    it('dado area maquina turno y observaciones cuando confirma entonces llama al backend con el payload', async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 9, codigo: 'CORR-2026-009', estado: 'en_proceso' } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Nueva Corrida/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Tintorería Continua' }));
      await userEvent.click(screen.getByRole('button', { name: 'Rama 01' }));
      await userEvent.click(screen.getByRole('button', { name: /Tarde/i }));
      await userEvent.type(screen.getByLabelText('Observaciones'), 'Arranque de turno');
      await userEvent.click(screen.getByRole('button', { name: 'Iniciar Corrida' }));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/corridas-produccion/iniciar-corrida/', {
        area_id: 1, maquina_principal_id: 1, modalidad: 'CONTINUA', turno: 'Tarde', observaciones: 'Arranque de turno',
      }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Corrida CORR-2026-009 iniciada exitosamente');
    });

    it('dado el backend rechaza iniciar corrida cuando falla entonces muestra el mensaje del error', async () => {
      mockPost.mockRejectedValueOnce({ response: { data: { error: 'Área ya tiene una corrida activa.' } } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Nueva Corrida/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Tintorería Continua' }));
      await userEvent.click(screen.getByRole('button', { name: 'Iniciar Corrida' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Área ya tiene una corrida activa.'));
    });

    it('dado el modal abierto cuando hace click en cancelar entonces lo cierra sin llamar al backend', async () => {
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Nueva Corrida/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

      expect(screen.queryByText('Iniciar Corrida de Producción')).not.toBeInTheDocument();
      expect(mockPost).not.toHaveBeenCalled();
    });
  });

  describe('Pausar / Reanudar / Finalizar', () => {
    it('dado corrida en proceso cuando hace click en pausar entonces llama al backend y actualiza el estado', async () => {
      mockPost.mockResolvedValueOnce({ data: { ...CORRIDA_ACTIVA, estado: 'pausada' } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByRole('button', { name: /Pausar/i })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Pausar/i }));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/corridas-produccion/1/pausar/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Corrida CORR-2026-001 ahora está pausada');
    });

    it('dado el backend rechaza pausar cuando falla entonces muestra el mensaje del error', async () => {
      mockPost.mockRejectedValueOnce({ response: { data: { error: 'No se puede pausar.' } } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByRole('button', { name: /Pausar/i })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Pausar/i }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se puede pausar.'));
    });

    it('dado confirmacion aceptada cuando hace click en finalizar entonces llama al backend', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockPost.mockResolvedValueOnce({ data: { ...CORRIDA_ACTIVA, estado: 'finalizada' } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByRole('button', { name: /Finalizar/i })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Finalizar/i }));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/corridas-produccion/1/finalizar-corrida/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Corrida CORR-2026-001 finalizada correctamente');
    });

    it('dado confirmacion rechazada cuando hace click en finalizar entonces no llama al backend', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByRole('button', { name: /Finalizar/i })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Finalizar/i }));

      expect(mockPost).not.toHaveBeenCalled();
    });

    it('dado el backend rechaza finalizar cuando falla entonces muestra el mensaje del error', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockPost.mockRejectedValueOnce({ response: { data: { error: 'Quedan operaciones pendientes.' } } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByRole('button', { name: /Finalizar/i })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Finalizar/i }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Quedan operaciones pendientes.'));
    });
  });

  describe('Registro de operación (pesaje continuo)', () => {
    async function llenarFormulario() {
      await userEvent.click(screen.getByRole('button', { name: 'TEL-CRUD - Tela Cruda (hilo)' }));
      await userEvent.click(screen.getAllByRole('button', { name: 'Bodega Materia Prima' })[0]);
      await userEvent.type(screen.getByLabelText(/Peso Consumido/i), '100');
      await userEvent.click(screen.getByRole('button', { name: 'TEL-ACAB - Tela Acabada' }));
      await userEvent.click(screen.getAllByRole('button', { name: 'Bodega Producto Terminado' })[1]);
      await userEvent.type(screen.getByLabelText(/Peso Neto Producido/i), '98');
    }

    it('dado balance correcto cuando llena el formulario entonces muestra el semaforo en OK', async () => {
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toBeInTheDocument());

      await llenarFormulario();
      // Merma por defecto es 0: 100 entrada vs 98 salida = desbalance de 2kg
      expect(screen.getByText(/Desbalance: Δ 2.000 kg/)).toBeInTheDocument();

      await userEvent.clear(screen.getByLabelText(/Merma \/ Desperdicio/i));
      await userEvent.type(screen.getByLabelText(/Merma \/ Desperdicio/i), '2');
      await waitFor(() => expect(screen.getByText(/Balance OK/)).toBeInTheDocument());
    });

    // El botón de envío se deshabilita mientras el balance no está OK, así que estas
    // validaciones (que preceden a la del balance en el código) se disparan con
    // fireEvent.submit directo sobre el formulario, no con un click al botón.
    it('dado insumo incompleto cuando confirma entonces exige completar los datos del insumo', async () => {
      const { container } = render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toBeInTheDocument());

      fireEvent.submit(container.querySelector('form')!);

      expect(toastErrorMock).toHaveBeenCalledWith('Complete los datos del insumo consumido.');
      expect(mockPost).not.toHaveBeenCalled();
    });

    it('dado salida incompleta cuando confirma entonces exige completar los datos del producto', async () => {
      const { container } = render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: 'TEL-CRUD - Tela Cruda (hilo)' }));
      await userEvent.click(screen.getAllByRole('button', { name: 'Bodega Materia Prima' })[0]);
      await userEvent.type(screen.getByLabelText(/Peso Consumido/i), '100');
      fireEvent.submit(container.querySelector('form')!);

      expect(toastErrorMock).toHaveBeenCalledWith('Complete los datos del producto transformado.');
      expect(mockPost).not.toHaveBeenCalled();
    });

    it('dado desbalance de masa cuando confirma entonces rechaza el envio con el detalle', async () => {
      const { container } = render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toBeInTheDocument());

      await llenarFormulario();
      fireEvent.submit(container.querySelector('form')!);

      expect(toastErrorMock).toHaveBeenCalledWith(expect.stringContaining('Desbalance de masa detectado'));
      expect(mockPost).not.toHaveBeenCalled();
    });

    it('dado formulario balanceado cuando confirma entonces registra la operacion y resetea los campos', async () => {
      mockPost.mockResolvedValueOnce({ data: { numero_secuencia: 2 } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toBeInTheDocument());

      await llenarFormulario();
      await userEvent.clear(screen.getByLabelText(/Merma \/ Desperdicio/i));
      await userEvent.type(screen.getByLabelText(/Merma \/ Desperdicio/i), '2');
      await userEvent.click(screen.getByRole('button', { name: 'Saldo / Retazo' }));
      await userEvent.click(screen.getByRole('button', { name: 'Setup / Arranque' }));
      await userEvent.type(screen.getByLabelText(/Metros/i), '50');

      await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar Transformación y Generar Etiqueta' })).not.toBeDisabled());
      await userEvent.click(screen.getByRole('button', { name: 'Confirmar Transformación y Generar Etiqueta' }));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
        '/corridas-produccion/1/registrar-operacion/',
        expect.objectContaining({
          consumos: [expect.objectContaining({ producto_id: 1, bodega_origen_id: 1, cantidad_consumida: '100' })],
          salidas: [expect.objectContaining({ producto_id: 2, bodega_destino_id: 2, cantidad_neta: '98', clasificacion_calidad: 'saldo' })],
          mermas: [expect.objectContaining({ peso_merma: '2', tipo_merma: 'setup' })],
        }),
      ));
      expect(toastSuccessMock).toHaveBeenCalledWith('Operación #2 registrada exitosamente.');
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toHaveValue(null));
    });

    it('dado el backend rechaza el registro cuando falla entonces muestra el mensaje del error', async () => {
      mockPost.mockRejectedValueOnce({ response: { data: { error: 'Stock insuficiente.' } } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toBeInTheDocument());

      await llenarFormulario();
      await userEvent.clear(screen.getByLabelText(/Merma \/ Desperdicio/i));
      await userEvent.type(screen.getByLabelText(/Merma \/ Desperdicio/i), '2');
      await userEvent.click(screen.getByRole('button', { name: 'Confirmar Transformación y Generar Etiqueta' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Stock insuficiente.'));
    });

    it('dado click en actualizar operaciones cuando hace click entonces vuelve a consultarlas', async () => {
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText('LOT-ACAB-01')).toBeInTheDocument());
      mockGet.mockClear();
      mockApi();

      await userEvent.click(screen.getByRole('button', { name: 'Actualizar' }));

      await waitFor(() => expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('/operaciones-produccion/?corrida=1')));
    });
  });

  describe('Reversión de operación', () => {
    it('dado una operacion completada cuando hace click en revertir sin motivo entonces exige justificacion', async () => {
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText('LOT-ACAB-01')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Revertir/i }));
      expect(screen.getByText(/Revertir Operación #1/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Confirmar Reversión' })).toBeDisabled();
    });

    it('dado motivo de reversion cuando confirma entonces llama al backend y cierra el modal', async () => {
      mockPost.mockResolvedValueOnce({ data: {} });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText('LOT-ACAB-01')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Revertir/i }));
      await userEvent.type(screen.getByLabelText(/Motivo de la Reversión/i), 'Rotura de hilo en máquina');
      await userEvent.click(screen.getByRole('button', { name: 'Confirmar Reversión' }));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/corridas-produccion/1/revertir-operacion/', {
        operacion_id: 10, justificacion: 'Rotura de hilo en máquina',
      }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Operación #1 revertida y saldos restaurados.');
      await waitFor(() => expect(screen.queryByText(/Revertir Operación #1/)).not.toBeInTheDocument());
    });

    it('dado el backend rechaza la reversion cuando falla entonces muestra el mensaje del error', async () => {
      mockPost.mockRejectedValueOnce({ response: { data: { error: 'No se puede revertir.' } } });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText('LOT-ACAB-01')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Revertir/i }));
      await userEvent.type(screen.getByLabelText(/Motivo de la Reversión/i), 'Error de pesaje detectado');
      await userEvent.click(screen.getByRole('button', { name: 'Confirmar Reversión' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se puede revertir.'));
    });

    it('dado el modal de reversion abierto cuando cancela entonces lo cierra sin llamar al backend', async () => {
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText('LOT-ACAB-01')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Revertir/i }));
      const dialogo = screen.getByText(/Revertir Operación #1/).closest('[role="dialog"]') as HTMLElement;
      await userEvent.click(within(dialogo).getByRole('button', { name: 'Cancelar' }));

      expect(screen.queryByText(/Revertir Operación #1/)).not.toBeInTheDocument();
      expect(mockPost).not.toHaveBeenCalled();
    });
  });

  describe('Formatos de respuesta alternativos y mensajes de error genericos', () => {
    it('dado catalogos y listas sin envoltorio results cuando carga entonces los usa directamente', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url.includes('/corridas-produccion/')) return Promise.resolve({ data: [CORRIDA_ACTIVA] });
        if (url.includes('/operaciones-produccion/')) return Promise.resolve({ data: OPERACIONES });
        if (url.includes('/areas/')) return Promise.resolve({ data: AREAS });
        if (url.includes('/maquinas/')) return Promise.resolve({ data: MAQUINAS });
        if (url.includes('/bodegas/')) return Promise.resolve({ data: BODEGAS });
        if (url.includes('/productos/')) return Promise.resolve({ data: PRODUCTOS });
        return Promise.resolve({ data: [] });
      });
      render(<CorridaContinuaDashboard />);

      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());
      expect(screen.getByText('LOT-ACAB-01')).toBeInTheDocument();
    });

    it('dado corridas y operaciones vacias sin envoltorio results cuando carga entonces no falla', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url.includes('/corridas-produccion/') || url.includes('/operaciones-produccion/')) {
          return Promise.resolve({ data: undefined });
        }
        return Promise.resolve({ data: [] });
      });
      render(<CorridaContinuaDashboard />);

      await waitFor(() => expect(screen.getByText('Corrida Actual: Ninguna seleccionada')).toBeInTheDocument());
    });

    it('dado catalogos sin datos cuando carga entonces usa arreglos vacios sin fallar', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url.includes('/corridas-produccion/')) return Promise.resolve({ data: { results: [CORRIDA_ACTIVA] } });
        if (url.includes('/operaciones-produccion/')) return Promise.resolve({ data: { results: OPERACIONES } });
        if (url.includes('/areas/') || url.includes('/maquinas/') || url.includes('/bodegas/') || url.includes('/productos/')) {
          return Promise.resolve({ data: undefined });
        }
        return Promise.resolve({ data: [] });
      });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Nueva Corrida/i }));
      expect(screen.getByText('Iniciar Corrida de Producción')).toBeInTheDocument();
    });

    it('dado un error de red sin respuesta cuando inicia corrida entonces usa el mensaje generico', async () => {
      mockPost.mockRejectedValueOnce(new Error('network'));
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Nueva Corrida/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Tintorería Continua' }));
      await userEvent.click(screen.getByRole('button', { name: 'Iniciar Corrida' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al iniciar corrida'));
    });

    it('dado un error de red sin respuesta cuando pausa entonces usa el mensaje generico', async () => {
      mockPost.mockRejectedValueOnce(new Error('network'));
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByRole('button', { name: /Pausar/i })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Pausar/i }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cambiar estado de la corrida'));
    });

    it('dado un error de red sin respuesta cuando finaliza entonces usa el mensaje generico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockPost.mockRejectedValueOnce(new Error('network'));
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByRole('button', { name: /Finalizar/i })).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Finalizar/i }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al finalizar corrida'));
    });

    it('dado un error de red sin respuesta cuando revierte entonces usa el mensaje generico', async () => {
      mockPost.mockRejectedValueOnce(new Error('network'));
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText('LOT-ACAB-01')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Revertir/i }));
      await userEvent.type(screen.getByLabelText(/Motivo de la Reversión/i), 'Error de pesaje detectado');
      await userEvent.click(screen.getByRole('button', { name: 'Confirmar Reversión' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al revertir operación'));
    });
  });

  describe('Seleccion de corrida activa por defecto', () => {
    it('dado catalogos con envoltorio results cuando carga entonces los extrae correctamente', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url.includes('/corridas-produccion/')) return Promise.resolve({ data: { results: [CORRIDA_ACTIVA] } });
        if (url.includes('/operaciones-produccion/')) return Promise.resolve({ data: { results: OPERACIONES } });
        if (url.includes('/areas/')) return Promise.resolve({ data: { results: AREAS } });
        if (url.includes('/maquinas/')) return Promise.resolve({ data: { results: MAQUINAS } });
        if (url.includes('/bodegas/')) return Promise.resolve({ data: { results: BODEGAS } });
        if (url.includes('/productos/')) return Promise.resolve({ data: { results: PRODUCTOS } });
        return Promise.resolve({ data: { results: [] } });
      });
      render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Nueva Corrida/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Tintorería Continua' }));
      expect(screen.getByRole('button', { name: 'Iniciar Corrida' })).toBeInTheDocument();
    });

    it('dado ninguna corrida en proceso ni pausada cuando carga entonces selecciona la primera de la lista', async () => {
      const finalizada = { ...CORRIDA_ACTIVA, estado: 'finalizada' };
      mockApi({ corridas: [finalizada] });
      render(<CorridaContinuaDashboard />);

      await waitFor(() => expect(screen.getByText('Corrida Actual: CORR-2026-001')).toBeInTheDocument());
    });

    it('dado solo una corrida pausada entre varias cuando carga entonces la selecciona como activa', async () => {
      const finalizada = { ...CORRIDA_ACTIVA, id: 9, codigo: 'CORR-2026-009', estado: 'finalizada' };
      mockApi({ corridas: [finalizada, CORRIDA_PAUSADA] });
      render(<CorridaContinuaDashboard />);

      await waitFor(() => expect(screen.getByText('Corrida Actual: CORR-2026-002')).toBeInTheDocument());
    });
  });

  describe('Registro de operación con corrida no en_proceso', () => {
    it('dado corrida pausada cuando intenta registrar una operacion entonces exige que este en proceso', async () => {
      mockApi({ corridas: [CORRIDA_PAUSADA] });
      const { container } = render(<CorridaContinuaDashboard />);
      await waitFor(() => expect(screen.getByLabelText(/Peso Consumido/i)).toBeInTheDocument());

      fireEvent.submit(container.querySelector('form')!);

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith(
        expect.stringContaining("Debe estar 'en_proceso' para registrar operaciones")));
    });
  });

  describe('Modo restringido (operario)', () => {
    it('dado modo restringido cuando renderiza entonces no muestra el boton Nueva Corrida', async () => {
      render(<CorridaContinuaDashboard restrictedMode />);
      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());
      expect(screen.queryByRole('button', { name: /Nueva Corrida/i })).not.toBeInTheDocument();
    });

    it('dado sin operaciones previas cuando renderiza en modo restringido entonces avisa que falta material definido', async () => {
      mockApi({ operaciones: [] });
      render(<CorridaContinuaDashboard restrictedMode />);

      await waitFor(() => expect(screen.getByText(/Un supervisor todavía no registra la primera transformación/)).toBeInTheDocument());
    });

    it('dado una operacion previa valida cuando renderiza en modo restringido entonces hereda el material y permite registrar avance', async () => {
      render(<CorridaContinuaDashboard restrictedMode />);

      await waitFor(() => expect(screen.getByRole('button', { name: /Registrar Avance/i })).toBeInTheDocument());
      expect(screen.getByText('Tela Cruda')).toBeInTheDocument();
      expect(screen.getByText('Tela Acabada')).toBeInTheDocument();
    });

    it('dado una operacion previa sin consumos ni salidas cuando renderiza en modo restringido entonces no hereda material', async () => {
      mockApi({ operaciones: [{ ...OPERACIONES[0], consumos: [], salidas: [] }] });
      render(<CorridaContinuaDashboard restrictedMode />);

      await waitFor(() => expect(screen.getByText(/CORR-2026-001/i)).toBeInTheDocument());
      expect(screen.queryByRole('button', { name: /Registrar Avance/i })).not.toBeInTheDocument();
    });
  });
});
