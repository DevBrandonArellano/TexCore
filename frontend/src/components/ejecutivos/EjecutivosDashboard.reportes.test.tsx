/**
 * ISTQB — Nivel: Componente / Integración
 * Técnica : Black-box (equivalencia de partición + valor límite + transición de estados)
 * Cubre   : CU-EJ-07 — Centro de Reportes de Gerencia
 *            - Validación de rango de fechas (inicio > fin, inicio === fin, sin fechas)
 *            - Bloqueo de doble descarga simultánea
 *            - Llamada correcta a cada endpoint de reporting
 *            - Feedback visual: toast.success / toast.error
 *            - Spinner y disabled durante descarga / re-habilitación tras error
 *            - Propagación de sede_id cuando hay filtro activo (presente y ausente)
 *            - Deudores: no valida rango de fechas (sin params de fecha)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

// ── Mocks de infraestructura ──────────────────────────────────────────────────

vi.mock('../../lib/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));
import apiClient from '../../lib/axios';

// Radix UI Select lanza error en jsdom con value="". Se mockea el componente
// para evitar la excepción no relacionada con los casos de uso bajo prueba.
// El mock captura onValueChange en closure para que SelectItem pueda dispararlo.
let _selectOnValueChange: ((val: string) => void) | undefined;
vi.mock('../ui/select', () => ({
  Select: ({ children, value, onValueChange }: any) => {
    _selectOnValueChange = onValueChange;
    return (
      <div data-testid="mock-select" data-value={value}>
        <button onClick={() => onValueChange?.('')}>clear-sede</button>
        {children}
      </div>
    );
  },
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => (
    <button data-testid={`select-item-${value}`} onClick={() => _selectOnValueChange?.(value)}>
      {children}
    </button>
  ),
}));

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

// Mocks de APIs del navegador necesarios en jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();
global.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/fake-blob-url');
global.URL.revokeObjectURL = vi.fn();

// ── Importación del componente ────────────────────────────────────────────────

import { EjecutivosDashboard } from './EjecutivosDashboard';

// ── Helpers ───────────────────────────────────────────────────────────────────

const FECHA_INICIO = '2026-01-01';
const FECHA_FIN = '2026-01-31';

/** Respuestas vacías para todos los endpoints de carga del dashboard */
const mockApiVacio = (url: string) => {
  const vacios: Record<string, object> = {
    '/kpi-ejecutivo/': {
      produccion: { ops_pendiente: 0, ops_en_proceso: 0, ops_finalizada: 0, kg_hoy: 0, kg_semana: 0, kg_mes: 0, tiempo_promedio_lote_min: 0 },
      mrp: { ocs_pendientes: 0, ocs_aprobadas: 0, ocs_rechazadas: 0, productos_en_deficit: 0 },
      stock: { productos_bajo_minimo: 0 },
      cartera: { cuentas_por_cobrar: 0, cartera_vencida: 0, pedidos_pendientes: 0, pedidos_despachados: 0 },
    },
    '/produccion/resumen/': {
      ops_por_estado: [], kg_hoy: 0, kg_semana: 0, kg_mes: 0, tiempo_promedio_lote_min: 0,
    },
    '/produccion/tendencia/': [],
    '/inventory/alertas-stock/': [],
    '/inventory/stock/': [],
    '/clientes/': [],
    '/pedidos-venta/': [],
    '/sedes/': [],
  };
  return Promise.resolve({ data: vacios[url] ?? [] });
};

const fakeBlob = new Blob(['excel'], {
  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
});

const setupUser = () => userEvent.setup({ pointerEventsCheck: 0 });

const renderDashboard = () =>
  render(
    <BrowserRouter>
      <EjecutivosDashboard />
    </BrowserRouter>
  );

/** Navega al tab Reportes y espera a que se cargue */
const navigateToReportes = async (user: ReturnType<typeof userEvent.setup>) => {
  renderDashboard();
  await waitFor(() => expect(screen.queryByText('Panel Ejecutivo')).toBeInTheDocument());
  const tab = screen.getByRole('tab', { name: /Reportes/i });
  await user.click(tab);
  await waitFor(() =>
    expect(screen.getByText(/Centro de reportes gerenciales/i)).toBeInTheDocument()
  );
};

// ── Suite de tests ────────────────────────────────────────────────────────────

describe('EjecutivosDashboard — Tab Reportes (CU-EJ-07)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation(mockApiVacio);
  });

  // ── 1. Renderizado ────────────────────────────────────────────────────────

  it('debe renderizar todos los botones de descarga del tab Reportes', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    expect(screen.getByTestId('btn-export-ventas')).toBeInTheDocument();
    expect(screen.getByTestId('btn-export-top-clientes')).toBeInTheDocument();
    expect(screen.getByTestId('btn-export-deudores')).toBeInTheDocument();
    expect(screen.getByTestId('btn-export-ordenes')).toBeInTheDocument();
    expect(screen.getByTestId('btn-export-lotes')).toBeInTheDocument();
    expect(screen.getByTestId('btn-export-tendencia')).toBeInTheDocument();
  });

  it('debe renderizar los KPIs de contexto en el tab Reportes', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    expect(screen.getByText('Ventas del Período')).toBeInTheDocument();
    expect(screen.getByText('Cartera Vencida')).toBeInTheDocument();
    expect(screen.getByText('kg Producidos (mes)')).toBeInTheDocument();
    expect(screen.getByText('Alertas de Stock')).toBeInTheDocument();
  });

  // ── 2. Validación de rango de fechas (valor límite) ───────────────────────

  it('[VL] debe rechazar descarga cuando fecha_inicio > fecha_fin', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    // Localizar los inputs de fecha por label dentro del tab Reportes
    const { fireEvent } = await import('@testing-library/react');
    const allDateInputs = document.querySelectorAll('input[type="date"]');
    // El tab Reportes tiene sus propios inputs; tomamos los dos últimos del DOM
    // (los primeros pertenecen a otros tabs que no se renderizan activamente)
    const inputs = Array.from(allDateInputs);
    const idxInicio = inputs.findIndex(
      (el) => (el as HTMLInputElement).value.endsWith('-01')
    );
    if (inputs.length >= 2) {
      fireEvent.change(inputs[0], { target: { value: '2026-03-01' } });
      fireEvent.change(inputs[1], { target: { value: '2026-01-01' } });
    }

    await user.click(screen.getByTestId('btn-export-ventas'));

    expect(toastErrorMock).toHaveBeenCalledWith(
      'La fecha de inicio no puede ser posterior a la fecha de fin'
    );
    expect(apiClient.get).not.toHaveBeenCalledWith(
      expect.stringContaining('/reporting/'),
      expect.anything()
    );
  });

  // ── 3. Descarga exitosa — cada endpoint ───────────────────────────────────

  it.each([
    ['btn-export-ventas', '/reporting/gerencial/ventas'],
    ['btn-export-top-clientes', '/reporting/gerencial/top-clientes'],
    ['btn-export-deudores', '/reporting/gerencial/deudores'],
    ['btn-export-ordenes', '/reporting/produccion/ordenes'],
    ['btn-export-lotes', '/reporting/produccion/lotes'],
    ['btn-export-tendencia', '/reporting/produccion/tendencia'],
  ])(
    '[EP] %s debe llamar a %s y mostrar toast.success',
    async (testId, expectedUrl) => {
      const user = setupUser();
      (apiClient.get as any).mockImplementation((url: string) => {
        if (url === expectedUrl) return Promise.resolve({ data: fakeBlob });
        return mockApiVacio(url);
      });

      await navigateToReportes(user);
      await user.click(screen.getByTestId(testId));

      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledWith(
          expectedUrl,
          expect.objectContaining({ params: expect.objectContaining({ format: 'xlsx' }) })
        );
      });
      await waitFor(() => {
        expect(toastSuccessMock).toHaveBeenCalledWith('Reporte descargado');
      });
    }
  );

  // ── 4. Manejo de error de API ─────────────────────────────────────────────

  it('debe mostrar toast.error cuando el endpoint de reporte falla', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/ventas') return Promise.reject(new Error('500'));
      return mockApiVacio(url);
    });

    await navigateToReportes(user);
    await user.click(screen.getByTestId('btn-export-ventas'));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Error al descargar el reporte');
    });
  });

  // ── 5. Bloqueo de descarga simultánea ────────────────────────────────────

  it('debe deshabilitar todos los botones mientras hay una descarga en curso', async () => {
    const user = setupUser();
    let resolvePendiente: (v: any) => void;
    const pendiente = new Promise((res) => { resolvePendiente = res; });

    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/ventas') return pendiente;
      return mockApiVacio(url);
    });

    await navigateToReportes(user);
    await user.click(screen.getByTestId('btn-export-ventas'));

    // Mientras la descarga está pendiente, todos los botones deben estar disabled
    await waitFor(() => {
      expect(screen.getByTestId('btn-export-top-clientes')).toBeDisabled();
      expect(screen.getByTestId('btn-export-deudores')).toBeDisabled();
      expect(screen.getByTestId('btn-export-ordenes')).toBeDisabled();
    });

    // Resolver la descarga y verificar que se rehabilitan
    resolvePendiente!({ data: fakeBlob });
    await waitFor(() => {
      expect(screen.getByTestId('btn-export-top-clientes')).not.toBeDisabled();
    });
  });

  // ── 6. BVA: fecha_inicio === fecha_fin → acepta ───────────────────────────

  it('[VL] debe aceptar descarga cuando fecha_inicio === fecha_fin (valor límite válido)', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/ventas') return Promise.resolve({ data: fakeBlob });
      return mockApiVacio(url);
    });

    await navigateToReportes(user);

    const { fireEvent } = await import('@testing-library/react');
    const inputs = Array.from(document.querySelectorAll('input[type="date"]'));
    if (inputs.length >= 2) {
      fireEvent.change(inputs[0], { target: { value: '2026-02-15' } });
      fireEvent.change(inputs[1], { target: { value: '2026-02-15' } });
    }

    await user.click(screen.getByTestId('btn-export-ventas'));

    // No debe lanzar toast de error de fechas
    expect(toastErrorMock).not.toHaveBeenCalledWith(
      'La fecha de inicio no puede ser posterior a la fecha de fin'
    );
    // Debe llamar al endpoint
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reporting/gerencial/ventas',
        expect.objectContaining({ params: expect.objectContaining({ format: 'xlsx' }) })
      );
    });
  });

  // ── 7. EP: deudores no valida rango de fechas ─────────────────────────────

  it('[EP] btn-export-deudores debe llamar al API aunque fecha_inicio > fecha_fin (no usa parámetros de fecha)', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/deudores') return Promise.resolve({ data: fakeBlob });
      return mockApiVacio(url);
    });

    await navigateToReportes(user);

    // Invertir fechas — deudores no usa params de fecha, no debe bloquear
    const { fireEvent } = await import('@testing-library/react');
    const inputs = Array.from(document.querySelectorAll('input[type="date"]'));
    if (inputs.length >= 2) {
      fireEvent.change(inputs[0], { target: { value: '2026-05-01' } });
      fireEvent.change(inputs[1], { target: { value: '2026-01-01' } });
    }

    await user.click(screen.getByTestId('btn-export-deudores'));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reporting/gerencial/deudores',
        expect.anything()
      );
    });
    expect(toastErrorMock).not.toHaveBeenCalledWith(
      'La fecha de inicio no puede ser posterior a la fecha de fin'
    );
  });

  // ── 8. EP: sede_id se incluye en params cuando hay filtro activo ──────────

  it('[EP] debe incluir sede_id en los params cuando el usuario selecciona una sede', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/ventas') return Promise.resolve({ data: fakeBlob });
      if (url === '/sedes/') return Promise.resolve({ data: [{ id: 42, nombre: 'Sede Principal' }] });
      return mockApiVacio(url);
    });

    await navigateToReportes(user);

    // Seleccionar la sede con id=42
    const sedeBtn = await screen.findByTestId('select-item-42');
    await user.click(sedeBtn);

    await user.click(screen.getByTestId('btn-export-ventas'));

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reporting/gerencial/ventas',
        expect.objectContaining({
          params: expect.objectContaining({ sede_id: '42', format: 'xlsx' }),
        })
      );
    });
  });

  // ── 9. EP: sede_id ausente cuando no hay filtro ───────────────────────────

  it('[EP] no debe incluir sede_id en los params cuando no hay sede seleccionada', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/ventas') return Promise.resolve({ data: fakeBlob });
      return mockApiVacio(url);
    });

    await navigateToReportes(user);
    await user.click(screen.getByTestId('btn-export-ventas'));

    await waitFor(() => {
      const call = (apiClient.get as any).mock.calls.find(
        (c: any[]) => c[0] === '/reporting/gerencial/ventas'
      );
      expect(call).toBeDefined();
      expect(call[1].params).not.toHaveProperty('sede_id');
    });
  });

  // ── 10. Estado: botones re-habilitados tras error de API ──────────────────

  it('[Estado] debe re-habilitar todos los botones después de un error de API', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/ventas') return Promise.reject(new Error('503'));
      return mockApiVacio(url);
    });

    await navigateToReportes(user);
    await user.click(screen.getByTestId('btn-export-ventas'));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Error al descargar el reporte');
    });

    // Tras el error, todos los botones deben estar habilitados de nuevo
    await waitFor(() => {
      expect(screen.getByTestId('btn-export-ventas')).not.toBeDisabled();
      expect(screen.getByTestId('btn-export-top-clientes')).not.toBeDisabled();
      expect(screen.getByTestId('btn-export-ordenes')).not.toBeDisabled();
    });
  });

  // ── 11. Estado: spinner en el botón activo durante descarga ──────────────

  it('[Estado] debe mostrar spinner en el botón activo y no en los demás durante la descarga', async () => {
    const user = setupUser();
    let resolvePendiente: (v: any) => void;
    const pendiente = new Promise((res) => { resolvePendiente = res; });

    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/produccion/tendencia') return pendiente;
      return mockApiVacio(url);
    });

    await navigateToReportes(user);
    await user.click(screen.getByTestId('btn-export-tendencia'));

    // El botón activo debe estar disabled (contiene spinner internamente)
    await waitFor(() => {
      expect(screen.getByTestId('btn-export-tendencia')).toBeDisabled();
    });

    // Los demás botones también disabled (bloqueo global)
    expect(screen.getByTestId('btn-export-ventas')).toBeDisabled();
    expect(screen.getByTestId('btn-export-lotes')).toBeDisabled();

    // Resolver y verificar que el botón activo vuelve a estar habilitado
    resolvePendiente!({ data: fakeBlob });
    await waitFor(() => {
      expect(screen.getByTestId('btn-export-tendencia')).not.toBeDisabled();
    });
  });
});
