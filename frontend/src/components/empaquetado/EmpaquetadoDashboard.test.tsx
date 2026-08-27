import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EmpaquetadoDashboard } from './EmpaquetadoDashboard';
import type { OrdenProduccion, Maquina, LoteProduccion } from '../../lib/types';

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
const toastInfoMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
    info: (...args: any[]) => toastInfoMock(...args),
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
    return (
      <button type="button" onClick={() => onValueChange(value)}>
        {children}
      </button>
    );
  },
}));

const writeTextMock = vi.fn().mockResolvedValue(undefined);
Object.assign(navigator, { clipboard: { writeText: writeTextMock } });

vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: { role: 'empaquetado', user: { id: 1, username: 'empacador1' } } }),
}));

const ORDEN_1: OrdenProduccion = {
  id: 1,
  codigo: 'OP-001',
  producto: 10,
  formula_color: 1,
  peso_neto_requerido: 100,
  peso_producido: 40,
  estado: 'en_proceso',
  fecha_creacion: '2026-07-01T00:00:00',
  fecha_modificacion: '2026-07-01T00:00:00',
  sede: 1,
  producto_nombre: 'Hilo Algodón',
  sede_nombre: 'Sede Norte',
  inventario_descontado: false,
  maquina_asignada: 5,
  prioridad: 'normal',
};

const ORDEN_2: OrdenProduccion = {
  ...ORDEN_1,
  id: 2,
  codigo: 'OP-002',
  producto_nombre: 'Tela Popelina',
  sede_nombre: 'Sede Sur',
  peso_producido: 0,
  maquina_asignada: null,
};

const MAQUINA_1: Maquina = {
  id: 5,
  nombre: 'Empacadora 1',
  capacidad_maxima: 100,
  eficiencia_ideal: 0.9,
  estado: 'operativa',
  area: 1,
};

const LOTE_1: LoteProduccion = {
  id: 1,
  orden_produccion: 1,
  codigo_lote: 'L-001',
  peso_neto_producido: 12.5,
  operario: 1,
  maquina: 5,
  turno: 'T1',
  hora_inicio: '2026-07-01T08:00:00',
  hora_final: '2026-07-01T08:10:00',
};

function mockFetch(ordenes: OrdenProduccion[] = [], maquinas: Maquina[] = [], lotes: LoteProduccion[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url.includes('generate_zpl')) return Promise.resolve({ data: { zpl: 'ZPL-DATA' } });
    if (url.startsWith('/ordenes-produccion/')) return Promise.resolve({ data: ordenes });
    if (url.startsWith('/maquinas/')) return Promise.resolve({ data: maquinas });
    if (url.startsWith('/lotes-produccion/')) return Promise.resolve({ data: lotes });
    return Promise.resolve({ data: [] });
  });
}

function renderComponent() {
  return render(<EmpaquetadoDashboard />);
}

async function seleccionarOrden(textoBoton: string) {
  await userEvent.click(await screen.findByRole('button', { name: textoBoton }));
}

async function completarCamposValidos() {
  await userEvent.clear(screen.getByLabelText('Código Lote/Bulto'));
  await userEvent.type(screen.getByLabelText('Código Lote/Bulto'), 'L-101');
  await userEvent.clear(screen.getByLabelText('Peso Bruto (Kg)'));
  await userEvent.type(screen.getByLabelText('Peso Bruto (Kg)'), '10.5');
}

function readableStreamDeLineas(lineas: string[]) {
  let i = 0;
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (i < lineas.length) {
        controller.enqueue(encoder.encode(lineas[i]));
        i++;
      } else {
        controller.close();
      }
    },
  });
}

describe('EmpaquetadoDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    toastInfoMock.mockReset();
    writeTextMock.mockClear();
  });

  afterEach(() => {
    delete (navigator as any).serial;
  });

  it('dado datos aun no resueltos cuando monta entonces muestra el estado de carga', async () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { container } = renderComponent();

    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
    expect(screen.queryByText('Estación de Empaque')).not.toBeInTheDocument();
  });

  it('dado sin ordenes ni lotes cuando carga entonces muestra los estados vacios', async () => {
    mockFetch([], [], []);
    renderComponent();

    await waitFor(() => expect(screen.getByText('No hay registros recientes.')).toBeInTheDocument());
    expect(screen.getByText('Seleccione orden...')).toBeInTheDocument();
  });

  it('dado ordenes y lotes existentes cuando carga entonces los lista', async () => {
    mockFetch([ORDEN_1, ORDEN_2], [MAQUINA_1], [LOTE_1]);
    renderComponent();

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'OP-001 - Hilo Algodón (Sede Norte)' })).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: 'OP-002 - Tela Popelina (Sede Sur)' })).toBeInTheDocument();
    expect(screen.getByText('L-001')).toBeInTheDocument();
    expect(screen.getByText('12.5 kg')).toBeInTheDocument();
  });

  it('dado click en una orden cuando la selecciona entonces muestra el progreso de produccion', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    renderComponent();

    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');

    expect(screen.getByText('40%')).toBeInTheDocument();
    expect(screen.getByText('40kg de 100kg requeridos')).toBeInTheDocument();
  });

  it('dado una orden de producto tipo tela cuando la selecciona entonces muestra el campo cantidad de metros', async () => {
    mockFetch([ORDEN_2], [MAQUINA_1], []);
    renderComponent();

    await seleccionarOrden('OP-002 - Tela Popelina (Sede Sur)');

    expect(screen.getByLabelText('Cantidad de Metros (Opcional)')).toBeInTheDocument();
  });

  it('dado una orden de producto no textil cuando la selecciona entonces no muestra el campo cantidad de metros', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    renderComponent();

    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');

    expect(screen.queryByLabelText('Cantidad de Metros (Opcional)')).not.toBeInTheDocument();
  });

  it('dado cambio de presentacion a Funda cuando actualiza entonces autocompleta la tara y recalcula el peso neto', async () => {
    mockFetch([], [], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.clear(screen.getByLabelText('Peso Bruto (Kg)'));
    await userEvent.type(screen.getByLabelText('Peso Bruto (Kg)'), '5');
    await userEvent.click(screen.getByRole('button', { name: 'Funda' }));

    await waitFor(() => expect(screen.getByLabelText('Tara (Kg) - Manual')).toHaveValue(0.1));
    expect(screen.getByText('4.90')).toBeInTheDocument();
  });

  it('dado cambios de peso bruto y tara cuando el usuario escribe entonces el peso neto se recalcula en vivo', async () => {
    mockFetch([], [], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.clear(screen.getByLabelText('Peso Bruto (Kg)'));
    await userEvent.type(screen.getByLabelText('Peso Bruto (Kg)'), '10');
    await userEvent.clear(screen.getByLabelText('Tara (Kg) - Manual'));
    await userEvent.type(screen.getByLabelText('Tara (Kg) - Manual'), '2');

    expect(screen.getByText('8.00')).toBeInTheDocument();
  });

  it('dado formulario vacio cuando intenta registrar entonces muestra errores de validacion y no llama al backend', async () => {
    mockFetch([], [], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.clear(screen.getByLabelText('Peso Bruto (Kg)'));

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(screen.getByText('Seleccione una orden')).toBeInTheDocument());
    expect(screen.getByText('Código de lote requerido')).toBeInTheDocument();
    expect(screen.getByText('Peso bruto debe ser mayor a 0')).toBeInTheDocument();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado unidades de empaque en cero cuando intenta registrar entonces muestra error de minimo y no llama al backend', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    renderComponent();
    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');
    await completarCamposValidos();

    await userEvent.clear(screen.getByLabelText('Unidades'));
    await userEvent.type(screen.getByLabelText('Unidades'), '0');

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(screen.getByText('Mínimo 1 unidad')).toBeInTheDocument());
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado una tara mayor o igual al peso bruto cuando intenta registrar entonces rechaza con error de validacion', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    renderComponent();
    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');

    await userEvent.clear(screen.getByLabelText('Código Lote/Bulto'));
    await userEvent.type(screen.getByLabelText('Código Lote/Bulto'), 'L-101');
    await userEvent.clear(screen.getByLabelText('Peso Bruto (Kg)'));
    await userEvent.type(screen.getByLabelText('Peso Bruto (Kg)'), '0.3');

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(screen.getByText('El peso bruto debe ser mayor que la tara')).toBeInTheDocument());
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando registra el lote entonces envia el payload correcto con la maquina de la orden', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    mockPost.mockResolvedValueOnce({ data: { id: 99, codigo_lote: 'L-101' } });
    renderComponent();

    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');
    await completarCamposValidos();

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/ordenes-produccion/1/registrar-lote/',
      expect.objectContaining({
        orden_produccion: '1',
        maquina: '5',
        codigo_lote: 'L-101',
        peso_bruto: 10.5,
        tara: 0.5,
        peso_neto_producido: 10,
        unidades_empaque: 1,
        presentacion: 'Caja',
      }),
    ));
    expect(mockPost.mock.calls[0][1].hora_inicio).toEqual(expect.any(String));
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Lote L-101 registrado correctamente. Peso Neto: 10kg'));
  });

  it('dado un registro exitoso cuando finaliza el envio entonces imprime la etiqueta automaticamente', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    mockPost.mockResolvedValueOnce({ data: { id: 99, codigo_lote: 'L-101' } });
    renderComponent();

    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');
    await completarCamposValidos();

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/99/generate_zpl/'));
    await waitFor(() => expect(writeTextMock).toHaveBeenCalledWith('ZPL-DATA'));
    await waitFor(() => expect(toastInfoMock).toHaveBeenCalledWith('Código ZPL copiado al portapapeles (sin impresora disponible).'));
  });

  it('dado una orden sin maquina asignada cuando registra el lote entonces no envia el id de la maquina', async () => {
    mockFetch([ORDEN_2], [MAQUINA_1], []);
    mockPost.mockResolvedValueOnce({ data: { id: 100, codigo_lote: 'L-200' } });
    renderComponent();

    await seleccionarOrden('OP-002 - Tela Popelina (Sede Sur)');
    await completarCamposValidos();

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    const payload = mockPost.mock.calls[0][1];
    expect(payload.maquina).not.toBe('5');
  });

  it('dado un error del backend cuando registra el lote entonces muestra el mensaje de error del backend', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    mockPost.mockRejectedValueOnce({ response: { data: { detail: 'Stock insuficiente para el empaque' } } });
    renderComponent();

    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');
    await completarCamposValidos();

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Stock insuficiente para el empaque'));
    expect(mockGet).not.toHaveBeenCalledWith(expect.stringContaining('generate_zpl'));
  });

  it('dado una falla al cargar datos iniciales cuando monta entonces muestra un toast de error y estados vacios', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    renderComponent();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar datos iniciales'));
    expect(screen.getByText('No hay registros recientes.')).toBeInTheDocument();
  });

  it('dado mas de 20 lotes recientes cuando carga entonces pagina el historial', async () => {
    const muchosLotes = Array.from({ length: 25 }, (_, i) => ({
      ...LOTE_1,
      id: i + 1,
      codigo_lote: `L-${String(i + 1).padStart(3, '0')}`,
    }));
    mockFetch([], [], muchosLotes);
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.queryByText('L-021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('L-021')).toBeInTheDocument();
  });

  it('dado mas de 20 lotes recientes cuando retrocede con Anterior entonces vuelve a la primera pagina', async () => {
    const muchosLotes = Array.from({ length: 25 }, (_, i) => ({
      ...LOTE_1,
      id: i + 1,
      codigo_lote: `L-${String(i + 1).padStart(3, '0')}`,
    }));
    mockFetch([], [], muchosLotes);
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Anterior/i }));

    await waitFor(() => expect(screen.getByText('Página 1 de 2')).toBeInTheDocument());
    expect(screen.getByText('L-001')).toBeInTheDocument();
    expect(screen.queryByText('L-021')).not.toBeInTheDocument();
  });

  it('dado mas de 20 lotes recientes cuando escribe un numero de pagina y presiona Enter entonces navega a esa pagina', async () => {
    const muchosLotes = Array.from({ length: 25 }, (_, i) => ({
      ...LOTE_1,
      id: i + 1,
      codigo_lote: `L-${String(i + 1).padStart(3, '0')}`,
    }));
    mockFetch([], [], muchosLotes);
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('L-021')).toBeInTheDocument();
  });

  it('dado mas de 20 lotes recientes cuando escribe un numero de pagina y sale del campo entonces navega a esa pagina', async () => {
    const muchosLotes = Array.from({ length: 25 }, (_, i) => ({
      ...LOTE_1,
      id: i + 1,
      codigo_lote: `L-${String(i + 1).padStart(3, '0')}`,
    }));
    mockFetch([], [], muchosLotes);
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2');
    await userEvent.tab();

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('L-021')).toBeInTheDocument();
  });

  it('dado un click en reimprimir de un lote reciente cuando confirma el motivo entonces llama al endpoint reimprimir e imprime', async () => {
    mockFetch([], [], [LOTE_1]);
    mockPost.mockImplementation((url: string) => {
      if (url.includes('/reimprimir/')) {
        return Promise.resolve({ data: { zpl: 'ZPL-DATA', evento: { version: 1, secuencia: 2 } } });
      }
      return Promise.resolve({ data: {} });
    });
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    const fila = screen.getByText('L-001').closest('tr') as HTMLElement;
    const botonImprimir = within(fila).getByTitle('Reimprimir');
    await userEvent.click(botonImprimir);

    const motivoOpcion = await screen.findByRole('button', { name: 'Etiqueta Dañada' });
    await userEvent.click(motivoOpcion);
    await userEvent.click(screen.getByRole('button', { name: /^Reimprimir$/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/lotes-produccion/1/reimprimir/',
      expect.objectContaining({ motivo: 'DANIADA' })
    ));
    await waitFor(() => expect(writeTextMock).toHaveBeenCalledWith('ZPL-DATA'));
  });

  it('dado un click en ver historial de un lote reciente cuando abre entonces consulta y muestra los eventos', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/etiquetas/')) {
        return Promise.resolve({
          data: [
            {
              id: 1, tipo_evento: 'ORIGINAL', secuencia: 1, version: 1, motivo: null,
              detalle_motivo: '', usuario: 'operario1', timestamp: '2026-07-01T08:10:00Z',
              formato: 'ZPL', anulada: false, anula_a: null,
            },
          ],
        });
      }
      if (url.includes('generate_zpl')) return Promise.resolve({ data: { zpl: 'ZPL-DATA' } });
      if (url.startsWith('/lotes-produccion/')) return Promise.resolve({ data: [LOTE_1] });
      return Promise.resolve({ data: [] });
    });
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    const fila = screen.getByText('L-001').closest('tr') as HTMLElement;
    await userEvent.click(within(fila).getByTitle('Ver historial de etiquetas'));

    await waitFor(() => expect(screen.getByText('Historial de Etiquetas')).toBeInTheDocument());
    expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/1/etiquetas/');
    await waitFor(() => expect(screen.getByText('Original')).toBeInTheDocument());
    expect(screen.getByText('operario1')).toBeInTheDocument();
    expect(screen.getByText('Vigente')).toBeInTheDocument();
  });

  it('dado un error del backend al reimprimir entonces muestra un toast de error', async () => {
    mockFetch([], [], [LOTE_1]);
    mockPost.mockImplementation((url: string) => {
      if (url.includes('/reimprimir/')) {
        return Promise.reject({ response: { data: { error: { message: 'Motivo requerido' } } } });
      }
      return Promise.resolve({ data: {} });
    });
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    const fila = screen.getByText('L-001').closest('tr') as HTMLElement;
    const botonImprimir = within(fila).getByTitle('Reimprimir');
    await userEvent.click(botonImprimir);

    const motivoOpcion = await screen.findByRole('button', { name: 'Etiqueta Dañada' });
    await userEvent.click(motivoOpcion);
    await userEvent.click(screen.getByRole('button', { name: /^Reimprimir$/i }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Motivo requerido'));
  });

  it('dado cambio de presentacion a Cono cuando actualiza entonces autocompleta la tara en 0.05', async () => {
    mockFetch([], [], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Cono' }));

    await waitFor(() => expect(screen.getByLabelText('Tara (Kg) - Manual')).toHaveValue(0.05));
  });

  it('dado el checkbox de finalizar orden marcado cuando registra el lote entonces envia completar_orden en true', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    mockPost.mockResolvedValueOnce({ data: { id: 99, codigo_lote: 'L-101' } });
    renderComponent();

    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');
    await completarCamposValidos();
    await userEvent.click(screen.getByRole('checkbox'));

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/ordenes-produccion/1/registrar-lote/',
      expect.objectContaining({ completar_orden: true }),
    ));
  });

  it('dado una cantidad de metros ingresada cuando registra el lote de una orden de tela entonces la incluye en el payload', async () => {
    mockFetch([ORDEN_2], [MAQUINA_1], []);
    mockPost.mockResolvedValueOnce({ data: { id: 100, codigo_lote: 'L-200' } });
    renderComponent();

    await seleccionarOrden('OP-002 - Tela Popelina (Sede Sur)');
    await completarCamposValidos();
    await userEvent.type(screen.getByLabelText('Cantidad de Metros (Opcional)'), '25.5');

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/ordenes-produccion/2/registrar-lote/',
      expect.objectContaining({ cantidad_metros: 25.5 }),
    ));
  });

  it('dado un navegador sin soporte Web Serial cuando conecta la balanza entonces muestra un toast de error', async () => {
    mockFetch([], [], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Conectar Balanza (COM)' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Tu navegador no soporta Web Serial API (Usa Chrome o Edge)'));
  });

  it('dado un error al solicitar el puerto serial cuando conecta la balanza entonces muestra un toast de error', async () => {
    mockFetch([], [], []);
    Object.assign(navigator, { serial: { requestPort: vi.fn().mockRejectedValue(new Error('acceso denegado')) } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Conectar Balanza (COM)' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo conectar a la balanza'));
  });

  it('dado una conexion exitosa con la balanza cuando llegan datos de peso entonces actualiza el peso bruto automaticamente', async () => {
    mockFetch([], [], []);
    const mockPort = {
      open: vi.fn().mockResolvedValue(undefined),
      readable: readableStreamDeLineas(['45.30\n']),
    };
    Object.assign(navigator, { serial: { requestPort: vi.fn().mockResolvedValue(mockPort) } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Conectar Balanza (COM)' }));

    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Balanza conectada correctamente'));
    expect(mockPort.open).toHaveBeenCalledWith({ baudRate: 9600 });
    expect(screen.getByRole('button', { name: 'Balanza Conectada' })).toBeDisabled();
    await waitFor(() => expect(screen.getByLabelText('Peso Bruto (Kg)')).toHaveValue(45.3));
  });

  it('dado un error de lectura de la balanza cuando se pierde la conexion entonces muestra un toast de error y desconecta', async () => {
    mockFetch([], [], []);
    const streamConError = new ReadableStream<Uint8Array>({
      pull(controller) {
        controller.error(new Error('puerto desconectado'));
      },
    });
    const mockPort = {
      open: vi.fn().mockResolvedValue(undefined),
      readable: streamConError,
    };
    Object.assign(navigator, { serial: { requestPort: vi.fn().mockResolvedValue(mockPort) } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Conectar Balanza (COM)' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Conexión con la balanza perdida'));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Conectar Balanza (COM)' })).toBeInTheDocument());
  });

  it('dado un backend que responde datos paginados en formato results cuando carga entonces desenvuelve las listas', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/ordenes-produccion/')) return Promise.resolve({ data: { results: [ORDEN_1] } });
      if (url.startsWith('/maquinas/')) return Promise.resolve({ data: { results: [MAQUINA_1] } });
      if (url.startsWith('/lotes-produccion/')) return Promise.resolve({ data: { results: [LOTE_1] } });
      return Promise.resolve({ data: [] });
    });
    renderComponent();

    await waitFor(() => expect(screen.getByRole('button', { name: 'OP-001 - Hilo Algodón (Sede Norte)' })).toBeInTheDocument());
    expect(screen.getByText('L-001')).toBeInTheDocument();
  });

  it('dado un error del backend sin detalle cuando registra el lote entonces muestra el mensaje generico', async () => {
    mockFetch([ORDEN_1], [MAQUINA_1], []);
    mockPost.mockRejectedValueOnce(new Error('falla de red'));
    renderComponent();

    await seleccionarOrden('OP-001 - Hilo Algodón (Sede Norte)');
    await completarCamposValidos();

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al registrar el empaque.'));
  });

  it('dado una orden sin nombre de producto cuando se lista entonces usa el texto por defecto Producto', async () => {
    const ordenSinNombre = { ...ORDEN_1, producto_nombre: undefined };
    mockFetch([ordenSinNombre], [MAQUINA_1], []);
    renderComponent();

    await waitFor(() => expect(screen.getByRole('button', { name: 'OP-001 - Producto (Sede Norte)' })).toBeInTheDocument());
  });

  it('dado un valor de metros ingresado y luego borrado cuando registra el lote entonces no incluye la cantidad de metros', async () => {
    mockFetch([ORDEN_2], [MAQUINA_1], []);
    mockPost.mockResolvedValueOnce({ data: { id: 100, codigo_lote: 'L-200' } });
    renderComponent();

    await seleccionarOrden('OP-002 - Tela Popelina (Sede Sur)');
    await completarCamposValidos();
    const metrosInput = screen.getByLabelText('Cantidad de Metros (Opcional)');
    await userEvent.type(metrosInput, '25.5');
    await userEvent.clear(metrosInput);
    expect(metrosInput).toHaveValue(null);

    await userEvent.click(screen.getByRole('button', { name: /Registrar e Imprimir Etiqueta/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    expect(mockPost.mock.calls[0][1].cantidad_metros).toBeUndefined();
  });

  it('dado un numero de pagina fuera de rango cuando lo ingresa entonces no navega', async () => {
    const muchosLotes = Array.from({ length: 25 }, (_, i) => ({
      ...LOTE_1,
      id: i + 1,
      codigo_lote: `L-${String(i + 1).padStart(3, '0')}`,
    }));
    mockFetch([], [], muchosLotes);
    renderComponent();

    await waitFor(() => expect(screen.getByText('L-001')).toBeInTheDocument());
    const irAInput = screen.getByText('Ir a').parentElement!.querySelector('input') as HTMLInputElement;

    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99{Enter}');
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();

    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado localStorage sin getItem ni setItem cuando monta y cambia el modo de impresion entonces usa auto por defecto y no falla', async () => {
    const originalLocalStorage = window.localStorage;
    Object.defineProperty(window, 'localStorage', { value: {}, configurable: true, writable: true });
    try {
      mockFetch([], [], []);
      renderComponent();
      await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());
      expect(screen.getByText('Automático (Zebra → PDF)')).toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: 'PDF Universal (Navegador)' }));
      await waitFor(() => expect(toastInfoMock).toHaveBeenCalledWith('Modo de impresión cambiado a: PDF Universal'));
    } finally {
      Object.defineProperty(window, 'localStorage', { value: originalLocalStorage, configurable: true, writable: true });
    }
  });

  it('dado cambio de modo de impresion a zebra o automatico cuando selecciona entonces muestra el toast correspondiente', async () => {
    mockFetch([], [], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Zebra ZPL Nativo' }));
    await waitFor(() => expect(toastInfoMock).toHaveBeenCalledWith('Modo de impresión cambiado a: Zebra ZPL Nativo'));

    await userEvent.click(screen.getByRole('button', { name: 'Automático (Zebra → PDF)' }));
    await waitFor(() => expect(toastInfoMock).toHaveBeenCalledWith('Modo de impresión cambiado a: Automático'));
  });

  it('dado cambio de presentacion a Rollo cuando actualiza entonces no autocompleta la tara', async () => {
    mockFetch([], [], []);
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await waitFor(() => expect(screen.getByLabelText('Tara (Kg) - Manual')).toHaveValue(0.5));
    await userEvent.click(screen.getByRole('button', { name: 'Rollo' }));

    expect(screen.getByLabelText('Tara (Kg) - Manual')).toHaveValue(0.5);
  });

  it('dado una respuesta del backend sin formato array ni results cuando carga entonces trata las listas como vacias', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith('/ordenes-produccion/')) return Promise.resolve({ data: {} });
      if (url.startsWith('/maquinas/')) return Promise.resolve({ data: {} });
      if (url.startsWith('/lotes-produccion/')) return Promise.resolve({ data: {} });
      return Promise.resolve({ data: [] });
    });
    renderComponent();

    await waitFor(() => expect(screen.getByText('No hay registros recientes.')).toBeInTheDocument());
    expect(screen.getByText('Seleccione orden...')).toBeInTheDocument();
  });

  it('dado lotes registrados hoy con y sin peso neto cuando carga entonces calcula bultos, peso total y promedio del turno', async () => {
    const hoy = new Date().toISOString().split('T')[0];
    const loteHoyConPeso: LoteProduccion = { ...LOTE_1, id: 50, hora_final: `${hoy}T08:10:00`, peso_neto_producido: 10 };
    const loteHoySinPeso: any = { ...LOTE_1, id: 51, hora_final: `${hoy}T09:10:00`, peso_neto_producido: undefined };
    mockFetch([], [], [loteHoyConPeso, loteHoySinPeso]);
    renderComponent();

    await waitFor(() => expect(screen.getByText('Bultos Empacados Hoy').closest('div')).toHaveTextContent('2'));
    expect(screen.getByText('Peso Total del Turno').closest('div')).toHaveTextContent('10');
    expect(screen.getByText('Promedio por Bulto').closest('div')).toHaveTextContent('5.0');
  });

  it('dado datos de balanza con lineas vacias, sin newline aun, sin numero y en cero cuando llegan entonces solo actualiza el peso con el valor valido positivo', async () => {
    mockFetch([], [], []);
    const mockPort = {
      open: vi.fn().mockResolvedValue(undefined),
      readable: readableStreamDeLineas(['', 'PART', 'IAL\n\nERR\n0\n45.30\n']),
    };
    Object.assign(navigator, { serial: { requestPort: vi.fn().mockResolvedValue(mockPort) } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('Seleccione orden...')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Conectar Balanza (COM)' }));

    await waitFor(() => expect(screen.getByLabelText('Peso Bruto (Kg)')).toHaveValue(45.3));
  });
});
