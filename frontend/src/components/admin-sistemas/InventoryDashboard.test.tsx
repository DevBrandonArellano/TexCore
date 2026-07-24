/**
 * ISTQB — Nivel: Componente / Integración
 * Técnica : Black-box (equivalencia de partición + valor límite + transición de estados)
 * Cubre   : InventoryDashboard — todo lo que NO cubre InventoryDashboard.reportes.test.tsx
 *            - Navegación entre las 6 pestañas
 *            - StockView: carga, vacío, poblado, búsqueda, paginación, error de fetch
 *            - RegistrarEntradaView: validación, envío exitoso, error de servidor, estado de envío
 *            - TransferView: validación de campos, validación de stock, envío exitoso
 *            - KardexView: consulta con filtros, limpiar filtros, exportación CSV, diálogos de edición/auditoría
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn(() => Promise.resolve({ data: [] }));

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    put: (...args: any[]) => mockPut(...args),
    patch: vi.fn(() => Promise.resolve({ data: [] })),
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

global.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/fake-blob-url');
global.URL.revokeObjectURL = vi.fn();

import { InventoryDashboard } from './InventoryDashboard';
import type { Producto, Bodega, Proveedor } from '../../lib/types';

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
    precio_base: 8.2,
  },
];

const mockBodegas: Bodega[] = [
  { id: 1, nombre: 'Bodega Principal', sede: 1 },
  { id: 2, nombre: 'Bodega Secundaria', sede: 1 },
];

const mockProveedores: Proveedor[] = [
  { id: 1, nombre: 'Proveedor Textil SA' },
];

function mockApi({
  stock = [] as any[],
  movimientos = [] as any[],
  stockError = false,
}: { stock?: any[]; movimientos?: any[]; stockError?: boolean } = {}) {
  mockGet.mockImplementation((url: string) => {
    if (url === '/inventory/stock/') {
      if (stockError) return Promise.reject(new Error('network error'));
      return Promise.resolve({ data: stock });
    }
    if (url === '/inventory/movimientos/') {
      return Promise.resolve({ data: movimientos });
    }
    if (url.includes('/auditoria/')) {
      return Promise.resolve({ data: [] });
    }
    return Promise.resolve({ data: [] });
  });
}

const setupUser = () => userEvent.setup({ pointerEventsCheck: 0 });

const renderDashboard = (props: Partial<React.ComponentProps<typeof InventoryDashboard>> = {}) =>
  render(
    <BrowserRouter>
      <InventoryDashboard
        productos={mockProductos}
        bodegas={mockBodegas}
        lotesProduccion={[]}
        proveedores={mockProveedores}
        onDataRefresh={vi.fn()}
        {...props}
      />
    </BrowserRouter>
  );

const selectComboboxOption = async (
  user: ReturnType<typeof userEvent.setup>,
  placeholderText: string,
  optionName: string | RegExp
) => {
  const triggers = screen.getAllByRole('combobox');
  const trigger = triggers.find((el) => el.textContent?.includes(placeholderText));
  if (!trigger) throw new Error(`No combobox found with placeholder "${placeholderText}"`);
  await user.click(trigger);
  const option = await screen.findByRole('option', { name: optionName });
  await user.click(option);
};

describe('InventoryDashboard', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
    mockGet.mockReset();
    mockPost.mockReset();
    mockPut.mockReset();
    mockDelete.mockReset();
    mockDelete.mockResolvedValue({ data: [] });
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    mockApi();
  });

  // ── Navegación entre pestañas ──────────────────────────────────────────────

  describe('Navegación de pestañas', () => {
    it('dado el dashboard cuando se monta entonces muestra las 6 pestañas y el tab Stock activo por defecto', async () => {
      renderDashboard();

      expect(screen.getByRole('tab', { name: /Stock/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Entrada/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Transfer/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Transform/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Kardex/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Reportes/i })).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('Stock Actual')).toBeInTheDocument();
      });
    });

    it('dado clic en la pestaña Entrada cuando se navega entonces muestra el formulario de registro de entrada', async () => {
      const user = setupUser();
      renderDashboard();

      await user.click(screen.getByRole('tab', { name: /Entrada/i }));
      expect(await screen.findByText('Registrar Entrada de Materia Prima')).toBeInTheDocument();
    });

    it('dado clic en la pestaña Transfer cuando se navega entonces muestra el formulario de transferencia', async () => {
      const user = setupUser();
      renderDashboard();

      await user.click(screen.getByRole('tab', { name: /Transfer/i }));
      expect(await screen.findByText('Transferencia de Stock')).toBeInTheDocument();
    });

    it('dado clic en la pestaña Transform cuando se navega entonces muestra la vista de transformación', async () => {
      const user = setupUser();
      renderDashboard();

      await user.click(screen.getByRole('tab', { name: /Transform/i }));
      expect(await screen.findByText('Transformación de Producto')).toBeInTheDocument();
    });

    it('dado clic en la pestaña Kardex cuando se navega entonces muestra el kardex profesional', async () => {
      const user = setupUser();
      renderDashboard();

      await user.click(screen.getByRole('tab', { name: /Kardex/i }));
      expect(await screen.findByText('Kardex de Inventario Profesional')).toBeInTheDocument();
    });
  });

  // ── StockView ───────────────────────────────────────────────────────────────

  describe('StockView', () => {
    it('dado stock aun no resuelto cuando monta entonces muestra el estado de carga con skeletons', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const { container } = renderDashboard();

      expect(container.querySelectorAll('[data-slot="skeleton"], .animate-pulse').length).toBeGreaterThan(0);
    });

    it('dado stock vacio cuando carga entonces muestra el mensaje de que no hay stock', async () => {
      mockApi({ stock: [] });
      renderDashboard();

      expect(await screen.findByText('No hay stock para mostrar.')).toBeInTheDocument();
    });

    it('dado stock con items cuando carga entonces renderiza filas con producto, bodega, lote y cantidad', async () => {
      mockApi({
        stock: [
          { id: 1, producto: 'Tela Algodón Premium', producto_id: 1, bodega: 'Bodega Principal', bodega_id: 1, lote: 'LOTE-001', lote_id: 5, lote_codigo: 'LOTE-001', cantidad: '120.50' },
        ],
      });
      renderDashboard();

      expect(await screen.findByText('Tela Algodón Premium')).toBeInTheDocument();
      expect(screen.getByText('Bodega Principal')).toBeInTheDocument();
      expect(screen.getByText('LOTE-001')).toBeInTheDocument();
      expect(screen.getByText('120.50')).toBeInTheDocument();
    });

    it('dado item de stock sin lote cuando carga entonces muestra guion en la columna Lote', async () => {
      mockApi({
        stock: [
          { id: 2, producto: 'Hilo Poliéster', producto_id: 2, bodega: 'Bodega Secundaria', bodega_id: 2, lote: null, lote_id: null, lote_codigo: null, cantidad: '30.00' },
        ],
      });
      renderDashboard();

      await screen.findByText('Hilo Poliéster');
      const row = screen.getByText('Hilo Poliéster').closest('tr')!;
      expect(within(row).getByText('-')).toBeInTheDocument();
    });

    it('dado error en el fetch de stock cuando falla entonces muestra toast de error y tabla vacia', async () => {
      mockApi({ stockError: true });
      renderDashboard();

      await waitFor(() => {
        expect(toastErrorMock).toHaveBeenCalledWith('Error stock');
      });
      expect(await screen.findByText('No hay stock para mostrar.')).toBeInTheDocument();
    });

    it('dado un termino de busqueda cuando se escribe entonces filtra el stock por producto, bodega o lote', async () => {
      const user = setupUser();
      mockApi({
        stock: [
          { id: 1, producto: 'Tela Algodón Premium', producto_id: 1, bodega: 'Bodega Principal', bodega_id: 1, lote: null, lote_id: null, lote_codigo: null, cantidad: '10.00' },
          { id: 2, producto: 'Hilo Poliéster', producto_id: 2, bodega: 'Bodega Secundaria', bodega_id: 2, lote: null, lote_id: null, lote_codigo: null, cantidad: '20.00' },
        ],
      });
      renderDashboard();

      await screen.findByText('Tela Algodón Premium');
      const searchInput = screen.getByPlaceholderText('Buscar por producto, bodega o lote...');
      await user.type(searchInput, 'Hilo');

      await waitFor(() => {
        expect(screen.queryByText('Tela Algodón Premium')).not.toBeInTheDocument();
      });
      expect(screen.getByText('Hilo Poliéster')).toBeInTheDocument();
    });

    it('dado mas de 20 items cuando carga entonces pagina los resultados y habilita Siguiente', async () => {
      const user = setupUser();
      const manyItems = Array.from({ length: 25 }).map((_, i) => ({
        id: i + 1,
        producto: `Producto ${i + 1}`,
        producto_id: 1,
        bodega: 'Bodega Principal',
        bodega_id: 1,
        lote: null,
        lote_id: null,
        lote_codigo: null,
        cantidad: '5.00',
      }));
      mockApi({ stock: manyItems });
      renderDashboard();

      await screen.findByText('Producto 1');
      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
      expect(screen.queryByText('Producto 21')).not.toBeInTheDocument();

      const siguienteBtn = screen.getByRole('button', { name: /Siguiente/i });
      expect(siguienteBtn).not.toBeDisabled();
      await user.click(siguienteBtn);

      await waitFor(() => {
        expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
      });
      expect(screen.getByText('Producto 21')).toBeInTheDocument();
      expect(siguienteBtn).toBeDisabled();
    });

    it('dado sedeId provisto cuando monta entonces solicita el stock filtrado por esa sede', async () => {
      mockApi({ stock: [] });
      renderDashboard({ sedeId: '7' });

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith(
          '/inventory/stock/',
          expect.objectContaining({ params: { sede_id: '7' } })
        );
      });
    });
  });

  // ── RegistrarEntradaView ─────────────────────────────────────────────────────

  describe('RegistrarEntradaView (tab Entrada)', () => {
    const goToEntrada = async (user: ReturnType<typeof userEvent.setup>) => {
      renderDashboard();
      await user.click(screen.getByRole('tab', { name: /Entrada/i }));
      await screen.findByText('Registrar Entrada de Materia Prima');
    };

    it('dado el formulario de entrada cuando se renderiza entonces muestra los campos principales', async () => {
      const user = setupUser();
      await goToEntrada(user);

      expect(screen.getByText('Producto')).toBeInTheDocument();
      expect(screen.getByLabelText('Bodega de Destino')).toBeInTheDocument();
      expect(screen.getByLabelText('Cantidad')).toBeInTheDocument();
      expect(screen.getByText(/Justificación de la Entrada/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Registrar Entrada' })).toBeInTheDocument();
    });

    it('dado campos requeridos vacios cuando se envia entonces muestra error y no llama al API', async () => {
      const user = setupUser();
      await goToEntrada(user);

      await user.click(screen.getByRole('button', { name: 'Registrar Entrada' }));

      await waitFor(() => {
        expect(toastErrorMock).toHaveBeenCalledWith('Producto, Bodega, Cantidad y Justificación son requeridos.');
      });
      expect(mockPost).not.toHaveBeenCalled();
    });

    it('dado datos validos cuando se envia entonces registra la entrada con el payload correcto y refresca el stock', async () => {
      const user = setupUser();
      mockPost.mockResolvedValue({ data: {} });
      await goToEntrada(user);

      await selectComboboxOption(user, 'Selecciona un producto', 'Tela Algodón Premium');
      await selectComboboxOption(user, 'Selecciona una bodega', 'Bodega Principal');
      await user.type(screen.getByPlaceholderText('0.00'), '15.5');
      await user.type(screen.getByPlaceholderText('Ej: Reposición mensual...'), 'Reposición mensual de stock');

      const initialGetCalls = mockGet.mock.calls.length;
      await user.click(screen.getByRole('button', { name: 'Registrar Entrada' }));

      await waitFor(() => {
        expect(mockPost).toHaveBeenCalledWith('/inventory/movimientos/', expect.objectContaining({
          tipo_movimiento: 'COMPRA',
          producto: 1,
          bodega_destino: 1,
          cantidad: 15.5,
          _justificacion_auditoria: 'Reposición mensual de stock',
        }));
      });

      await waitFor(() => {
        expect(toastSuccessMock).toHaveBeenCalledWith('Entrada de materia prima registrada con éxito.');
      });

      await waitFor(() => {
        expect(mockGet.mock.calls.length).toBeGreaterThan(initialGetCalls);
      });
    });

    it('dado error del servidor cuando se envia entonces muestra el mensaje de error retornado', async () => {
      const user = setupUser();
      mockPost.mockRejectedValue({ response: { data: { error: 'La bodega no pertenece a la sede.' } } });
      await goToEntrada(user);

      await selectComboboxOption(user, 'Selecciona un producto', 'Tela Algodón Premium');
      await selectComboboxOption(user, 'Selecciona una bodega', 'Bodega Principal');
      await user.type(screen.getByPlaceholderText('0.00'), '10');
      await user.type(screen.getByPlaceholderText('Ej: Reposición mensual...'), 'Justificación de prueba');

      await user.click(screen.getByRole('button', { name: 'Registrar Entrada' }));

      await waitFor(() => {
        expect(toastErrorMock).toHaveBeenCalledWith('Error', { description: 'La bodega no pertenece a la sede.' });
      });
    });

    it('dado un envio en curso cuando se hace clic entonces el boton muestra "Registrando..." y se deshabilita', async () => {
      const user = setupUser();
      let resolvePost: (v: any) => void;
      mockPost.mockImplementation(() => new Promise((resolve) => { resolvePost = resolve; }));
      await goToEntrada(user);

      await selectComboboxOption(user, 'Selecciona un producto', 'Tela Algodón Premium');
      await selectComboboxOption(user, 'Selecciona una bodega', 'Bodega Principal');
      await user.type(screen.getByPlaceholderText('0.00'), '10');
      await user.type(screen.getByPlaceholderText('Ej: Reposición mensual...'), 'Justificación de prueba');

      await user.click(screen.getByRole('button', { name: 'Registrar Entrada' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Registrando...' })).toBeDisabled();
      });

      resolvePost!({ data: {} });
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Registrar Entrada' })).not.toBeDisabled();
      });
    });
  });

  // ── TransferView ─────────────────────────────────────────────────────────────

  describe('TransferView (tab Transfer)', () => {
    const goToTransfer = async (user: ReturnType<typeof userEvent.setup>, stock: any[] = []) => {
      mockApi({ stock });
      renderDashboard();
      await user.click(screen.getByRole('tab', { name: /Transfer/i }));
      await screen.findByText('Transferencia de Stock');
    };

    it('dado el formulario vacio cuando se envia entonces muestra los errores de validacion de cada campo', async () => {
      const user = setupUser();
      await goToTransfer(user);

      await user.click(screen.getByRole('button', { name: 'Transferir' }));

      expect(await screen.findByText('Producto es requerido.')).toBeInTheDocument();
      expect(screen.getByText('Bodega origen requerida.')).toBeInTheDocument();
      expect(screen.getByText('Bodega destino requerida.')).toBeInTheDocument();
      expect(screen.getByText('Cantidad inválida.')).toBeInTheDocument();
      expect(screen.getByText('Justificación requerida.')).toBeInTheDocument();
      expect(mockPost).not.toHaveBeenCalled();
    });

    it('dado stock suficiente cuando se completa y envia el formulario entonces transfiere con exito', async () => {
      const user = setupUser();
      mockPost.mockResolvedValue({ data: {} });
      await goToTransfer(user, [
        { id: 1, producto: 'Tela Algodón Premium', producto_id: 1, bodega: 'Bodega Principal', bodega_id: 1, lote: null, lote_id: null, lote_codigo: null, cantidad: '50.00' },
      ]);

      await selectComboboxOption(user, 'Selecciona un producto', 'Tela Algodón Premium');
      await selectComboboxOption(user, 'Origen', 'Bodega Principal');
      await selectComboboxOption(user, 'Destino', 'Bodega Secundaria');
      await user.type(screen.getByRole('spinbutton'), '30');
      await user.type(screen.getByPlaceholderText('Motivo del traslado...'), 'Reorganización de bodegas');

      await user.click(screen.getByRole('button', { name: 'Transferir' }));

      await waitFor(() => {
        expect(mockPost).toHaveBeenCalledWith('/inventory/transferencias/', expect.objectContaining({
          producto_id: 1,
          bodega_origen_id: 1,
          bodega_destino_id: 2,
          cantidad: 30,
          lote_id: null,
          _justificacion_auditoria: 'Reorganización de bodegas',
        }));
      });

      await waitFor(() => {
        expect(toastSuccessMock).toHaveBeenCalledWith('Transferencia exitosa');
      });
    });

    it('dado cantidad mayor al stock disponible cuando se envia entonces muestra error de stock insuficiente', async () => {
      const user = setupUser();
      await goToTransfer(user, [
        { id: 1, producto: 'Tela Algodón Premium', producto_id: 1, bodega: 'Bodega Principal', bodega_id: 1, lote: null, lote_id: null, lote_codigo: null, cantidad: '50.00' },
      ]);

      await selectComboboxOption(user, 'Selecciona un producto', 'Tela Algodón Premium');
      await selectComboboxOption(user, 'Origen', 'Bodega Principal');
      await selectComboboxOption(user, 'Destino', 'Bodega Secundaria');
      await user.type(screen.getByRole('spinbutton'), '100');
      await user.type(screen.getByPlaceholderText('Motivo del traslado...'), 'Traslado de prueba');

      await user.click(screen.getByRole('button', { name: 'Transferir' }));

      expect(await screen.findByText('Stock insuficiente. Disponible: 50.00')).toBeInTheDocument();
      expect(mockPost).not.toHaveBeenCalled();
    });
  });

  // ── KardexView ───────────────────────────────────────────────────────────────

  describe('KardexView (tab Kardex)', () => {
    const goToKardex = async (user: ReturnType<typeof userEvent.setup>, movimientos: any[] = []) => {
      mockApi({ movimientos });
      renderDashboard();
      await user.click(screen.getByRole('tab', { name: /Kardex/i }));
      await screen.findByText('Kardex de Inventario Profesional');
    };

    it('dado ningun filtro aplicado cuando carga entonces muestra el mensaje de que no hay movimientos', async () => {
      const user = setupUser();
      await goToKardex(user, []);

      expect(screen.getByText('No se encontraron movimientos con los filtros seleccionados.')).toBeInTheDocument();
    });

    it('dado clic en Consultar cuando responde el API entonces muestra los movimientos obtenidos', async () => {
      const user = setupUser();
      await goToKardex(user, [
        {
          id: 501,
          fecha: '2026-07-01T10:00:00',
          tipo_movimiento: 'COMPRA',
          producto: 'Tela Algodón Premium',
          producto_nombre: 'Tela Algodón Premium',
          bodega_origen: null,
          bodega_destino: 'Bodega Principal',
          cantidad: '25.00',
          documento_ref: 'FAC-001',
          usuario: 'admin',
        },
      ]);

      await user.click(screen.getByRole('button', { name: 'Consultar' }));

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('/inventory/movimientos/', { params: {} });
      });
      expect(await screen.findByText('Tela Algodón Premium')).toBeInTheDocument();
      expect(screen.getByText('FAC-001')).toBeInTheDocument();
    });

    it('dado bodega y producto seleccionados cuando se consulta entonces envia esos filtros y muestra columna Saldo', async () => {
      const user = setupUser();
      await goToKardex(user, [
        {
          id: 502,
          fecha: '2026-07-01T10:00:00',
          tipo_movimiento: 'COMPRA',
          producto: 'Tela Algodón Premium',
          producto_nombre: 'Tela Algodón Premium',
          bodega_origen: null,
          bodega_destino_nombre: 'Bodega Principal',
          bodega_destino: 'Bodega Principal',
          cantidad: '25.00',
          documento_ref: 'FAC-002',
          usuario: 'admin',
        },
      ]);

      await selectComboboxOption(user, 'Todas las Bodegas', 'Bodega Principal');
      await selectComboboxOption(user, 'Todos los productos', 'Tela Algodón Premium');
      await user.click(screen.getByRole('button', { name: 'Consultar' }));

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('/inventory/movimientos/', {
          params: { bodega_id: '1', producto_id: '1' },
        });
      });

      expect(await screen.findByText('Saldo')).toBeInTheDocument();
      expect(screen.getByText('25.00')).toBeInTheDocument();
    });

    it('dado filtros aplicados cuando se hace clic en Limpiar entonces resetea los filtros y los resultados', async () => {
      const user = setupUser();
      await goToKardex(user, [
        {
          id: 503,
          fecha: '2026-07-01T10:00:00',
          tipo_movimiento: 'COMPRA',
          producto: 'Tela Algodón Premium',
          producto_nombre: 'Tela Algodón Premium',
          bodega_origen: null,
          bodega_destino: 'Bodega Principal',
          cantidad: '25.00',
          documento_ref: 'FAC-003',
          usuario: 'admin',
        },
      ]);

      await user.click(screen.getByRole('button', { name: 'Consultar' }));
      await screen.findByText('Tela Algodón Premium');

      await user.click(screen.getByRole('button', { name: 'Limpiar' }));

      await waitFor(() => {
        expect(screen.getByText('No se encontraron movimientos con los filtros seleccionados.')).toBeInTheDocument();
      });
    });

    it('dado kardex vacio cuando se exporta a CSV entonces muestra un error y no descarga nada', async () => {
      const user = setupUser();
      await goToKardex(user, []);

      await user.click(screen.getByRole('button', { name: /Exportar CSV/i }));

      expect(toastErrorMock).toHaveBeenCalledWith('No hay datos para exportar');
      expect(URL.createObjectURL).not.toHaveBeenCalled();
    });

    it('dado datos de kardex cargados cuando se exporta a CSV entonces genera y descarga el archivo', async () => {
      const user = setupUser();
      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      await goToKardex(user, [
        {
          id: 504,
          fecha: '2026-07-01T10:00:00',
          tipo_movimiento: 'COMPRA',
          producto: 'Tela Algodón Premium',
          producto_nombre: 'Tela Algodón Premium',
          bodega_origen: null,
          bodega_destino: 'Bodega Principal',
          cantidad: '25.00',
          documento_ref: 'FAC-004',
          usuario: 'admin',
        },
      ]);

      await user.click(screen.getByRole('button', { name: 'Consultar' }));
      await screen.findByText('Tela Algodón Premium');

      await user.click(screen.getByRole('button', { name: /Exportar CSV/i }));

      expect(URL.createObjectURL).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
      clickSpy.mockRestore();
    });

    it('dado un movimiento en la tabla cuando se hace clic en el icono de edicion entonces abre el dialogo de edicion', async () => {
      const user = setupUser();
      await goToKardex(user, [
        {
          id: 505,
          fecha: '2026-07-01T10:00:00',
          tipo_movimiento: 'COMPRA',
          producto: 'Tela Algodón Premium',
          producto_nombre: 'Tela Algodón Premium',
          bodega_origen: null,
          bodega_destino: 'Bodega Principal',
          cantidad: '25.00',
          documento_ref: 'FAC-005',
          usuario: 'admin',
        },
      ]);

      await user.click(screen.getByRole('button', { name: 'Consultar' }));
      await screen.findByText('Tela Algodón Premium');

      const dataRow = screen.getByText('Tela Algodón Premium').closest('tr')!;
      const rowButtons = within(dataRow).getAllByRole('button');
      await user.click(rowButtons[1]);

      expect(await screen.findByText('Editar Entrada de Inventario')).toBeInTheDocument();
    });

    it('dado un movimiento en la tabla cuando se hace clic en el icono de auditoria entonces abre el dialogo de historial', async () => {
      const user = setupUser();
      await goToKardex(user, [
        {
          id: 506,
          fecha: '2026-07-01T10:00:00',
          tipo_movimiento: 'COMPRA',
          producto: 'Tela Algodón Premium',
          producto_nombre: 'Tela Algodón Premium',
          bodega_origen: null,
          bodega_destino: 'Bodega Principal',
          cantidad: '25.00',
          documento_ref: 'FAC-006',
          usuario: 'admin',
        },
      ]);

      await user.click(screen.getByRole('button', { name: 'Consultar' }));
      await screen.findByText('Tela Algodón Premium');

      const dataRow = screen.getByText('Tela Algodón Premium').closest('tr')!;
      const rowButtons = within(dataRow).getAllByRole('button');
      await user.click(rowButtons[0]);

      expect(await screen.findByText('Historial de Cambios')).toBeInTheDocument();
      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('/inventory/movimientos/506/auditoria/');
      });
    });

    it('dado clic en Registrar Merma cuando se abre entonces muestra el dialogo de registro de merma', async () => {
      const user = setupUser();
      await goToKardex(user, []);

      await user.click(screen.getByRole('button', { name: /Registrar Merma/i }));

      expect(await screen.findByRole('heading', { name: 'Registrar Merma' })).toBeInTheDocument();
    });

    it('dado un movimiento en la tabla cuando se hace clic en el icono de eliminar y confirma entonces revierte el movimiento', async () => {
      const user = setupUser();
      await goToKardex(user, [
        {
          id: 507,
          fecha: '2026-07-01T10:00:00',
          tipo_movimiento: 'MERMA',
          producto: 'Tela Algodón Premium',
          producto_nombre: 'Tela Algodón Premium',
          bodega_origen: 'Bodega Principal',
          bodega_destino: null,
          cantidad: '5.00',
          documento_ref: '',
          usuario: 'admin',
        },
      ]);

      await user.click(screen.getByRole('button', { name: 'Consultar' }));
      await screen.findByText('Tela Algodón Premium');

      const dataRow = screen.getByText('Tela Algodón Premium').closest('tr')!;
      const rowButtons = within(dataRow).getAllByRole('button');
      await user.click(rowButtons[2]);

      expect(await screen.findByRole('heading', { name: 'Eliminar Movimiento' })).toBeInTheDocument();

      await user.type(screen.getByLabelText('Justificación (Obligatoria)'), 'Merma registrada por error');
      await user.click(screen.getByRole('button', { name: 'Eliminar y Revertir' }));

      await waitFor(() => {
        expect(mockDelete).toHaveBeenCalledWith('/inventory/movimientos/507/', {
          data: { justificacion: 'Merma registrada por error' },
        });
      });
    });
  });
});
