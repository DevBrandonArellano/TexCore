import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VendedorDashboard } from './VendedorDashboard';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

vi.mock('../../lib/axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: [] })),
    patch: vi.fn(() => Promise.resolve({ data: [] })),
    delete: vi.fn(() => Promise.resolve({ data: [] })),
    put: vi.fn(() => Promise.resolve({ data: [] })),
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: [] })),
      post: vi.fn(() => Promise.resolve({ data: [] })),
      patch: vi.fn(() => Promise.resolve({ data: [] })),
      delete: vi.fn(() => Promise.resolve({ data: [] })),
      put: vi.fn(() => Promise.resolve({ data: [] }))
    }))
  },
}));
import apiClient from '../../lib/axios';

// Perfil sin usuario identificado: simula sesión corrupta / profile aún no cargado.
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: { user: { id: undefined } } }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));
import { toast } from 'sonner';

global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

const renderComponent = () =>
  render(
    <BrowserRouter>
      <VendedorDashboard />
    </BrowserRouter>
  );

describe('VendedorDashboard — Exportación de ventas sin vendedor identificado', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    (apiClient.get as any).mockImplementation(() => Promise.resolve({ data: [] }));
  });

  it('dado que el perfil no tiene un id de vendedor cuando se intenta exportar el reporte de ventas entonces muestra un toast pidiendo reiniciar sesión', async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => expect(screen.getByText('Directorio de Clientes')).toBeInTheDocument());
    const tabs = screen.getAllByRole('tab');
    const reportesTab = tabs.find((t) => t.textContent?.includes('Reportes Excel'));
    await user.click(reportesTab!);
    await waitFor(() => expect(screen.getByText('Reportes Comerciales Avanzados')).toBeInTheDocument());

    const botones = screen.getAllByRole('button', { name: /Bajar Excel/i });
    await user.click(botones[0]);

    expect(toast.error).toHaveBeenCalledWith('No se pudo identificar al vendedor. Cierra sesión e inicia de nuevo.');
    expect(apiClient.get).not.toHaveBeenCalledWith(expect.stringContaining('/reporting/'), expect.anything());
  });
});
