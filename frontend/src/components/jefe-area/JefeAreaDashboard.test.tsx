import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { JefeAreaDashboard } from './JefeAreaDashboard';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock axios / apiClient — JefeAreaDashboard usa apiClient directamente
// y ManageMaquinas usa useQuery (TanStack Query) sobre apiClient
vi.mock('axios', () => {
  const kpiDefault = { total_produccion_kg: 0, rendimiento_yield: 0, tiempo_promedio_lote_min: 0, area: '' };
  const mockGet = vi.fn((url: string) => {
    if (url.startsWith('/kpi-area')) return Promise.resolve({ data: kpiDefault });
    return Promise.resolve({ data: [] });
  });
  const mockAxiosInstance = {
    get: mockGet,
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  };
  return {
    default: { ...mockAxiosInstance, create: vi.fn(() => mockAxiosInstance) },
  };
});

// Mock Auth
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: { user: { id: 1, role: 'jefe_area', area: 1 } } }),
}));

// Polyfills para Radix UI en jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

// ── Helper: crea un QueryClient nuevo por test para aislar cache ──────────────

const makeQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

const renderComponent = () => {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <JefeAreaDashboard />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('JefeAreaDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('se renderiza sin crashear', async () => {
    expect(() => renderComponent()).not.toThrow();
  });

  it('el card de Estado de Máquinas no tiene un botón propio de "Nueva Máquina" duplicado', async () => {
    renderComponent();

    // Esperar a que el componente termine de montar
    await waitFor(() => {
      expect(screen.getByText('Estado de Máquinas y Carga')).toBeInTheDocument();
    });

    // Debe existir exactamente UN botón "+ Nueva Máquina" (el de ManageMaquinas).
    // Antes del fix había DOS: uno en el CardHeader del dashboard y otro dentro de ManageMaquinas.
    const botonesNuevaMaquina = screen.getAllByRole('button', { name: /Nueva Máquina/i });
    expect(botonesNuevaMaquina).toHaveLength(1);
  });
});
