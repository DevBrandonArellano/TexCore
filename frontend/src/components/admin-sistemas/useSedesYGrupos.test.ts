import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useSedesYGrupos } from './useSedesYGrupos';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
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

function setup(selectedSedeId = '') {
  const setSearchParams = vi.fn();
  const setAreas = vi.fn();
  const hook = renderHook(() => useSedesYGrupos({ selectedSedeId, setSearchParams, setAreas }));
  return { ...hook, setSearchParams, setAreas };
}

describe('useSedesYGrupos', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado respuestas planas (array) cuando carga entonces normaliza sedes y grupos', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/sedes/') return Promise.resolve({ data: [{ id: 1, nombre: 'Sede A' }] });
      if (url === '/groups/') return Promise.resolve({ data: [{ id: 1, name: 'admin_sistemas' }] });
      return Promise.resolve({ data: [] });
    });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));
    expect(result.current.sedes).toEqual([{ id: 1, nombre: 'Sede A' }]);
    expect(result.current.groups).toEqual([{ id: 1, name: 'admin_sistemas' }]);
  });

  it('dado respuestas paginadas ({results}) cuando carga entonces extrae el array interno', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/sedes/') return Promise.resolve({ data: { results: [{ id: 1, nombre: 'Sede A' }] } });
      if (url === '/groups/') return Promise.resolve({ data: { results: [] } });
      return Promise.resolve({ data: [] });
    });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));
    expect(result.current.sedes).toEqual([{ id: 1, nombre: 'Sede A' }]);
  });

  it('dado sin sede seleccionada y hay sedes cuando carga entonces auto-selecciona la primera en la URL', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/sedes/') return Promise.resolve({ data: [{ id: 7, nombre: 'Sede A' }] });
      return Promise.resolve({ data: [] });
    });
    const { setSearchParams } = setup('');
    await waitFor(() => expect(setSearchParams).toHaveBeenCalled());
    const updater = setSearchParams.mock.calls[0][0];
    const params = new URLSearchParams();
    updater(params);
    expect(params.get('sede')).toBe('7');
  });

  it('dado sede ya seleccionada cuando carga entonces no reescribe la URL', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/sedes/') return Promise.resolve({ data: [{ id: 7, nombre: 'Sede A' }] });
      return Promise.resolve({ data: [] });
    });
    const { result, setSearchParams } = setup('7');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));
    expect(setSearchParams).not.toHaveBeenCalled();
  });

  it('dado error de red cuando carga entonces igual marca sedesFetchDone', async () => {
    mockGet.mockRejectedValue(new Error('boom'));
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));
    expect(result.current.sedes).toEqual([]);
  });

  it('dado datos validos cuando crea una sede entonces llama post y notifica exito', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPost.mockResolvedValue({ data: { id: 1, nombre: 'Nueva Sede' } });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = false;
    await act(async () => { ok = await result.current.handleSedeCreate({ nombre: 'Nueva Sede' }); });
    expect(ok).toBe(true);
    expect(toastSuccessMock).toHaveBeenCalled();
  });

  it('dado fallo del backend cuando crea una sede entonces reporta el error', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPost.mockRejectedValue({ response: { status: 400, data: {} } });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = true;
    await act(async () => { ok = await result.current.handleSedeCreate({ nombre: 'X' }); });
    expect(ok).toBe(false);
    expect(toastErrorMock).toHaveBeenCalled();
  });

  it('dado sede existente cuando actualiza entonces llama patch y notifica exito', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPatch.mockResolvedValue({ data: { id: 1, nombre: 'Actualizada' } });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = false;
    await act(async () => { ok = await result.current.handleSedeUpdate(1, { nombre: 'Actualizada' }); });
    expect(ok).toBe(true);
    expect(mockPatch).toHaveBeenCalledWith('/sedes/1/', { nombre: 'Actualizada' });
  });

  it('dado fallo del backend cuando actualiza una sede entonces reporta el error', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPatch.mockRejectedValue({ response: { status: 500, data: {} } });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = true;
    await act(async () => { ok = await result.current.handleSedeUpdate(1, {}); });
    expect(ok).toBe(false);
    expect(toastErrorMock).toHaveBeenCalled();
  });

  it('dado confirmacion cancelada cuando elimina una sede entonces no llama al backend', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    mockGet.mockResolvedValue({ data: [] });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    await act(async () => { await result.current.handleSedeDelete(1); });
    expect(mockDelete).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('dado confirmacion aceptada cuando elimina una sede entonces llama delete y notifica exito', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockGet.mockResolvedValue({ data: [] });
    mockDelete.mockResolvedValue({});
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    await act(async () => { await result.current.handleSedeDelete(1); });
    expect(mockDelete).toHaveBeenCalledWith('/sedes/1/');
    expect(toastSuccessMock).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('dado fallo del backend cuando elimina una sede entonces reporta el error', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockGet.mockResolvedValue({ data: [] });
    mockDelete.mockRejectedValue({ response: { status: 500, data: {} } });
    const { result } = setup();
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    await act(async () => { await result.current.handleSedeDelete(1); });
    expect(toastErrorMock).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('dado sin sede seleccionada y hay sedes disponibles cuando crea un area entonces exige seleccionar sede primero', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/sedes/') return Promise.resolve({ data: [{ id: 1, nombre: 'Sede A' }] });
      return Promise.resolve({ data: [] });
    });
    const { result } = setup('');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = true;
    await act(async () => { ok = await result.current.handleAreaCreate({ nombre: 'Area X' }); });
    expect(ok).toBe(false);
    expect(toastErrorMock).toHaveBeenCalledWith(expect.stringContaining('Selecciona una sede'));
  });

  it('dado sin sedes disponibles en absoluto cuando crea un area sin sede seleccionada entonces indica que no hay sedes', async () => {
    mockGet.mockResolvedValue({ data: [] });
    const { result } = setup('');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = true;
    await act(async () => { ok = await result.current.handleAreaCreate({ nombre: 'Area X' }); });
    expect(ok).toBe(false);
    expect(toastErrorMock).toHaveBeenCalledWith(expect.stringContaining('No hay sedes disponibles'));
  });

  it('dado sede seleccionada cuando crea un area entonces llama post con el payload correcto', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPost.mockResolvedValue({ data: { id: 1, nombre: 'Area X' } });
    const { result } = setup('5');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = false;
    await act(async () => { ok = await result.current.handleAreaCreate({ nombre: 'Area X' }); });
    expect(ok).toBe(true);
    expect(mockPost).toHaveBeenCalledWith('/areas/', expect.objectContaining({ sede: 5 }));
  });

  it('dado fallo del backend cuando crea un area entonces reporta el error', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPost.mockRejectedValue({ response: { status: 400, data: {} } });
    const { result } = setup('5');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = true;
    await act(async () => { ok = await result.current.handleAreaCreate({ nombre: 'X' }); });
    expect(ok).toBe(false);
    expect(toastErrorMock).toHaveBeenCalled();
  });

  it('dado area existente cuando actualiza entonces llama patch y notifica exito', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPatch.mockResolvedValue({ data: { id: 1, nombre: 'Area Actualizada' } });
    const { result } = setup('5');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = false;
    await act(async () => { ok = await result.current.handleAreaUpdate(1, { nombre: 'Area Actualizada' }); });
    expect(ok).toBe(true);
  });

  it('dado fallo del backend cuando actualiza un area entonces reporta el error', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPatch.mockRejectedValue({ response: { status: 500, data: {} } });
    const { result } = setup('5');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    let ok = true;
    await act(async () => { ok = await result.current.handleAreaUpdate(1, {}); });
    expect(ok).toBe(false);
    expect(toastErrorMock).toHaveBeenCalled();
  });

  it('dado confirmacion cancelada cuando elimina un area entonces no llama al backend', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    mockGet.mockResolvedValue({ data: [] });
    const { result } = setup('5');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    await act(async () => { await result.current.handleAreaDelete(1); });
    expect(mockDelete).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('dado confirmacion aceptada cuando elimina un area entonces llama delete y notifica exito', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockGet.mockResolvedValue({ data: [] });
    mockDelete.mockResolvedValue({});
    const { result } = setup('5');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    await act(async () => { await result.current.handleAreaDelete(1); });
    expect(mockDelete).toHaveBeenCalledWith('/areas/1/');
    expect(toastSuccessMock).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('dado fallo del backend cuando elimina un area entonces reporta el error', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockGet.mockResolvedValue({ data: [] });
    mockDelete.mockRejectedValue({ response: { status: 500, data: {} } });
    const { result } = setup('5');
    await waitFor(() => expect(result.current.sedesFetchDone).toBe(true));

    await act(async () => { await result.current.handleAreaDelete(1); });
    expect(toastErrorMock).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
