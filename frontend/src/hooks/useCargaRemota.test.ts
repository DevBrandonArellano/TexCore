import { describe, it, expect, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useCargaRemota } from './useCargaRemota';

describe('useCargaRemota', () => {
  it('dado montaje cuando carga entonces expone los datos y termina la carga', async () => {
    const { result } = renderHook(() => useCargaRemota(() => Promise.resolve('ok'), 1));
    expect(result.current.cargando).toBe(true);
    await waitFor(() => expect(result.current.datos).toBe('ok'));
    expect(result.current.cargando).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('dado error del servidor cuando carga entonces expone un mensaje legible', async () => {
    const err = { response: { status: 403, data: {} } };
    const { result } = renderHook(() => useCargaRemota(() => Promise.reject(err), 1));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.datos).toBeNull();
    expect(result.current.cargando).toBe(false);
  });

  it('dado cambio de clave cuando la respuesta vieja llega tarde entonces se descarta', async () => {
    let resolverVieja: (v: string) => void = () => {};
    const cargar = vi
      .fn()
      .mockImplementationOnce(() => new Promise<string>((r) => { resolverVieja = r; }))
      .mockResolvedValueOnce('nueva');
    const { result, rerender } = renderHook(({ clave }) => useCargaRemota(cargar, clave), { initialProps: { clave: 1 } });
    rerender({ clave: 2 });
    await waitFor(() => expect(result.current.datos).toBe('nueva'));
    act(() => resolverVieja('vieja'));
    expect(result.current.datos).toBe('nueva');
  });

  it('dado recargar cuando se invoca entonces vuelve a pedir', async () => {
    const cargar = vi.fn().mockResolvedValue('x');
    const { result } = renderHook(() => useCargaRemota(cargar, 1));
    await waitFor(() => expect(result.current.cargando).toBe(false));
    act(() => result.current.recargar());
    await waitFor(() => expect(cargar).toHaveBeenCalledTimes(2));
  });

  it('dado cambio de clave cuando la carga vieja falla tarde entonces el error se descarta', async () => {
    let rechazarVieja: (e: unknown) => void = () => {};
    const cargar = vi
      .fn()
      .mockImplementationOnce(() => new Promise<string>((_, r) => { rechazarVieja = r; }))
      .mockResolvedValueOnce('nueva');
    const { result, rerender } = renderHook(({ clave }) => useCargaRemota(cargar, clave), { initialProps: { clave: 1 } });
    rerender({ clave: 2 });
    await waitFor(() => expect(result.current.datos).toBe('nueva'));
    await act(async () => rechazarVieja(new Error('vieja')));
    expect(result.current.error).toBeNull();
    expect(result.current.cargando).toBe(false);
  });
});
