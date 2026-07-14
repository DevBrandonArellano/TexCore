import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RegistrarTransformacion } from './RegistrarTransformacion';

const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { post: (...args: any[]) => mockPost(...args) },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
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
    return <button onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const MAQUINAS = [{ id: 1, nombre: 'Tintura 1' } as any];
const PRODUCTOS = [{ id: 5, codigo: 'TELA-002', descripcion: 'Tela procesada' } as any];

// Los <Label> del componente no tienen htmlFor/id asociado al input (no es
// accesible por getByLabelText) — se consulta por rol/tipo y posición.
const pesoEntradaInput = () => screen.getAllByRole('spinbutton')[0] as HTMLInputElement;
const pesoSalidaInput = () => screen.getAllByRole('spinbutton')[1] as HTMLInputElement;
const inicioInput = () => document.querySelectorAll('input[type="datetime-local"]')[0] as HTMLInputElement;
const finInput = () => document.querySelectorAll('input[type="datetime-local"]')[1] as HTMLInputElement;

function renderComponent(overrides = {}) {
  const onOpenChange = vi.fn();
  const onSuccess = vi.fn();
  const props = {
    open: true,
    onOpenChange,
    ordenId: 42,
    maquinas: MAQUINAS,
    productos: PRODUCTOS,
    onSuccess,
    ...overrides,
  };
  render(<RegistrarTransformacion {...props} />);
  return { onOpenChange, onSuccess };
}

async function llenarFormularioValido() {
  await userEvent.click(screen.getByText('Tintura 1'));
  await userEvent.click(screen.getByText('TELA-002 — Tela procesada'));
  await userEvent.type(pesoEntradaInput(), '100');
  await userEvent.type(pesoSalidaInput(), '95');
}

describe('RegistrarTransformacion', () => {
  beforeEach(() => {
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado sin maquina seleccionada cuando registra entonces muestra error de validacion', async () => {
    renderComponent();
    await userEvent.click(screen.getByText('Registrar'));
    expect(toastErrorMock).toHaveBeenCalledWith('Selecciona la máquina.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado sin producto de salida cuando registra entonces muestra error de validacion', async () => {
    renderComponent();
    await userEvent.click(screen.getByText('Tintura 1'));
    await userEvent.click(screen.getByText('Registrar'));
    expect(toastErrorMock).toHaveBeenCalledWith('Selecciona el producto de salida (nuevo código).');
  });

  it('dado peso de entrada cero cuando registra entonces muestra error BVA', async () => {
    renderComponent();
    await userEvent.click(screen.getByText('Tintura 1'));
    await userEvent.click(screen.getByText('TELA-002 — Tela procesada'));
    await userEvent.type(pesoEntradaInput(), '0');
    await userEvent.type(pesoSalidaInput(), '0');
    await userEvent.click(screen.getByText('Registrar'));
    expect(toastErrorMock).toHaveBeenCalledWith('El peso de entrada debe ser mayor que cero.');
  });

  it('dado peso de salida negativo cuando registra entonces muestra error', async () => {
    renderComponent();
    await userEvent.click(screen.getByText('Tintura 1'));
    await userEvent.click(screen.getByText('TELA-002 — Tela procesada'));
    await userEvent.type(pesoEntradaInput(), '10');
    await userEvent.type(pesoSalidaInput(), '-5');
    await userEvent.click(screen.getByText('Registrar'));
    expect(toastErrorMock).toHaveBeenCalledWith('El peso de salida no es válido.');
  });

  it('dado peso de salida mayor al de entrada cuando registra entonces muestra error de merma negativa', async () => {
    renderComponent();
    await userEvent.click(screen.getByText('Tintura 1'));
    await userEvent.click(screen.getByText('TELA-002 — Tela procesada'));
    await userEvent.type(pesoEntradaInput(), '50');
    await userEvent.type(pesoSalidaInput(), '60');
    await userEvent.click(screen.getByText('Registrar'));
    expect(toastErrorMock).toHaveBeenCalledWith('El peso de salida no puede superar el de entrada (merma negativa).');
  });

  it('dado fecha fin anterior a inicio cuando registra entonces muestra error', async () => {
    renderComponent();
    await llenarFormularioValido();
    await userEvent.clear(finInput());
    await userEvent.type(finInput(), '2020-01-01T00:00');
    await userEvent.clear(inicioInput());
    await userEvent.type(inicioInput(), '2026-01-01T00:00');
    await userEvent.click(screen.getByText('Registrar'));
    expect(toastErrorMock).toHaveBeenCalledWith('La fecha de fin no puede ser anterior al inicio.');
  });

  it('dado pesos validos cuando calcula la merma entonces la muestra en kg', async () => {
    renderComponent();
    await userEvent.type(pesoEntradaInput(), '100');
    await userEvent.type(pesoSalidaInput(), '95');
    expect(screen.getByText(/5\.000 kg/)).toBeInTheDocument();
  });

  it('dado datos validos cuando registra entonces envia el payload correcto y notifica exito', async () => {
    mockPost.mockResolvedValueOnce({ data: { id: 1 } });
    const { onOpenChange, onSuccess } = renderComponent();

    await llenarFormularioValido();
    await userEvent.click(screen.getByText('Registrar'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/ordenes-produccion/42/registrar-transformacion/',
      expect.objectContaining({
        maquina: 1,
        producto_salida: 5,
        peso_entrada: '100',
        peso_salida: '95',
        observaciones: '',
      }),
    ));
    expect(toastSuccessMock).toHaveBeenCalledWith('Transformación registrada correctamente.');
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(onSuccess).toHaveBeenCalled();
  });

  it('dado error del backend con detail string cuando registra entonces muestra ese mensaje', async () => {
    mockPost.mockRejectedValueOnce({ response: { data: { detail: 'La máquina no pertenece al área.' } } });
    renderComponent();
    await llenarFormularioValido();
    await userEvent.click(screen.getByText('Registrar'));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('La máquina no pertenece al área.'));
  });

  it('dado error del backend con detail como dict de campos cuando registra entonces junta los mensajes', async () => {
    mockPost.mockRejectedValueOnce({
      response: { data: { detail: { peso_salida: ['No puede ser mayor.'], maquina: ['Es obligatoria.'] } } },
    });
    renderComponent();
    await llenarFormularioValido();
    await userEvent.click(screen.getByText('Registrar'));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No puede ser mayor. Es obligatoria.'));
  });

  it('dado error sin detail cuando registra entonces muestra mensaje generico', async () => {
    mockPost.mockRejectedValueOnce({ response: { data: {} } });
    renderComponent();
    await llenarFormularioValido();
    await userEvent.click(screen.getByText('Registrar'));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No se pudo registrar la transformación.'));
  });

  it('dado entradaEsperada cuando renderiza entonces la muestra en la descripcion', () => {
    renderComponent({ entradaEsperada: 'TELA-001' });
    expect(screen.getByText(/entrará: TELA-001/)).toBeInTheDocument();
  });

  it('dado click en cancelar cuando se presiona entonces cierra el dialogo', async () => {
    const { onOpenChange } = renderComponent();
    await userEvent.click(screen.getByText('Cancelar'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
