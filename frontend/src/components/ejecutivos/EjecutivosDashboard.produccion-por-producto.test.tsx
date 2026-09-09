/**
 * ISTQB — Nivel: Componente / Integración
 * Técnica : Black-box (equivalencia de partición + valor límite + transición de estados)
 * Cubre   : CU-EJ-08 Ver Producción por Producto (tabla + impresión PDF)
 *           CU-EJ-09 Ver Historial de Producción de un Producto (drill-down por fila)
 *            - Carga de la tabla al entrar al tab Producción
 *            - Estados vacío / cargando / error de la tabla
 *            - Clic en una fila abre el modal e invoca el endpoint de historial
 *            - Estados vacío / cargando / error del historial
 *            - Botón Imprimir: llama al endpoint con responseType blob y abre el PDF
 *            - Propagación de sede_id cuando hay filtro de sede activo
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

// ── Mocks de infraestructura ──────────────────────────────────────────────────

vi.mock('../../lib/axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: [] })),
    patch: vi.fn(() => Promise.resolve({ data: [] })),
    delete: vi.fn(() => Promise.resolve({ data: [] })),
    put: vi.fn(() => Promise.resolve({ data: [] })),
  },
}));
import apiClient from '../../lib/axios';

vi.mock('../../lib/auth', () => ({
  useAuth: () => ({
    profile: { user: { username: 'gerente_test' }, role: 'ejecutivo' },
  }),
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

// Contexto propio por instancia de Select — el tab Producción monta dos
// selects a la vez (sede en el header + rango de tendencia); una única
// variable global haría que el segundo pise el onValueChange del primero.
const SelectCtx = React.createContext<((v: string) => void) | undefined>(undefined);
vi.mock('../ui/select', () => ({
  Select: ({ children, value, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}>
      <div data-testid="mock-select" data-value={value}>{children}</div>
    </SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return (
      <button data-testid={`select-item-${value}`} onClick={() => onValueChange?.(value)}>
        {children}
      </button>
    );
  },
}));

global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

// ── Importación del componente ────────────────────────────────────────────────

import { EjecutivosDashboard } from './EjecutivosDashboard';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PRODUCTOS_FULL = [
  { producto_id: 1, producto_codigo: 'HIL-001', producto_nombre: 'Hilo Nylon 40/1', kg_total: 320.5, num_lotes: 6 },
  { producto_id: 2, producto_codigo: 'TEL-007', producto_nombre: 'Tela Jersey', kg_total: 150, num_lotes: 2 },
];

const HISTORIAL_PRODUCTO_1 = [
  { fecha: '2026-08-10', kg: 0 },
  { fecha: '2026-08-11', kg: 50.5 },
];

/** Respuestas vacías para todos los endpoints de carga del dashboard */
const mockApiVacio = (url: string) => {
  const vacios: Record<string, object> = {
    '/kpi-ejecutivo/': {
      produccion: { ops_pendiente: 0, ops_en_proceso: 0, ops_finalizada: 0, kg_hoy: 0, kg_semana: 0, kg_mes: 0, tiempo_promedio_lote_min: 0 },
      mrp: { ocs_pendientes: 0, ocs_aprobadas: 0, ocs_rechazadas: 0, productos_en_deficit: 0 },
      stock: { productos_bajo_minimo: 0 },
      cartera: { cuentas_por_cobrar: 0, cartera_vencida: 0, pedidos_pendientes: 0, pedidos_despachados: 0 },
    },
    '/produccion/resumen/': { ops_por_estado: [], kg_hoy: 0, kg_semana: 0, kg_mes: 0, tiempo_promedio_lote_min: 0 },
    '/produccion/tendencia/': [],
    '/produccion/por-producto/': [],
    '/produccion/historial-producto/': [],
    '/inventory/alertas-stock/': [],
    '/inventory/stock/': [],
    '/clientes/': [],
    '/pedidos-venta/': [],
    '/sedes/': [],
  };
  return Promise.resolve({ data: vacios[url] ?? [] });
};

const setupUser = () => userEvent.setup({ pointerEventsCheck: 0 });

const renderDashboard = () =>
  render(
    <BrowserRouter>
      <EjecutivosDashboard />
    </BrowserRouter>
  );

/** Navega al tab Producción y espera a que se cargue */
const navigateToProduccion = async (user: ReturnType<typeof userEvent.setup>) => {
  renderDashboard();
  await waitFor(() => expect(screen.queryByText('Panel Ejecutivo')).toBeInTheDocument());
  const tab = screen.getByRole('tab', { name: /Producción/i });
  await user.click(tab);
  await waitFor(() => expect(screen.getByText('Producción por Producto')).toBeInTheDocument());
};

// ── Suite de tests ────────────────────────────────────────────────────────────

describe('EjecutivosDashboard — Producción por Producto (CU-EJ-08/09)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation(mockApiVacio);
    window.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/fake-blob-url');
    window.URL.revokeObjectURL = vi.fn();
    window.open = vi.fn();
  });

  // ── 1. Carga y renderizado de la tabla ────────────────────────────────────

  it('debe cargar y renderizar la tabla de producción por producto al entrar al tab', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/produccion/por-producto/') return Promise.resolve({ data: PRODUCTOS_FULL });
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);

    await waitFor(() => {
      expect(screen.getByText('HIL-001')).toBeInTheDocument();
      expect(screen.getByText('Hilo Nylon 40/1')).toBeInTheDocument();
      expect(screen.getByText('TEL-007')).toBeInTheDocument();
    });
  });

  it('[EP] debe mostrar estado vacío cuando no hay producción en el rango', async () => {
    const user = setupUser();
    await navigateToProduccion(user);

    await waitFor(() => {
      expect(screen.getByText('Sin producción registrada en el rango seleccionado.')).toBeInTheDocument();
    });
  });

  it('debe mostrar toast.error cuando falla la carga de producción por producto', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/produccion/por-producto/') return Promise.reject(new Error('500'));
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar la producción por producto');
    });
  });

  // ── 2. Drill-down: clic en una fila abre el historial (CU-EJ-09) ──────────

  it('debe llamar al endpoint de historial con producto_id al hacer clic en una fila', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/produccion/por-producto/') return Promise.resolve({ data: PRODUCTOS_FULL });
      if (url === '/produccion/historial-producto/') return Promise.resolve({ data: HISTORIAL_PRODUCTO_1 });
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);
    await waitFor(() => expect(screen.getByText('HIL-001')).toBeInTheDocument());

    await user.click(screen.getByTestId('fila-producto-1'));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/produccion/historial-producto/',
        expect.objectContaining({ params: expect.objectContaining({ producto_id: 1 }) })
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Historial de Producción: Hilo Nylon 40/1')).toBeInTheDocument();
      expect(screen.getByText('2026-08-11')).toBeInTheDocument();
    });
  });

  it('[EP] debe mostrar estado vacío del historial cuando el producto no tiene producción diaria', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/produccion/por-producto/') return Promise.resolve({ data: PRODUCTOS_FULL });
      if (url === '/produccion/historial-producto/') return Promise.resolve({ data: [] });
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);
    await waitFor(() => expect(screen.getByText('HIL-001')).toBeInTheDocument());
    await user.click(screen.getByTestId('fila-producto-1'));

    await waitFor(() => {
      expect(screen.getByText('Sin producción diaria registrada para este producto.')).toBeInTheDocument();
    });
  });

  it('debe mostrar toast.error cuando falla la carga del historial del producto', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/produccion/por-producto/') return Promise.resolve({ data: PRODUCTOS_FULL });
      if (url === '/produccion/historial-producto/') return Promise.reject(new Error('500'));
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);
    await waitFor(() => expect(screen.getByText('HIL-001')).toBeInTheDocument());
    await user.click(screen.getByTestId('fila-producto-1'));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar el historial del producto');
    });
  });

  // ── 3. Imprimir PDF ────────────────────────────────────────────────────────

  it('debe llamar al endpoint de impresión con responseType blob y abrir el PDF', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/produccion/por-producto/imprimir/') return Promise.resolve({ data: new Blob(['%PDF-fake']) });
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);
    await user.click(screen.getByTestId('btn-imprimir-produccion-producto'));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/produccion/por-producto/imprimir/',
        expect.objectContaining({ responseType: 'blob' })
      );
    });
    expect(window.open).toHaveBeenCalledWith('blob:http://localhost/fake-blob-url', '_blank');
  });

  it('debe mostrar toast.error cuando falla la generación del PDF', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/produccion/por-producto/imprimir/') return Promise.reject(new Error('503'));
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);
    await user.click(screen.getByTestId('btn-imprimir-produccion-producto'));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Error al generar el PDF de producción por producto');
    });
  });

  // ── 4. EP: sede_id se propaga a los tres endpoints ────────────────────────

  it('[EP] debe incluir sede_id en los params al consultar producción por producto cuando hay sede seleccionada', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/sedes/') return Promise.resolve({ data: [{ id: 42, nombre: 'Sede Principal' }] });
      return mockApiVacio(url);
    });

    await navigateToProduccion(user);

    const sedeBtn = await screen.findByTestId('select-item-42');
    await user.click(sedeBtn);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/produccion/por-producto/',
        expect.objectContaining({ params: expect.objectContaining({ sede_id: '42' }) })
      );
    });
  });

  it('[EP] no debe incluir sede_id en los params cuando no hay sede seleccionada', async () => {
    const user = setupUser();
    await navigateToProduccion(user);

    await waitFor(() => {
      const call = (apiClient.get as any).mock.calls.find(
        (c: any[]) => c[0] === '/produccion/por-producto/'
      );
      expect(call).toBeDefined();
      expect(call[1].params).not.toHaveProperty('sede_id');
    });
  });
});
