import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useSedeSpecificData } from './useSedeSpecificData';

// 0 sentencias sin cubrir pero 32 ramas muertas: el hook ya se ejercita
// indirectamente desde los dashboards padre, pero siempre con respuestas
// planas (array) y siempre con selectedSedeId definido. Aquí se cierran
// las ramas de `getData` (paginado vs. plano vs. ausente) y las guardas
// "sede no seleccionada" de los handlers de creación.

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

function mockTodosVacios() {
  mockGet.mockResolvedValue({ data: [] });
}

describe('useSedeSpecificData', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado selectedSedeId vacio cuando monta entonces no consulta el backend', () => {
    const setAreas = vi.fn();
    renderHook(() => useSedeSpecificData('', 0, setAreas));
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado respuestas paginadas ({results}) cuando carga entonces getData extrae el array interno', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/bodegas/') return Promise.resolve({ data: { results: [{ id: 1, nombre: 'B1' }] } });
      return Promise.resolve({ data: { results: [] } });
    });
    const setAreas = vi.fn();
    const { result } = renderHook(() => useSedeSpecificData('1', 2, setAreas));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.bodegas).toEqual([{ id: 1, nombre: 'B1' }]);
  });

  it('dado respuestas planas (array) cuando carga entonces getData las usa directamente', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/bodegas/') return Promise.resolve({ data: [{ id: 1, nombre: 'B1' }] });
      return Promise.resolve({ data: [] });
    });
    const setAreas = vi.fn();
    const { result } = renderHook(() => useSedeSpecificData('1', 2, setAreas));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.bodegas).toEqual([{ id: 1, nombre: 'B1' }]);
  });

  it('dado respuesta sin data cuando carga entonces getData retorna arreglo vacio sin fallar', async () => {
    mockGet.mockResolvedValue({});
    const setAreas = vi.fn();
    const { result } = renderHook(() => useSedeSpecificData('1', 2, setAreas));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.bodegas).toEqual([]);
  });

  it('dado error de red cuando carga entonces notifica y termina de cargar', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    const setAreas = vi.fn();
    const { result } = renderHook(() => useSedeSpecificData('1', 2, setAreas));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar datos de la sede');
  });

  it('dado sede no seleccionada y hay sedes disponibles cuando crea usuario entonces exige seleccionar sede primero', async () => {
    mockTodosVacios();
    const setAreas = vi.fn();
    const { result } = renderHook(() => useSedeSpecificData('', 3, setAreas));

    let creado: boolean = true;
    await act(async () => {
      creado = await result.current.handleUserCreate({ username: 'nuevo' });
    });
    expect(creado).toBe(false);
    expect(toastErrorMock).toHaveBeenCalledWith(
      expect.stringContaining('Selecciona una sede'),
    );
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado sede seleccionada cuando crea usuario entonces envia el payload con la sede numerica', async () => {
    mockTodosVacios();
    mockPost.mockResolvedValue({ data: { id: 9, username: 'nuevo' } });
    const setAreas = vi.fn();
    const { result } = renderHook(() => useSedeSpecificData('5', 3, setAreas));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let creado: boolean = false;
    await act(async () => {
      creado = await result.current.handleUserCreate({ username: 'nuevo' });
    });
    expect(creado).toBe(true);
    expect(mockPost).toHaveBeenCalledWith('/users/', expect.objectContaining({ sede: 5 }));
    expect(toastSuccessMock).toHaveBeenCalled();
  });

  it('dado fallo del backend cuando crea usuario entonces reporta el error via showApiError', async () => {
    mockTodosVacios();
    mockPost.mockRejectedValue({ response: { status: 400, data: { username: ['Ya existe'] } } });
    const setAreas = vi.fn();
    const { result } = renderHook(() => useSedeSpecificData('5', 3, setAreas));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let creado: boolean = true;
    await act(async () => {
      creado = await result.current.handleUserCreate({ username: 'dup' });
    });
    expect(creado).toBe(false);
    expect(toastErrorMock).toHaveBeenCalled();
  });

  // Handlers de Cliente/Bodega/Formula/Chemical/Product/Proveedor: mismo
  // esqueleto try/create-guard, update, delete-con-confirm que User (ya
  // cubierto arriba), nunca ejercitado para el resto de entidades. Recorre
  // create (con sede)/update/delete-cancelado/delete-confirmado para cada
  // una — cierra la mayoría de las 31 ramas muertas del archivo.
  const ENTIDADES: Array<{
    key: 'Cliente' | 'Bodega' | 'Formula' | 'Chemical' | 'Product' | 'Proveedor';
    endpoint: string;
    createData: Record<string, unknown>;
  }> = [
    { key: 'Cliente', endpoint: '/clientes/', createData: { nombre_razon_social: 'Cliente X' } },
    { key: 'Bodega', endpoint: '/bodegas/', createData: { nombre: 'Bodega X' } },
    { key: 'Formula', endpoint: '/formula-colors/', createData: { nombre_color: 'Rojo X' } },
    { key: 'Chemical', endpoint: '/chemicals/', createData: { codigo: 'Q1', descripcion: 'Quimico X' } },
    { key: 'Product', endpoint: '/productos/', createData: { codigo: 'P1', descripcion: 'Producto X' } },
    { key: 'Proveedor', endpoint: '/proveedores/', createData: { nombre: 'Proveedor X' } },
  ];

  ENTIDADES.forEach(({ key, endpoint, createData }) => {
    describe(`handlers de ${key}`, () => {
      it(`dado sede seleccionada cuando crea ${key} entonces envia el payload con la sede numerica`, async () => {
        mockTodosVacios();
        mockPost.mockResolvedValue({ data: { id: 1 } });
        const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
        await waitFor(() => expect(result.current.loading).toBe(false));

        let creado = false;
        await act(async () => {
          creado = await (result.current as any)[`handle${key}Create`](createData);
        });
        expect(creado).toBe(true);
        expect(mockPost).toHaveBeenCalledWith(endpoint, expect.objectContaining({ sede: 7 }));
        expect(toastSuccessMock).toHaveBeenCalled();
      });

      it(`dado fallo del backend cuando crea ${key} entonces reporta el error`, async () => {
        mockTodosVacios();
        mockPost.mockRejectedValue({ response: { status: 400, data: {} } });
        const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
        await waitFor(() => expect(result.current.loading).toBe(false));

        let creado = true;
        await act(async () => {
          creado = await (result.current as any)[`handle${key}Create`](createData);
        });
        expect(creado).toBe(false);
        expect(toastErrorMock).toHaveBeenCalled();
      });

      it(`dado ${key} existente cuando actualiza entonces llama patch y notifica exito`, async () => {
        mockTodosVacios();
        mockPatch.mockResolvedValue({ data: { id: 99 } });
        const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
        await waitFor(() => expect(result.current.loading).toBe(false));

        let actualizado = false;
        await act(async () => {
          actualizado = await (result.current as any)[`handle${key}Update`](99, createData);
        });
        expect(actualizado).toBe(true);
        expect(mockPatch).toHaveBeenCalledWith(`${endpoint}99/`, expect.anything());
        expect(toastSuccessMock).toHaveBeenCalled();
      });

      it(`dado fallo del backend cuando actualiza ${key} entonces reporta el error`, async () => {
        mockTodosVacios();
        mockPatch.mockRejectedValue({ response: { status: 500, data: {} } });
        const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
        await waitFor(() => expect(result.current.loading).toBe(false));

        let actualizado = true;
        await act(async () => {
          actualizado = await (result.current as any)[`handle${key}Update`](99, createData);
        });
        expect(actualizado).toBe(false);
        expect(toastErrorMock).toHaveBeenCalled();
      });

      it(`dado confirmacion cancelada cuando elimina ${key} entonces no llama al backend`, async () => {
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
        mockTodosVacios();
        const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
        await waitFor(() => expect(result.current.loading).toBe(false));

        await act(async () => {
          await (result.current as any)[`handle${key}Delete`](99);
        });
        expect(mockDelete).not.toHaveBeenCalled();
        confirmSpy.mockRestore();
      });

      it(`dado confirmacion aceptada cuando elimina ${key} entonces llama delete y notifica exito`, async () => {
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
        mockTodosVacios();
        mockDelete.mockResolvedValue({});
        const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
        await waitFor(() => expect(result.current.loading).toBe(false));

        await act(async () => {
          await (result.current as any)[`handle${key}Delete`](99);
        });
        expect(mockDelete).toHaveBeenCalledWith(`${endpoint}99/`);
        expect(toastSuccessMock).toHaveBeenCalled();
        confirmSpy.mockRestore();
      });

      it(`dado fallo del backend cuando elimina ${key} entonces reporta el error`, async () => {
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
        mockTodosVacios();
        mockDelete.mockRejectedValue({ response: { status: 500, data: {} } });
        const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
        await waitFor(() => expect(result.current.loading).toBe(false));

        await act(async () => {
          await (result.current as any)[`handle${key}Delete`](99);
        });
        expect(toastErrorMock).toHaveBeenCalled();
        confirmSpy.mockRestore();
      });
    });
  });

  // Ramas index1 aún muertas: `selectedSedeId ? parseInt(...) : null` siempre
  // tomaba el lado truthy (todos los tests de arriba usan sede definida), los
  // `.map` de los updates nunca tenían un item que NO coincidiera con el id
  // actualizado, y los `?? ''`/`|| null` de codigo/descripcion/nombre/presentacion
  // en Chemical/Product/Proveedor nunca recibían valores undefined.
  it('dado sede vacia y sin sedes disponibles cuando crea entidades entonces omite el guard y envia sede null', async () => {
    mockTodosVacios();
    mockPost.mockResolvedValue({ data: { id: 1 } });
    const { result } = renderHook(() => useSedeSpecificData('', 0, vi.fn()));

    await act(async () => { await result.current.handleUserCreate({ username: 'u' }); });
    expect(mockPost).toHaveBeenCalledWith('/users/', expect.objectContaining({ sede: null }));

    await act(async () => { await result.current.handleBodegaCreate({ nombre: 'b' }); });
    expect(mockPost).toHaveBeenCalledWith('/bodegas/', expect.objectContaining({ sede: null }));

    await act(async () => { await result.current.handleChemicalCreate({ codigo: 'Q1', descripcion: 'd' }); });
    expect(mockPost).toHaveBeenCalledWith('/chemicals/', expect.objectContaining({ sede: null }));

    await act(async () => { await result.current.handleProductCreate({ codigo: 'P1', descripcion: 'd' }); });
    expect(mockPost).toHaveBeenCalledWith('/productos/', expect.objectContaining({ sede: null }));

    await act(async () => { await result.current.handleProveedorCreate({ nombre: 'Prov' }); });
    expect(mockPost).toHaveBeenCalledWith('/proveedores/', expect.objectContaining({ sede: null }));

    await act(async () => { await result.current.handleFormulaCreate({ nombre_color: 'Rojo' }); });
    expect(mockPost).toHaveBeenCalledWith('/formula-colors/', expect.objectContaining({ sede: null }));
  });

  it('dado chemical/product sin codigo ni descripcion cuando crea o actualiza entonces usa cadena vacia por defecto', async () => {
    mockTodosVacios();
    mockPost.mockResolvedValue({ data: { id: 1 } });
    mockPatch.mockResolvedValue({ data: { id: 1 } });
    const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => { await result.current.handleChemicalCreate({}); });
    expect(mockPost).toHaveBeenCalledWith('/chemicals/', expect.objectContaining({ codigo: '', descripcion: '' }));

    await act(async () => { await result.current.handleChemicalUpdate(1, {}); });
    expect(mockPatch).toHaveBeenCalledWith('/chemicals/1/', expect.objectContaining({ codigo: '', descripcion: '' }));

    await act(async () => { await result.current.handleProductCreate({}); });
    expect(mockPost).toHaveBeenCalledWith('/productos/', expect.objectContaining({ codigo: '', descripcion: '' }));

    await act(async () => { await result.current.handleProductUpdate(1, {}); });
    expect(mockPatch).toHaveBeenCalledWith('/productos/1/', expect.objectContaining({ codigo: '', descripcion: '' }));
  });

  it('dado proveedor sin nombre cuando crea entonces usa cadena vacia por defecto', async () => {
    mockTodosVacios();
    mockPost.mockResolvedValue({ data: { id: 1 } });
    const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => { await result.current.handleProveedorCreate({}); });
    expect(mockPost).toHaveBeenCalledWith('/proveedores/', expect.objectContaining({ nombre: '' }));
  });

  const UPDATE_MAP_CASES: Array<{
    key: 'User' | 'Bodega' | 'Formula' | 'Chemical' | 'Product' | 'Proveedor';
    getUrl: string;
    field: 'users' | 'bodegas' | 'formulasColor' | 'quimicos' | 'productos' | 'proveedores';
    existingItem: Record<string, unknown>;
  }> = [
    { key: 'User', getUrl: '/users/', field: 'users', existingItem: { id: 1, username: 'u1' } },
    { key: 'Bodega', getUrl: '/bodegas/', field: 'bodegas', existingItem: { id: 1, nombre: 'B1' } },
    { key: 'Formula', getUrl: '/formula-colors/', field: 'formulasColor', existingItem: { id: 1, nombre_color: 'Rojo' } },
    { key: 'Chemical', getUrl: '/chemicals/', field: 'quimicos', existingItem: { id: 1, codigo: 'Q1' } },
    { key: 'Product', getUrl: '/productos/', field: 'productos', existingItem: { id: 1, codigo: 'P1' } },
    { key: 'Proveedor', getUrl: '/proveedores/', field: 'proveedores', existingItem: { id: 1, nombre: 'Prov1' } },
  ];

  UPDATE_MAP_CASES.forEach(({ key, getUrl, field, existingItem }) => {
    it(`dado ${key} existente con id distinto cuando actualiza otro id entonces conserva el item sin cambios`, async () => {
      mockGet.mockImplementation((url: string) =>
        Promise.resolve({ data: url === getUrl ? [existingItem] : [] }),
      );
      mockPatch.mockResolvedValue({ data: { id: 99 } });
      const { result } = renderHook(() => useSedeSpecificData('7', 3, vi.fn()));
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect((result.current as any)[field]).toEqual([existingItem]);

      await act(async () => {
        await (result.current as any)[`handle${key}Update`](99, {});
      });

      expect((result.current as any)[field]).toEqual([existingItem]);
    });
  });
});
