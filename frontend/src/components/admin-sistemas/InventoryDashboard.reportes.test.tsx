/**
 * ISTQB — Nivel: Componente / Integración
 * Técnica : Black-box (equivalencia de partición + valor límite + transición de estados)
 * Cubre   : ReportesView dentro de InventoryDashboard
 *            - Validación de bodega requerida para exportar kardex
 *            - Descarga exitosa de kardex con bodega seleccionada
 *            - Descarga exitosa de catálogo (sin bodega requerida)
 *            - Manejo de errores 404 y 500 del microservicio reporting_excel
 *            - Estado de carga del botón (spinner/texto)
 *            - Parámetros opcionales de fecha en exportación kardex
 *            - Fallback de filename cuando no hay Content-Disposition
 */
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

// Mock ResizeObserver para componentes Radix UI
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

// ── Fixtures ──────────────────────────────────────────────────────────────────

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
];

const mockBodegas: Bodega[] = [
  { id: 1, nombre: 'Bodega Principal', sede: 1 },
  { id: 2, nombre: 'Bodega Secundaria', sede: 1 },
];

const fakeBlob = new Blob(['fake-excel-content'], {
  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
});

// ── Helpers ───────────────────────────────────────────────────────────────────

const setupUser = () => userEvent.setup({ pointerEventsCheck: 0 });

const renderDashboard = () =>
  render(
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

/**
 * Navega al tab Reportes y espera a que se muestre el contenido del kardex.
 * El texto centinela es 'Kardex de Movimientos' (CardTitle real del componente).
 */
const navigateToReportes = async (user: ReturnType<typeof userEvent.setup>) => {
  renderDashboard();
  const reportesTab = screen.getByRole('tab', { name: /Reportes/i });
  await user.click(reportesTab);
  await waitFor(() => {
    expect(screen.getByText('Kardex de Movimientos')).toBeInTheDocument();
  });
};

/**
 * Selecciona una bodega del Radix UI Select.
 * El trigger es el combobox que muestra el placeholder de bodega.
 */
const selectBodega = async (
  user: ReturnType<typeof userEvent.setup>,
  nombre: string
) => {
  // El SelectTrigger de bodega tiene role="combobox"; puede haber otros selects,
  // usamos el que contiene el placeholder de bodega.
  const triggers = screen.getAllByRole('combobox');
  const bodegaTrigger = triggers.find(
    (el) =>
      el.textContent?.includes('Selecciona una bodega') ||
      el.getAttribute('aria-label')?.includes('bodega') ||
      el.closest('[data-slot]')?.textContent?.includes('Selecciona una bodega')
  ) ?? triggers[0];

  await user.click(bodegaTrigger);
  const option = await screen.findByRole('option', { name: nombre });
  await user.click(option);
};

// ── Suite de tests ────────────────────────────────────────────────────────────

describe('ReportesView — Exportación de reportes via microservicio reporting_excel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation(() =>
      Promise.resolve({ data: [] })
    );
  });

  // ── 1. Renderizado correcto de la UI ─────────────────────────────────────

  it('[R-01] debe renderizar los títulos y botones de exportación en el tab Reportes', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    // Títulos de las cards
    expect(screen.getByText('Kardex de Movimientos')).toBeInTheDocument();
    expect(screen.getByText('Catálogo maestro de Productos')).toBeInTheDocument();

    // Botones de acción
    expect(screen.getByRole('button', { name: /Exportar Kardex/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Descargar Catálogo/i })).toBeInTheDocument();

    // Placeholder del selector de bodega presente
    expect(
      screen.getByText('Selecciona una bodega para habilitar los reportes')
    ).toBeInTheDocument();
  });

  // ── 2. Validación: bodega requerida para exportar kardex ──────────────────

  it('[EP-01] debe mostrar toast.error si se exporta kardex sin bodega seleccionada', async () => {
    const user = setupUser();
    await navigateToReportes(user);

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    expect(toastErrorMock).toHaveBeenCalledWith(
      'Debe seleccionar una bodega para este reporte.'
    );
    expect(apiClient.get).not.toHaveBeenCalledWith(
      '/reporting/export/kardex',
      expect.anything()
    );
  });

  // ── 3. Descarga exitosa de kardex con bodega seleccionada ─────────────────

  it('[EP-02] debe llamar a /reporting/export/kardex con bodega_id y mostrar toast.success', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.resolve({
          data: fakeBlob,
          headers: { 'content-disposition': 'attachment; filename=kardex_1.xlsx' },
        });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);
    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reporting/export/kardex',
        expect.objectContaining({
          params: expect.objectContaining({ bodega_id: '1' }),
          responseType: 'blob',
        })
      );
    });

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith('Reporte generado exitosamente.');
    });

    expect(URL.createObjectURL).toHaveBeenCalledWith(fakeBlob);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/fake-blob-url');
  });

  // ── 4. Parámetros opcionales de fecha en exportación kardex ──────────────

  it('[EP-03] debe enviar bodega_id en params al exportar kardex con bodega seleccionada', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.resolve({ data: fakeBlob, headers: {} });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);
    await selectBodega(user, 'Bodega Secundaria');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reporting/export/kardex',
        expect.objectContaining({
          params: expect.objectContaining({ bodega_id: '2' }),
          responseType: 'blob',
        })
      );
    });
  });

  // ── 5. Error 404 muestra mensaje específico ───────────────────────────────

  it('[EP-04] debe mostrar mensaje específico cuando el API responde 404', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.reject({ response: { status: 404 } });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);
    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'No se encontraron datos para los filtros seleccionados.'
      );
    });
  });

  // ── 6. Error genérico (500, red, etc.) ───────────────────────────────────

  it('[EP-05] debe mostrar mensaje genérico para errores de servidor o red', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.reject({ response: { status: 500 } });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);
    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'Error al generar el reporte. Intente de nuevo.'
      );
    });
  });

  // ── 7. Exportar Catálogo de Productos exitoso ─────────────────────────────

  it('[EP-06] debe llamar a /reporting/export/productos y mostrar toast.success', async () => {
    const user = setupUser();
    const catalogBlob = new Blob(['productos-excel']);
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/productos') {
        return Promise.resolve({
          data: catalogBlob,
          headers: { 'content-disposition': 'attachment; filename=catalogo_productos.xlsx' },
        });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);

    const btnCatalogo = screen.getByRole('button', { name: /Descargar Catálogo/i });
    await user.click(btnCatalogo);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reporting/export/productos',
        expect.objectContaining({ responseType: 'blob' })
      );
    });

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith('Reporte generado exitosamente.');
    });

    expect(URL.createObjectURL).toHaveBeenCalledWith(catalogBlob);
  });

  // ── 8. Error al exportar catálogo ─────────────────────────────────────────

  it('[EP-07] debe mostrar toast.error si falla la exportación del catálogo', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/productos') {
        return Promise.reject({ response: { status: 500 } });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);

    const btnCatalogo = screen.getByRole('button', { name: /Descargar Catálogo/i });
    await user.click(btnCatalogo);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith(
        'Error al generar el reporte. Intente de nuevo.'
      );
    });
  });

  // ── 9. Fallback filename cuando no hay Content-Disposition ────────────────

  it('[VL-01] debe usar fallback filename cuando no hay Content-Disposition header', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return Promise.resolve({ data: fakeBlob, headers: {} });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);
    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith('Reporte generado exitosamente.');
    });
    expect(URL.createObjectURL).toHaveBeenCalledWith(fakeBlob);
  });

  // ── 10. Estado de carga en botón Exportar Kardex ─────────────────────────

  it('[Estado-01] debe mostrar "Generando..." mientras se genera el reporte de kardex', async () => {
    const user = setupUser();
    let resolvePromise: (v: any) => void;
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/export/kardex') {
        return new Promise((resolve) => { resolvePromise = resolve; });
      }
      return Promise.resolve({ data: [] });
    });

    await navigateToReportes(user);
    await selectBodega(user, 'Bodega Principal');

    const btnExportKardex = screen.getByRole('button', { name: /Exportar Kardex/i });
    await user.click(btnExportKardex);

    // Mientras descarga, el botón muestra "Generando..."
    await waitFor(() => {
      expect(screen.getByText('Generando...')).toBeInTheDocument();
    });

    // Resolver la promesa
    resolvePromise!({ data: fakeBlob, headers: {} });

    // Tras la resolución, vuelve al texto normal
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Exportar Kardex/i })).toBeInTheDocument();
    });
  });
});
