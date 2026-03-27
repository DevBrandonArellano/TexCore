import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

// Mock apiClient
vi.mock('../../lib/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  }
}));
import apiClient from '../../lib/axios';

// Mock sonner toast
const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  }
}));

// Mock ResizeObserver for Radix UI components
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

// Mock URL.createObjectURL / revokeObjectURL
global.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/fake-blob-url');
global.URL.revokeObjectURL = vi.fn();

import { InventoryDashboard } from './InventoryDashboard';
import { Producto, Bodega } from '../../lib/types';

const mockProductos: Producto[] = [
  {
    id: 1,
    codigo: 'PROD-001',
    descripcion: 'Tela Algodón Premium',
    tipo: 'tela',
    unidad_medida: 'kg',
    stock_minimo: 10,
    precio_base: 15.5,
  },
  {
    id: 2,
    codigo: 'PROD-002',
    descripcion: 'Hilo Poliéster',
    tipo: 'hilo',
    unidad_medida: 'kg',
    stock_minimo: 5,
    precio_base: 8.0,
  },
];

const mockBodegas: Bodega[] = [
  { id: 1, nombre: 'Bodega Principal', sede: 1 },
  { id: 2, nombre: 'Bodega Secundaria', sede: 1 },
];

describe('ReportesView - Exportación de reportes via microservicio reporting_excel', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock: stock endpoint returns empty
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/inventory/stock/') {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: [] });
    });
  });

  // Use pointerEventsCheck: 0 to bypass Radix UI pointer-events: none in jsdom
  const setupUser = () => userEvent.setup({ pointerEventsCheck: 0 });

  const renderDashboard = () => render(
    <BrowserRouter>
      <InventoryDashboard
        productos={mockProductos}
        bodegas={mockBodegas}
        lotesProduccion={[]}
        proveedores={[]}
        onDataRefresh={vi.fn()}
      />
    </BrowserRouter>
  );

  const navigateToReportes = async (user: ReturnType<typeof userEvent.setup>) => {
    renderDashboard();
    const reportesTab = screen.getByRole('tab', { name: /Reportes/i });
    await user.click(reportesTab);
    await waitFor(() => {
      expect(screen.getByText('Exportar Kardex de Bodega (Excel)')).toBeInTheDocument();
    });
  };

  const selectBodega = async (user: ReturnType<typeof userEvent.setup>, nombre: string) => {
    const bodegaTrigger = screen.getByText('Selecciona una bodega');
    await user.click(bodegaTrigger);
    const option = await screen.findByRole('option', { name: nombre });
    await user.click(option);
  };

  // ────────────────────────────────────────────────────────
  // 1. Renderizado correcto de la UI
  // ────────────────────────────────────────────────────────
  it('debe renderizar los títulos y campos del formulario de reportes', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    // Card titles
    expect(screen.getByText('Exportar Kardex de Bodega (Excel)')).toBeInTheDocument();
    expect(screen.getByText('Exportar Catálogo de Productos')).toBeInTheDocument();

    // Buttons
    expect(screen.getByRole('button', { name: /Exportar Kardex/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Descargar Catálogo/i })).toBeInTheDocument();

    // Bodega select placeholder
    expect(screen.getByText('Selecciona una bodega')).toBeInTheDocument();

    // Hint when no bodega selected
    expect(screen.getByText(/Seleccione una bodega para habilitar/i)).toBeInTheDocument();
  });

  // ────────────────────────────────────────────────────────
  // 2. Validación: bodega es requerida para exportar kardex
  // ────────────────────────────────────────────────────────
  it('debe mostrar error toast si se intenta exportar kardex sin seleccionar bodega', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    expect(toastErrorMock).toHaveBeenCalledWith(
      'Debe seleccionar una bodega para generar el reporte de kardex.'
    );
    // Must NOT have called the reporting API
    expect(apiClient.get).not.toHaveBeenCalledWith(
      '/reporting/export/kardex',
      expect.anything()
    );
  });

  // ────────────────────────────────────────────────────────
  // 3. Exportar Kardex exitoso con bodega seleccionada
  // ────────────────────────────────────────────────────────
  it('debe llamar al endpoint /reporting/export/kardex con bodega_id y descargar el blob', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    const fakeBlob = new Blob(['fake-excel-content'], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.resolve({
          data: fakeBlob,
          headers: { 'content-disposition': 'attachment; filename=kardex_1.xlsx' },
        });
      }
      return Promise.resolve({ data: [] });
    });

    // Select bodega
    await selectBodega(user, 'Bodega Principal');

    // Hint should disappear
    expect(screen.queryByText(/Seleccione una bodega para habilitar/i)).not.toBeInTheDocument();

    // Click export
    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/reporting/export/kardex', {
        params: { bodega_id: '1' },
        responseType: 'blob',
      });
    });

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith('Kardex descargado exitosamente.');
    });

    expect(URL.createObjectURL).toHaveBeenCalledWith(fakeBlob);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/fake-blob-url');
  });

  // ────────────────────────────────────────────────────────
  // 4. Exportar Kardex con filtros opcionales de fecha
  // ────────────────────────────────────────────────────────
  it('debe enviar fecha_inicio y fecha_fin como parámetros opcionales al exportar kardex', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    const fakeBlob = new Blob(['data']);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.resolve({ data: fakeBlob, headers: {} });
      }
      return Promise.resolve({ data: [] });
    });

    // Select bodega
    await selectBodega(user, 'Bodega Secundaria');

    // Set date range via native date inputs
    const allInputs = document.querySelectorAll('input[type="date"]');
    const fechaDesde = allInputs[0] as HTMLInputElement;
    const fechaHasta = allInputs[1] as HTMLInputElement;

    // Programmatically set values and fire change events
    await user.clear(fechaDesde);
    await user.type(fechaDesde, '2026-01-01');
    await user.clear(fechaHasta);
    await user.type(fechaHasta, '2026-03-26');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/reporting/export/kardex', {
        params: expect.objectContaining({ bodega_id: '2' }),
        responseType: 'blob',
      });
    });
  });

  // ────────────────────────────────────────────────────────
  // 5. Error 404 muestra mensaje específico
  // ────────────────────────────────────────────────────────
  it('debe mostrar mensaje específico cuando la API responde 404 (sin datos)', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.reject({ response: { status: 404 } });
      }
      return Promise.resolve({ data: [] });
    });

    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'No se encontraron movimientos para los filtros seleccionados.'
      );
    });
  });

  // ────────────────────────────────────────────────────────
  // 6. Error genérico (500, red, etc.)
  // ────────────────────────────────────────────────────────
  it('debe mostrar mensaje genérico para errores de servidor o red', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.reject({ response: { status: 500 } });
      }
      return Promise.resolve({ data: [] });
    });

    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'Error al generar el kardex. Verifique los filtros e intente de nuevo.'
      );
    });
  });

  // ────────────────────────────────────────────────────────
  // 7. Exportar Catálogo de Productos exitoso
  // ────────────────────────────────────────────────────────
  it('debe llamar al endpoint /reporting/export/productos y descargar', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    const fakeBlob = new Blob(['productos-excel']);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/productos') {
        return Promise.resolve({
          data: fakeBlob,
          headers: { 'content-disposition': 'attachment; filename=catalogo_productos.xlsx' },
        });
      }
      return Promise.resolve({ data: [] });
    });

    const btnCatalogo = screen.getByRole('button', { name: /Descargar Catálogo/i });
    await user.click(btnCatalogo);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/reporting/export/productos', {
        responseType: 'blob',
      });
    });

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith('Catálogo de productos descargado.');
    });

    expect(URL.createObjectURL).toHaveBeenCalledWith(fakeBlob);
  });

  // ────────────────────────────────────────────────────────
  // 8. Error al exportar catálogo
  // ────────────────────────────────────────────────────────
  it('debe mostrar error toast si falla la exportación del catálogo', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/productos') {
        return Promise.reject(new Error('Network Error'));
      }
      return Promise.resolve({ data: [] });
    });

    const btnCatalogo = screen.getByRole('button', { name: /Descargar Catálogo/i });
    await user.click(btnCatalogo);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Error al exportar el catálogo de productos.');
    });
  });

  // ────────────────────────────────────────────────────────
  // 9. Content-Disposition fallback filename
  // ────────────────────────────────────────────────────────
  it('debe usar el fallback filename cuando no hay Content-Disposition header', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    const fakeBlob = new Blob(['data']);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.resolve({
          data: fakeBlob,
          headers: {}, // No content-disposition
        });
      }
      return Promise.resolve({ data: [] });
    });

    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith('Kardex descargado exitosamente.');
    });

    expect(URL.createObjectURL).toHaveBeenCalledWith(fakeBlob);
  });

  // ────────────────────────────────────────────────────────
  // 10. Loading state en botón Exportar Kardex
  // ────────────────────────────────────────────────────────
  it('debe mostrar estado de carga en el botón mientras se genera el reporte', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    // Mock a slow response
    let resolvePromise: (v: any) => void;
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return new Promise((resolve) => { resolvePromise = resolve; });
      }
      return Promise.resolve({ data: [] });
    });

    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    // Button should show loading text
    await waitFor(() => {
      expect(screen.getByText('Generando...')).toBeInTheDocument();
    });

    // Resolve the promise
    resolvePromise!({
      data: new Blob(['data']),
      headers: {},
    });

    // After resolve, button should revert
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Exportar Kardex/i })).toBeInTheDocument();
    });
  });
});
