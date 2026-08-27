import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePagosCliente } from './usePagosCliente';
import type { Cliente, PagoCliente } from '../../lib/types';

const mockPost = vi.fn();
const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: {
    post: (...args: any[]) => mockPost(...args),
    get: (...args: any[]) => mockGet(...args),
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

const CLIENTE: Cliente = { id: 1, nombre_razon_social: 'Cliente X' } as any;

describe('usePagosCliente', () => {
  beforeEach(() => {
    mockPost.mockReset();
    mockGet.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado sin cliente seleccionado cuando crea un pago entonces exige un monto valido y no llama a la API', async () => {
    const setSelectedCliente = vi.fn();
    const fetchData = vi.fn();
    const { result } = renderHook(() => usePagosCliente(null, setSelectedCliente, fetchData));

    await act(async () => { await result.current.handleCreatePago(); });
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor ingresa un monto válido');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado monto cero o negativo cuando crea un pago entonces no llama a la API', async () => {
    const { result } = renderHook(() => usePagosCliente(CLIENTE, vi.fn(), vi.fn()));
    act(() => { result.current.setPagoForm((p) => ({ ...p, monto: '0' })); });
    await act(async () => { await result.current.handleCreatePago(); });
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado monto valido cuando crea un pago normal entonces llama post y refresca el cliente', async () => {
    mockPost.mockResolvedValue({});
    mockGet.mockResolvedValue({ data: { ...CLIENTE, saldo_pendiente: 0 } });
    const setSelectedCliente = vi.fn();
    const fetchData = vi.fn();
    const { result } = renderHook(() => usePagosCliente(CLIENTE, setSelectedCliente, fetchData));
    act(() => { result.current.setPagoForm((p) => ({ ...p, monto: '100' })); });

    await act(async () => { await result.current.handleCreatePago(); });

    expect(mockPost).toHaveBeenCalledWith('/pagos-cliente/', expect.objectContaining({ cliente: 1, monto: 100 }));
    expect(toastSuccessMock).toHaveBeenCalledWith('Pago registrado correctamente');
    expect(setSelectedCliente).toHaveBeenCalled();
    expect(fetchData).toHaveBeenCalled();
  });

  it('dado es_anticipo en true cuando crea un pago entonces notifica como anticipo', async () => {
    mockPost.mockResolvedValue({});
    mockGet.mockResolvedValue({ data: CLIENTE });
    const { result } = renderHook(() => usePagosCliente(CLIENTE, vi.fn(), vi.fn()));
    act(() => { result.current.setPagoForm((p) => ({ ...p, monto: '50', es_anticipo: true })); });

    await act(async () => { await result.current.handleCreatePago(); });
    expect(toastSuccessMock).toHaveBeenCalledWith('Anticipo registrado correctamente');
  });

  it('dado el backend rechaza el monto cuando crea un pago entonces muestra el mensaje de campo monto', async () => {
    mockPost.mockRejectedValue({ response: { data: { monto: ['El monto excede el saldo pendiente'] } } });
    const { result } = renderHook(() => usePagosCliente(CLIENTE, vi.fn(), vi.fn()));
    act(() => { result.current.setPagoForm((p) => ({ ...p, monto: '999' })); });

    await act(async () => { await result.current.handleCreatePago(); });
    expect(toastErrorMock).toHaveBeenCalledWith('El monto excede el saldo pendiente');
  });

  it('dado un error de red sin detalle cuando crea un pago entonces muestra el mensaje generico', async () => {
    mockPost.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => usePagosCliente(CLIENTE, vi.fn(), vi.fn()));
    act(() => { result.current.setPagoForm((p) => ({ ...p, monto: '50' })); });

    await act(async () => { await result.current.handleCreatePago(); });
    expect(toastErrorMock).toHaveBeenCalledWith('Error al registrar el pago');
  });

  it('dado un pago cuando inicia la reversion entonces setea el pago y limpia la justificacion previa', () => {
    const { result } = renderHook(() => usePagosCliente(CLIENTE, vi.fn(), vi.fn()));
    const pago: PagoCliente = { id: 9 } as any;
    act(() => { result.current.handleInitiatePagoReversion(pago); });
    expect(result.current.pagoRevertir).toEqual(pago);
    expect(result.current.pagoReversionJustificacion).toBe('');
  });

  it('dado sin justificacion cuando confirma la reversion entonces exige una justificacion valida', async () => {
    const { result } = renderHook(() => usePagosCliente(CLIENTE, vi.fn(), vi.fn()));
    act(() => { result.current.handleInitiatePagoReversion({ id: 9 } as any); });

    await act(async () => { await result.current.handleConfirmPagoReversion(); });
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor ingresa una justificación válida');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado justificacion valida cuando confirma la reversion entonces llama post y refresca el cliente', async () => {
    mockPost.mockResolvedValue({});
    mockGet.mockResolvedValue({ data: CLIENTE });
    const setSelectedCliente = vi.fn();
    const fetchData = vi.fn();
    const { result } = renderHook(() => usePagosCliente(CLIENTE, setSelectedCliente, fetchData));
    act(() => { result.current.handleInitiatePagoReversion({ id: 9 } as any); });
    act(() => { result.current.setPagoReversionJustificacion('Error de digitación'); });

    await act(async () => { await result.current.handleConfirmPagoReversion(); });

    expect(mockPost).toHaveBeenCalledWith('/pagos-cliente/9/revertir/', { justificacion: 'Error de digitación' });
    expect(toastSuccessMock).toHaveBeenCalled();
    expect(result.current.pagoRevertir).toBeNull();
    expect(setSelectedCliente).toHaveBeenCalled();
    expect(fetchData).toHaveBeenCalled();
  });

  it('dado sin cliente seleccionado cuando confirma la reversion entonces no intenta refrescar el cliente', async () => {
    mockPost.mockResolvedValue({});
    const { result } = renderHook(() => usePagosCliente(null, vi.fn(), vi.fn()));
    act(() => { result.current.handleInitiatePagoReversion({ id: 9 } as any); });
    act(() => { result.current.setPagoReversionJustificacion('motivo valido'); });

    await act(async () => { await result.current.handleConfirmPagoReversion(); });
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado fallo del backend cuando confirma la reversion entonces reporta el error del campo justificacion', async () => {
    mockPost.mockRejectedValue({ response: { data: { justificacion: 'Debe tener al menos 10 caracteres' } } });
    const { result } = renderHook(() => usePagosCliente(CLIENTE, vi.fn(), vi.fn()));
    act(() => { result.current.handleInitiatePagoReversion({ id: 9 } as any); });
    act(() => { result.current.setPagoReversionJustificacion('corta'); });

    await act(async () => { await result.current.handleConfirmPagoReversion(); });
    expect(toastErrorMock).toHaveBeenCalledWith('Debe tener al menos 10 caracteres');
    expect(result.current.pagoReversionLoading).toBe(false);
  });
});
