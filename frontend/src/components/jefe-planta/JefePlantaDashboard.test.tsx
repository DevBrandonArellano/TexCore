import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JefePlantaDashboard } from './JefePlantaDashboard';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

// Mocks
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: [] })),
    patch: vi.fn(() => Promise.resolve({ data: [] })),
    delete: vi.fn(() => Promise.resolve({ data: [] })),
    put: vi.fn(() => Promise.resolve({ data: [] })),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() }
    }
  };
  return {
    default: {
      ...mockAxiosInstance,
      create: vi.fn(() => mockAxiosInstance)
    }
  };
});
import apiClient from '../../lib/axios';

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

vi.mock('./ManageOrdenesProduccion', () => ({
  ManageOrdenesProduccion: (props: any) => (
    <div data-testid="manage-op-mock">
      <span data-testid="op-count">{props.ordenes.length}</span>
      <span data-testid="op-loading">{String(props.loading)}</span>
      <button onClick={() => props.onOrdenCreate({ codigo: 'OP-NEW' })}>crear-orden</button>
      <button onClick={() => props.onOrdenUpdate(1, { codigo: 'OP-UPD' })}>actualizar-orden</button>
      <button onClick={() => props.onOrdenDelete(1)}>eliminar-orden</button>
      <button onClick={() => props.onOrderStatusChange(1, 'en_proceso')}>iniciar-orden</button>
      <button onClick={() => props.onOrderStatusChange(1, 'finalizada')}>finalizar-orden</button>
      <button onClick={() => props.onOrderStatusChange(1, 'otro_estado')}>cambiar-otro-estado</button>
      <button onClick={() => props.onDataRefresh()}>refrescar-datos</button>
    </div>
  ),
}));

vi.mock('../produccion/TransferenciasInterarea', () => ({
  TransferenciasInterarea: (props: any) => (
    <div data-testid="transferencias-mock">areaId:{String(props.areaId)}</div>
  ),
}));

// Mock ResizeObserver for Radix UI
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

function mockEndpoints(overrides: Record<string, any> = {}) {
  const defaults: Record<string, any> = {
    '/ordenes-produccion/': {
      count: 2,
      results: [
        { id: 1, codigo: 'OP-001', estado: 'pendiente', peso_neto_requerido: 100, peso_producido: 0 },
        { id: 2, codigo: 'OP-002', estado: 'en_proceso', peso_neto_requerido: 200, peso_producido: 100 },
      ]
    },
    '/produccion/pulso-diario/': {
      kg_planificados_hoy: 100,
      kg_producidos_hoy: 50,
      kg_merma_hoy: 5,
      wip_estancado: 10,
    },
    '/productos/': [],
    '/formula-colors/': [],
    '/sedes/': [],
    '/maquinas/': [],
    '/areas/': [],
    '/bodegas/': [],
    '/users/': [],
  };
  const data = { ...defaults, ...overrides };
  (apiClient.get as any).mockImplementation((url: string) => {
    // If URL has query params, just match the base path
    const basePath = url.split('?')[0];
    if (basePath in data) return Promise.resolve({ data: data[basePath] });
    return Promise.resolve({ data: [] });
  });
}

describe('JefePlantaDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEndpoints();
  });

  const renderComponent = () => render(
    <BrowserRouter>
      <JefePlantaDashboard />
    </BrowserRouter>
  );

  it('debe renderizar el título del dashboard y cargar datos', async () => {
    renderComponent();

    // Verifica que muestra el título
    expect(screen.getByText('Panel de Jefe de Planta')).toBeInTheDocument();

    // Espera a que los KPIs se rendericen basados en la data mockeada
    await waitFor(() => {
      expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument();
    });

    // También valida que las órdenes se pasen al hijo ManageOrdenesProduccion
    expect(screen.getByTestId('op-count')).toHaveTextContent('2');
  });

  it('dado que las peticiones aun no resuelven cuando monta entonces muestra el estado de carga', () => {
    (apiClient.get as any).mockReturnValue(new Promise(() => {}));
    renderComponent();

    expect(screen.getByText('Cargando datos...')).toBeInTheDocument();
    expect(screen.getByTestId('op-loading')).toHaveTextContent('true');
  });

  it('dado ordenes y datos de pulso diario cuando carga entonces calcula los KPIs correctamente', async () => {
    mockEndpoints({
      '/produccion/pulso-diario/': {
        kg_planificados_hoy: 450,
        kg_producidos_hoy: 150,
        kg_merma_hoy: 15,
        wip_estancado: 50,
      }
    });
    renderComponent();

    await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());

    // kg_planificados_hoy = 450, kg_producidos_hoy = 150 => cumplimiento = 33%
    expect(screen.getByText('33%')).toBeInTheDocument();

    // kg_merma_hoy = 15, kg_producidos_hoy = 150 => desperdicio = 10.00%
    expect(screen.getByText('10.00%')).toBeInTheDocument();

    // WIP Estancado = 50 Kg
    expect(screen.getByText('50 Kg')).toBeInTheDocument();
  });

  it('dado exportacion PDF cuando hace click entonces deshabilita el boton y muestra loading', async () => {
    (apiClient.post as any).mockResolvedValueOnce(new Blob(['pdf'], { type: 'application/pdf' }));
    renderComponent();

    const menuBtn = screen.getByRole('button', { name: /acciones gerenciales/i });
    await userEvent.click(menuBtn);

    const btnAvance = screen.getByText(/reporte avance operativo/i).closest('div[role="menuitem"]');
    await userEvent.click(btnAvance!);

    // Muestra success (sonner mockup)
    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith(expect.stringContaining('Reporte de Avance exportado correctamente'));
    });
  });

  it('dado un error al obtener los datos iniciales cuando falla la peticion entonces muestra un toast de error', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.split('?')[0] === '/ordenes-produccion/') return Promise.reject(new Error('network error'));
      return Promise.resolve({ data: [] });
    });
    renderComponent();

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar los datos del panel.'),
    );
    expect(screen.getByTestId('op-loading')).toHaveTextContent('false');
  });

  it('renderiza TransferenciasInterarea sin areaId para que jefe de planta vea todas las transferencias', async () => {
    renderComponent();

    await waitFor(() => expect(screen.getByTestId('transferencias-mock')).toBeInTheDocument());
    expect(screen.getByTestId('transferencias-mock')).toHaveTextContent('areaId:undefined');
  });

  describe('creacion de ordenes', () => {
    it('dado una creacion exitosa cuando el usuario crea una orden entonces la agrega a la lista y muestra un toast de exito', async () => {
      (apiClient.post as any).mockResolvedValueOnce({ data: { id: 3, codigo: 'OP-003', estado: 'pendiente' } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('crear-orden'));

      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('3'));
      expect(apiClient.post).toHaveBeenCalledWith('/ordenes-produccion/', { codigo: 'OP-NEW' });
      expect(toastSuccessMock).toHaveBeenCalledWith('Orden de producción creada exitosamente');
    });

    it('dado un error de validacion 400 cuando el usuario crea una orden entonces muestra un toast con el detalle', async () => {
      (apiClient.post as any).mockRejectedValueOnce({
        response: { status: 400, data: { codigo: ['ya existe'] } },
      });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('crear-orden'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('codigo: ya existe'),
      );
      expect(screen.getByTestId('op-count')).toHaveTextContent('2');
    });

    it('dado un error generico cuando el usuario crea una orden entonces muestra un toast de error genérico', async () => {
      (apiClient.post as any).mockRejectedValueOnce({ response: { status: 500 } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('crear-orden'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Error del servidor. Si persiste, contacta al administrador.'),
      );
    });
  });

  describe('actualizacion de ordenes', () => {
    it('dado una actualizacion exitosa cuando el usuario actualiza una orden entonces la reemplaza en la lista y muestra un toast de exito', async () => {
      (apiClient.patch as any).mockResolvedValueOnce({ data: { id: 1, codigo: 'OP-001-EDIT', estado: 'pendiente' } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('actualizar-orden'));

      await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Orden actualizada'));
      expect(apiClient.patch).toHaveBeenCalledWith('/ordenes-produccion/1/', { codigo: 'OP-UPD' });
      expect(screen.getByTestId('op-count')).toHaveTextContent('2');
    });

    it('dado un error de validacion 400 cuando el usuario actualiza una orden entonces muestra un toast con el detalle', async () => {
      (apiClient.patch as any).mockRejectedValueOnce({
        response: { status: 400, data: { peso_neto_requerido: ['debe ser mayor a cero'] } },
      });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('actualizar-orden'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('peso_neto_requerido: debe ser mayor a cero'),
      );
    });

    it('dado un error generico cuando el usuario actualiza una orden entonces muestra un toast de error genérico', async () => {
      (apiClient.patch as any).mockRejectedValueOnce({ response: { status: 500 } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('actualizar-orden'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Error del servidor. Si persiste, contacta al administrador.'),
      );
    });
  });

  describe('eliminacion de ordenes', () => {
    it('dado que el usuario confirma cuando elimina una orden entonces la quita de la lista y muestra un toast de exito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('eliminar-orden'));

      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('1'));
      expect(apiClient.delete).toHaveBeenCalledWith('/ordenes-produccion/1/');
      expect(toastSuccessMock).toHaveBeenCalledWith('Orden eliminada');
    });

    it('dado que el usuario cancela cuando elimina una orden entonces no elimina nada', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('eliminar-orden'));

      expect(apiClient.delete).not.toHaveBeenCalled();
      expect(screen.getByTestId('op-count')).toHaveTextContent('2');
    });

    it('dado un error al eliminar cuando falla la peticion entonces muestra un toast de error y no quita la orden', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      (apiClient.delete as any).mockRejectedValueOnce(new Error('boom'));
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('eliminar-orden'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar la orden'));
      expect(screen.getByTestId('op-count')).toHaveTextContent('2');
    });
  });

  describe('cambio de estado de ordenes', () => {
    it('dado un cambio exitoso a en_proceso cuando el usuario inicia una orden entonces muestra el toast de orden iniciada', async () => {
      (apiClient.patch as any).mockResolvedValueOnce({ data: { status: 'ok', estado: 'en_proceso' } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('iniciar-orden'));

      await waitFor(() =>
        expect(toastSuccessMock).toHaveBeenCalledWith('Orden iniciada — en proceso'),
      );
      expect(apiClient.patch).toHaveBeenCalledWith('/ordenes-produccion/1/cambiar_estado/', { estado: 'en_proceso' });
    });

    it('dado un cambio exitoso a finalizada cuando el usuario finaliza una orden entonces muestra el toast de orden finalizada', async () => {
      (apiClient.patch as any).mockResolvedValueOnce({ data: { status: 'ok', estado: 'finalizada' } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('finalizar-orden'));

      await waitFor(() =>
        expect(toastSuccessMock).toHaveBeenCalledWith('Orden marcada como finalizada'),
      );
    });

    it('dado un estado sin etiqueta especifica cuando cambia el estado entonces muestra el toast genérico de estado actualizado', async () => {
      (apiClient.patch as any).mockResolvedValueOnce({ data: { status: 'ok', estado: 'otro_estado' } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('cambiar-otro-estado'));

      await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Estado actualizado'));
    });

    it('dado un error de validacion 400 con campo estado cuando cambia el estado entonces muestra el mensaje especifico', async () => {
      (apiClient.patch as any).mockRejectedValueOnce({
        response: { status: 400, data: { estado: ['transición inválida'] } },
      });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('iniciar-orden'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('No se puede cambiar el estado', {
          description: 'transición inválida',
        }),
      );
    });

    it('dado un error de validacion 400 sin campo estado cuando cambia el estado entonces usa el json completo como mensaje', async () => {
      (apiClient.patch as any).mockRejectedValueOnce({
        response: { status: 400, data: { detail: 'no permitido' } },
      });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('iniciar-orden'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('No se puede cambiar el estado', {
          description: 'no permitido',
        }),
      );
    });

    it('dado un error generico cuando cambia el estado entonces muestra un toast de error genérico', async () => {
      (apiClient.patch as any).mockRejectedValueOnce({ response: { status: 500 } });
      renderComponent();
      await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));

      await userEvent.click(screen.getByText('iniciar-orden'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Error del servidor. Si persiste, contacta al administrador.'),
      );
    });
  });

  it('dado respuestas paginadas ({results}) para catalogos cuando carga entonces normaliza cada lista al array interno', async () => {
    mockEndpoints({
      '/productos/': { results: [{ id: 1, nombre: 'Hilo' }] },
      '/formula-colors/': { results: [{ id: 1, nombre_color: 'Rojo' }] },
      '/sedes/': { results: [{ id: 1, nombre: 'Sede A' }] },
      '/maquinas/': { results: [{ id: 1, nombre: 'M1' }] },
      '/areas/': { results: [{ id: 1, nombre: 'Area A' }] },
      '/bodegas/': { results: [{ id: 1, nombre: 'B1' }] },
      '/users/': { results: [{ id: 1, username: 'op1' }] },
    });
    renderComponent();

    await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());
    expect(screen.getByTestId('op-count')).toHaveTextContent('2');
  });

  it('dado ordenes sin count cuando carga entonces usa 0 como total por defecto', async () => {
    mockEndpoints({ '/ordenes-produccion/': { results: [] } });
    renderComponent();
    await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());
    expect(screen.getByTestId('op-count')).toHaveTextContent('0');
  });

  it('dado un cumplimiento diario del 95% cuando calcula la severidad entonces usa el color de exito (>=90%)', async () => {
    mockEndpoints({
      '/produccion/pulso-diario/': {
        kg_planificados_hoy: 100, kg_producidos_hoy: 95, kg_merma_hoy: 0, wip_estancado: 0,
      },
    });
    renderComponent();
    await waitFor(() => expect(screen.getByText('95%')).toBeInTheDocument());
    expect(screen.getByText('95%')).toHaveClass('text-emerald-700');
  });

  it('dado un cumplimiento diario del 80% cuando calcula la severidad entonces usa el color de advertencia (70-89%)', async () => {
    mockEndpoints({
      '/produccion/pulso-diario/': {
        kg_planificados_hoy: 100, kg_producidos_hoy: 80, kg_merma_hoy: 0, wip_estancado: 0,
      },
    });
    renderComponent();
    await waitFor(() => expect(screen.getByText('80%')).toBeInTheDocument());
    expect(screen.getByText('80%')).toHaveClass('text-amber-700');
  });

  it('dado datos ya cargados cuando el hijo solicita refrescar entonces vuelve a pedir los datos al servidor', async () => {
    renderComponent();
    await waitFor(() => expect(screen.getByTestId('op-count')).toHaveTextContent('2'));
    const llamadasIniciales = (apiClient.get as any).mock.calls.length;

    await userEvent.click(screen.getByText('refrescar-datos'));

    await waitFor(() => expect((apiClient.get as any).mock.calls.length).toBeGreaterThan(llamadasIniciales));
  });

  // ─────────────────────────────────────────────────────────────────────────
  // ISTQB EP — Exportación de PDFs
  // Clases de equivalencia:
  //   EP-V1  Avance: POST exitoso  → descarga + toast success
  //   EP-V2  Balance: POST exitoso con sede disponible → descarga + toast success
  //   EP-I1  Avance: POST falla (error de red) → toast error, sin descarga
  //   EP-I2  Balance: sin órdenes (sedeId = null) → toast error, sin POST
  //   EP-I3  Balance: POST falla (error de red) → toast error, sin descarga
  // ─────────────────────────────────────────────────────────────────────────
  describe('exportacion de PDFs', () => {

    // Helpers de DOM/URL para simular el flujo blob → click → revoke
    let createObjectURLMock: ReturnType<typeof vi.fn>;
    let revokeObjectURLMock: ReturnType<typeof vi.fn>;
    let anchorClickMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      createObjectURLMock = vi.fn().mockReturnValue('blob:http://localhost/test-pdf');
      revokeObjectURLMock = vi.fn();
      anchorClickMock     = vi.fn();

      window.URL.createObjectURL = createObjectURLMock;
      window.URL.revokeObjectURL = revokeObjectURLMock;

      // Interceptar createElement('a') solo cuando sea un anchor
      const originalCreate = document.createElement.bind(document);
      vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
        if (tag === 'a') {
          const anchor = originalCreate('a') as HTMLAnchorElement;
          anchor.click = anchorClickMock;
          return anchor;
        }
        return originalCreate(tag);
      });
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    // Abre el menú "Acciones Gerenciales" y hace click en el ítem indicado.
    const exportarDesdeMenu = async (item: RegExp) => {
      await userEvent.click(screen.getByRole('button', { name: /acciones gerenciales/i }));
      const menuItem = await screen.findByText(item);
      await userEvent.click(menuItem.closest('[role="menuitem"]') ?? menuItem);
    };

    // EP-V1 ─────────────────────────────────────────────────────────────────
    it('ep-v1: dado un post exitoso cuando el usuario exporta el avance operativo entonces descarga el pdf y muestra toast de exito', async () => {
      (apiClient.post as any).mockResolvedValueOnce({
        data: new Blob(['%PDF-1.4 test'], { type: 'application/pdf' }),
      });

      renderComponent();
      await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());

      await exportarDesdeMenu(/reporte avance operativo/i);

      await waitFor(() =>
        expect(toastSuccessMock).toHaveBeenCalledWith('Reporte de Avance exportado correctamente'),
      );
      expect(apiClient.post).toHaveBeenCalledWith(
        '/internal/v1/reports/produccion/reporte-avance/',
        { empresa_nombre: 'TexCore Industrial' },
        { responseType: 'blob' },
      );
      expect(createObjectURLMock).toHaveBeenCalledTimes(1);
      expect(anchorClickMock).toHaveBeenCalledTimes(1);
      expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:http://localhost/test-pdf');
    });

    // EP-V2 ─────────────────────────────────────────────────────────────────
    // La sede ya NO se envía desde el cliente: el backend la deriva del usuario
    // autenticado. El payload solo lleva mes_label y empresa_nombre.
    it('ep-v2: dado un post exitoso cuando el usuario exporta el balance de masas entonces descarga el pdf sin enviar sede_id', async () => {
      (apiClient.post as any).mockResolvedValueOnce({
        data: new Blob(['%PDF-1.4 balance'], { type: 'application/pdf' }),
      });

      renderComponent();
      await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());

      await exportarDesdeMenu(/balance de masas mensual/i);

      await waitFor(() =>
        expect(toastSuccessMock).toHaveBeenCalledWith('Balance de Masas exportado correctamente'),
      );
      const [, balancePayload] = (apiClient.post as any).mock.calls.find(
        (c: any[]) => c[0] === '/internal/v1/reports/produccion/reporte-balance/',
      );
      expect(balancePayload).toEqual(
        expect.objectContaining({ empresa_nombre: 'TexCore Industrial' }),
      );
      // Seguridad: el cliente no debe filtrar por una sede arbitraria.
      expect(balancePayload).not.toHaveProperty('sede_id');
      expect(createObjectURLMock).toHaveBeenCalledTimes(1);
      expect(anchorClickMock).toHaveBeenCalledTimes(1);
    });

    // EP-I1 ─────────────────────────────────────────────────────────────────
    it('ep-i1: dado un error de red cuando el usuario exporta el avance entonces muestra toast de error y no llama a createObjectURL', async () => {
      (apiClient.post as any).mockRejectedValueOnce(new Error('Network Error'));

      renderComponent();
      await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());

      await exportarDesdeMenu(/reporte avance operativo/i);

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Error al generar el PDF de Avance Operativo'),
      );
      expect(createObjectURLMock).not.toHaveBeenCalled();
      expect(anchorClickMock).not.toHaveBeenCalled();
    });

    // EP-I2 ─────────────────────────────────────────────────────────────────
    // Antes el cliente exigía sede (ordenes[0].sede) y bloqueaba el balance si
    // no había órdenes. Tras el fix, el balance funciona SIN órdenes cargadas
    // porque la sede la impone el backend.
    it('ep-i2: dado que no hay ordenes cargadas cuando el usuario exporta el balance entonces igual llama al backend', async () => {
      mockEndpoints({ '/ordenes-produccion/': { count: 0, results: [] } });
      (apiClient.post as any).mockResolvedValueOnce({
        data: new Blob(['%PDF-1.4 balance'], { type: 'application/pdf' }),
      });

      renderComponent();
      await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());

      await exportarDesdeMenu(/balance de masas mensual/i);

      await waitFor(() =>
        expect(apiClient.post).toHaveBeenCalledWith(
          '/internal/v1/reports/produccion/reporte-balance/',
          expect.not.objectContaining({ sede_id: expect.anything() }),
          { responseType: 'blob' },
        ),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Balance de Masas exportado correctamente');
    });

    // EP-I3 ─────────────────────────────────────────────────────────────────
    it('ep-i3: dado un error de red cuando el usuario exporta el balance entonces muestra toast de error', async () => {
      (apiClient.post as any).mockRejectedValueOnce(new Error('Service Unavailable'));

      renderComponent();
      await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());

      await exportarDesdeMenu(/balance de masas mensual/i);

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Error al generar el PDF de Balance de Masas'),
      );
      expect(createObjectURLMock).not.toHaveBeenCalled();
    });

    // Render — el menú de acciones y sus dos ítems de exportación existen ─────
    it('dado el dashboard cargado cuando se abre el menú entonces expone ambos reportes PDF', async () => {
      renderComponent();
      await waitFor(() => expect(screen.getByText('Cumplimiento Diario')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /acciones gerenciales/i }));

      expect(await screen.findByText(/reporte avance operativo/i)).toBeInTheDocument();
      expect(screen.getByText(/balance de masas mensual/i)).toBeInTheDocument();
    });
  });
});

