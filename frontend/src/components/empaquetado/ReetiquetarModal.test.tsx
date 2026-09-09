import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReetiquetarModal } from './ReetiquetarModal';
import type { LoteProduccion } from '../../lib/types';

// El modal solo se monta hoy cuando `esSupervisor` es true en BuscadorLotes
// (rol en ROLES_SUPERVISOR), y el único test que renderiza ese árbol usa
// role:'empaquetado' — por eso el archivo entero estaba en 0% de cobertura.
// Aquí se prueba el componente de forma aislada, con el rol como variable
// controlada por caso (`mockRole`), para cubrir tanto la rama supervisor
// como la de no-supervisor.
const mockRole = { current: 'jefe_area' as string | null };
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({
    profile: mockRole.current
      ? { role: mockRole.current, user: { id: 1, username: 'usuario_test' } }
      : null,
  }),
}));

const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { post: (...args: any[]) => mockPost(...args) },
}));

const mockPrintLabel = vi.fn();
vi.mock('../../lib/printing', () => ({
  printLabel: (...args: any[]) => mockPrintLabel(...args),
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

// Shim de Radix Select — mismo patrón que HistorialEtiquetasModal.test.tsx.
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

const LOTE: LoteProduccion = {
  id: 7,
  orden_produccion: 1,
  codigo_lote: 'L-007',
  peso_neto_producido: 90,
  operario: 1,
  maquina: 1,
  turno: 'Dia',
  hora_inicio: '2026-01-01T08:00:00Z',
  hora_final: '2026-01-01T16:00:00Z',
  clasificacion_calidad: 'primera',
};

async function seleccionarMotivo(label = 'Corrección de Peso') {
  await userEvent.click(await screen.findByRole('button', { name: label }));
}

describe('ReetiquetarModal', () => {
  beforeEach(() => {
    mockRole.current = 'jefe_area';
    mockPost.mockReset();
    mockPrintLabel.mockReset();
    mockPrintLabel.mockResolvedValue('clipboard');
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado motivo no seleccionado cuando confirma entonces muestra error y no llama a la API', async () => {
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={LOTE} />);
    const confirmarBtn = screen.getByRole('button', { name: /reetiquetar lote/i });
    expect(confirmarBtn).toBeDisabled();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado peso fuera de tolerancia sin confirmar cuando confirma entonces muestra error de tolerancia', async () => {
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={LOTE} />);
    const pesoInput = screen.getByRole('spinbutton');
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '150'); // >10% de desvío sobre 90
    await seleccionarMotivo();

    await userEvent.click(screen.getByRole('button', { name: /reetiquetar lote/i }));
    expect(toastErrorMock).toHaveBeenCalledWith(
      expect.stringContaining('difiere más del 10%'),
    );
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado usuario no supervisor sin credenciales cuando confirma entonces pide usuario y contraseña', async () => {
    mockRole.current = 'empaquetado'; // no está en SUPERVISOR_ROLES
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={LOTE} />);
    expect(screen.getByText(/Validación de Jefe de Área/i)).toBeInTheDocument();

    await seleccionarMotivo();
    const pesoInput = screen.getByRole('spinbutton');
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '95');

    await userEvent.click(screen.getByRole('button', { name: /reetiquetar lote/i }));
    expect(toastErrorMock).toHaveBeenCalledWith(
      expect.stringContaining('usuario y contraseña'),
    );
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado sin cambios de peso ni calidad cuando confirma entonces exige modificar algun dato', async () => {
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={LOTE} />);
    await seleccionarMotivo();
    await userEvent.click(screen.getByRole('button', { name: /reetiquetar lote/i }));
    expect(toastErrorMock).toHaveBeenCalledWith(
      expect.stringContaining('modificar al menos un dato'),
    );
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado supervisor con cambio de peso cuando confirma entonces envia payload sin credenciales y notifica exito', async () => {
    mockPost.mockResolvedValue({
      data: { zpl: 'ZPL-DATA', evento: { tipo_evento: 'REETIQUETADO', version: 2 } },
    });
    const onOpenChange = vi.fn();
    const onReetiquetado = vi.fn();
    render(
      <ReetiquetarModal open={true} onOpenChange={onOpenChange} lote={LOTE} onReetiquetado={onReetiquetado} />,
    );
    expect(screen.getByText(/Autorizando como/i)).toBeInTheDocument();

    const pesoInput = screen.getByRole('spinbutton');
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '95');
    await seleccionarMotivo();

    await userEvent.click(screen.getByRole('button', { name: /reetiquetar lote/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/lotes-produccion/7/reetiquetar/',
      expect.objectContaining({
        cambios: { peso_neto_producido: 95 },
        motivo: 'CORRECCION_PESO',
      }),
    ));
    const payloadEnviado = mockPost.mock.calls[0][1];
    expect(payloadEnviado.supervisor_username).toBeUndefined();

    await waitFor(() => expect(mockPrintLabel).toHaveBeenCalledWith(
      7, 'ZPL-DATA', { tipo_evento: 'REETIQUETADO', version: 2 },
    ));
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalled());
    expect(onReetiquetado).toHaveBeenCalledWith('ZPL-DATA');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('dado no supervisor con credenciales completas cuando confirma entonces incluye usuario y contrasena en el payload', async () => {
    mockRole.current = 'empaquetado';
    mockPost.mockResolvedValue({
      data: { zpl: 'ZPL-DATA', evento: { tipo_evento: 'REETIQUETADO', version: 2 } },
    });
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={LOTE} />);

    const pesoInput = screen.getByRole('spinbutton');
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '95');
    await seleccionarMotivo();

    await userEvent.type(screen.getByPlaceholderText('ej: jefe_area1'), 'jefe1');
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'clave-secreta');

    await userEvent.click(screen.getByRole('button', { name: /reetiquetar lote/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalled());
    const payloadEnviado = mockPost.mock.calls[0][1];
    expect(payloadEnviado.supervisor_username).toBe('jefe1');
    expect(payloadEnviado.supervisor_password).toBe('clave-secreta');
  });

  it('dado error de la API cuando confirma entonces muestra el mensaje del backend', async () => {
    mockPost.mockRejectedValue({
      response: { data: { error: { message: 'El lote ya fue reetiquetado.' } } },
    });
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={LOTE} />);

    const pesoInput = screen.getByRole('spinbutton');
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '95');
    await seleccionarMotivo();
    await userEvent.click(screen.getByRole('button', { name: /reetiquetar lote/i }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('El lote ya fue reetiquetado.'));
  });

  it('dado error de red sin payload estructurado cuando confirma entonces muestra mensaje generico', async () => {
    mockPost.mockRejectedValue(new Error('network error'));
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={LOTE} />);

    const pesoInput = screen.getByRole('spinbutton');
    await userEvent.clear(pesoInput);
    await userEvent.type(pesoInput, '95');
    await seleccionarMotivo();
    await userEvent.click(screen.getByRole('button', { name: /reetiquetar lote/i }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al reetiquetar el lote.'));
  });

  it('dado click en cancelar cuando no esta enviando entonces cierra sin llamar a la API', async () => {
    const onOpenChange = vi.fn();
    render(<ReetiquetarModal open={true} onOpenChange={onOpenChange} lote={LOTE} />);
    await userEvent.click(screen.getByRole('button', { name: /cancelar/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado lote null cuando renderiza entonces no falla y no calcula desvio', () => {
    render(<ReetiquetarModal open={true} onOpenChange={vi.fn()} lote={null} />);
    expect(screen.getByRole('button', { name: /reetiquetar lote/i })).toBeDisabled();
  });
});
