/**
 * ISTQB — Nivel: Componente / Integración
 * Técnica : Black-box (equivalencia de partición + valor límite + transición de estados)
 * Cubre   : CU-EJ-01..06 — todo lo que NO cubre EjecutivosDashboard.reportes.test.tsx
 *            - Estados de carga / error / vacío del fetch principal
 *            - Header (modo ejecutivo vs. modo admin de sede) y filtro de sede
 *            - Botón Actualizar y auto-refresh (intervalo de 60s)
 *            - Tab Resumen: KPIs consolidados y semáforos de alerta (OCS, cartera vencida)
 *            - Tab Producción: KPIs, donut de estado de OPs, gráfico de Tendencia de Producción
 *              con sus selectores de rango (7/15/30/90) y agrupación (diario/semanal/mensual)
 *            - Tab Stock: KPIs, gráficos, búsqueda/filtro de alertas
 *            - Tab Ventas: KPIs, funnel, fallback de "sin deudores"
 *
 * NOTA: ResponsiveContainer de recharts no renderiza contenido en jsdom porque
 * el ancho/alto del contenedor es 0 (no hay layout real). Se mockea únicamente
 * ResponsiveContainer para forzar un tamaño fijo y permitir verificar, a través
 * del DOM renderizado, que los datos agrupados por el useMemo llegan correctos
 * a los ejes/leyendas — sin tocar la lógica real de los charts.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
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

// Select con contexto propio por instancia — a diferencia de una única
// variable global, permite tener el selector de sede (header) y el selector
// de rango de tendencia (tab Producción) montados simultáneamente sin que
// uno pise el onValueChange del otro.
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

// Fuerza un tamaño fijo en ResponsiveContainer: en jsdom el contenedor real
// mide 0x0 y recharts no dibuja nada dentro, lo que impediría verificar el
// resultado del useMemo de agrupación de la tendencia.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<any>();
  return {
    ...actual,
    ResponsiveContainer: ({ children, height }: any) => (
      <div style={{ width: 800, height: height ?? 280 }}>
        {React.cloneElement(children, { width: 800, height: height ?? 280 })}
      </div>
    ),
  };
});

vi.mock('../shared/MRPDashboard', () => ({
  MRPDashboard: () => <div data-testid="mock-mrp-dashboard">MRP Mock</div>,
}));
vi.mock('../shared/MovementApproval', () => ({
  MovementApproval: () => <div data-testid="mock-movement-approval">Movement Mock</div>,
}));
vi.mock('../shared/AuditLogViewer', () => ({
  AuditLogViewer: () => <div data-testid="mock-audit-log">Audit Mock</div>,
}));

global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

// ── Importación del componente ────────────────────────────────────────────────

import { EjecutivosDashboard } from './EjecutivosDashboard';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const KPI_FULL = {
  produccion: { ops_pendiente: 4, ops_en_proceso: 7, ops_finalizada: 20, kg_hoy: 120.5, kg_semana: 800, kg_mes: 3200.5, tiempo_promedio_lote_min: 45 },
  mrp: { ocs_pendientes: 3, ocs_aprobadas: 6, ocs_rechazadas: 1, productos_en_deficit: 2 },
  stock: { productos_bajo_minimo: 5 },
  cartera: { cuentas_por_cobrar: 0, cartera_vencida: 0, pedidos_pendientes: 9, pedidos_despachados: 15 },
};

const KPI_SIN_OCS = {
  ...KPI_FULL,
  mrp: { ...KPI_FULL.mrp, ocs_pendientes: 0 },
};

const PRODUCCION_RESUMEN_FULL = {
  ops_por_estado: [
    { estado: 'Pendiente', value: 4, fill: '#f59e0b' },
    { estado: 'En Proceso', value: 7, fill: '#3b82f6' },
    { estado: 'Finalizada', value: 20, fill: '#10b981' },
  ],
  kg_hoy: 120.5, kg_semana: 800, kg_mes: 3200.5, tiempo_promedio_lote_min: 45,
};

const PRODUCCION_RESUMEN_VACIO = {
  ops_por_estado: [{ estado: 'Pendiente', value: 0, fill: '#f59e0b' }],
  kg_hoy: 0, kg_semana: 0, kg_mes: 0, tiempo_promedio_lote_min: 0,
};

const ALERTAS_FULL = [
  { producto: 'Hilo Poliéster Blanco', producto_codigo: 'HP-001', bodega: 'Bodega Norte', stock_actual: '10', stock_minimo: '50', faltante: 40 },
  { producto: 'Hilo Poliéster Negro', producto_codigo: 'HP-002', bodega: 'Bodega Sur', stock_actual: '5', stock_minimo: '20', faltante: 15 },
];

const STOCK_FULL = [
  { id: 1, producto: 'Hilo Blanco', bodega: 'Bodega Norte', lote: 'L1', cantidad: '100' },
  { id: 2, producto: 'Hilo Negro', bodega: 'Bodega Sur', lote: 'L2', cantidad: '50' },
];

const CLIENTES_NEUTRO = [
  { id: 1, nombre_razon_social: 'Cliente Uno', saldo_pendiente: '500', limite_credito: 2000, cartera_vencida: '100' },
];

const CLIENTES_ALERTA = [
  { id: 1, nombre_razon_social: 'Cliente Riesgo', saldo_pendiente: '1000', limite_credito: 2000, cartera_vencida: '900' },
];

const CLIENTES_SIN_DEUDA = [
  { id: 1, nombre_razon_social: 'Cliente Al Día', saldo_pendiente: '0', limite_credito: 2000, cartera_vencida: '0' },
];

const PEDIDOS_FULL = [
  { id: 1, cliente: 1, cliente_nombre: 'Cliente Uno', vendedor_nombre: 'Vendedor A', guia_remision: 'G1', fecha_pedido: '2026-07-01', estado: 'pendiente', esta_pagado: false, sede: 1, total: 1000, anulado: false },
  { id: 2, cliente: 1, cliente_nombre: 'Cliente Uno', vendedor_nombre: 'Vendedor A', guia_remision: 'G2', fecha_pedido: '2026-07-02', estado: 'despachado', esta_pagado: true, sede: 1, total: 2000, anulado: false },
  { id: 3, cliente: 1, cliente_nombre: 'Cliente Uno', vendedor_nombre: 'Vendedor B', guia_remision: 'G3', fecha_pedido: '2026-07-03', estado: 'facturado', esta_pagado: true, sede: 1, total: 500, anulado: false },
];

const SEDES_FULL = [{ id: 42, nombre: 'Sede Principal', location: 'Quito', status: 'activo' }];

/** Construye una serie de `days` días consecutivos desde `startDate`, kg constante. */
function buildTendencia(startDate: string, days: number, kg = 10) {
  const start = new Date(`${startDate}T00:00:00`);
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return { fecha: d.toISOString().split('T')[0], kg };
  });
}

// 30 días de junio (2026-06-01..30) + 10 días de julio (2026-07-01..10) = 40 días
const TENDENCIA_40D = buildTendencia('2026-06-01', 40, 10);

function buildMockData(overrides: Record<string, unknown> = {}) {
  return {
    '/kpi-ejecutivo/': KPI_FULL,
    '/produccion/resumen/': PRODUCCION_RESUMEN_FULL,
    '/produccion/tendencia/': TENDENCIA_40D,
    '/inventory/alertas-stock/': ALERTAS_FULL,
    '/inventory/stock/': STOCK_FULL,
    '/clientes/': CLIENTES_NEUTRO,
    '/pedidos-venta/': PEDIDOS_FULL,
    '/sedes/': SEDES_FULL,
    ...overrides,
  };
}

function mockApi(data: Record<string, unknown>) {
  return (url: string) => Promise.resolve({ data: (data as any)[url] ?? [] });
}

const setupUser = () => userEvent.setup({ pointerEventsCheck: 0 });

const renderDashboard = (isAdminSede = false) =>
  render(
    <BrowserRouter>
      <EjecutivosDashboard isAdminSede={isAdminSede} />
    </BrowserRouter>
  );

const esperarCarga = async () =>
  waitFor(() => expect(screen.getByText('Panel Ejecutivo')).toBeInTheDocument());

const irATab = async (user: ReturnType<typeof userEvent.setup>, nombre: RegExp) => {
  const tab = screen.getByRole('tab', { name: nombre });
  await user.click(tab);
};

/**
 * Simula el hover que recharts necesita para activar el Tooltip de un chart
 * "axis" (Bar/Area/Line): jsdom no calcula layout real, así que getBoundingClientRect
 * y offsetWidth/offsetHeight se fuerzan al tamaño fijo que ya inyecta el mock de
 * ResponsiveContainer — de lo contrario el cálculo interno de recharts (bbox.width /
 * offsetWidth) da Infinity y el mouse nunca cae "dentro" del chart.
 */
function hoverAxisChart(card: HTMLElement, width: number, height: number, x: number, y: number) {
  const wrapper = card.querySelector('.recharts-wrapper') as HTMLElement;
  const rect = { left: 0, top: 0, right: width, bottom: height, width, height, x: 0, y: 0, toJSON: () => {} };
  wrapper.getBoundingClientRect = () => rect as any;
  Object.defineProperty(wrapper, 'offsetWidth', { configurable: true, value: width });
  Object.defineProperty(wrapper, 'offsetHeight', { configurable: true, value: height });
  fireEvent.mouseMove(wrapper, { clientX: x, clientY: y, pageX: x, pageY: y });
  fireEvent.mouseOver(wrapper, { clientX: x, clientY: y, pageX: x, pageY: y });
}

/** Ubica la Card (shadcn, data-slot="card") que contiene el título dado. */
function cardOf(tituloTexto: string): HTMLElement {
  return screen.getByText(tituloTexto).closest('[data-slot="card"]') as HTMLElement;
}

// ── Suite de tests ────────────────────────────────────────────────────────────

describe('EjecutivosDashboard — flujos principales (fuera de Reportes)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation(mockApi(buildMockData()));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ── 1. Carga / error / vacío ────────────────────────────────────────────────

  it('dado un fetch en curso cuando el componente monta entonces muestra el estado de carga', async () => {
    (apiClient.get as any).mockImplementation(() => new Promise(() => {}));
    const { container } = renderDashboard();

    expect(screen.queryByText('Panel Ejecutivo')).not.toBeInTheDocument();
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it('dado un error inesperado al construir las peticiones cuando carga entonces muestra toast de error y no rompe el render', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/kpi-ejecutivo/') throw new Error('boom');
      return mockApi(buildMockData())(url);
    });
    renderDashboard();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar los datos del dashboard'));
    await esperarCarga();
  });

  it('dado que el endpoint de KPI falla individualmente cuando carga entonces los KPIs muestran guiones de fallback', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/kpi-ejecutivo/') return Promise.reject(new Error('500'));
      return mockApi(buildMockData())(url);
    });
    renderDashboard();
    await esperarCarga();

    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  // ── 2. Header ────────────────────────────────────────────────────────────────

  it('dado modo ejecutivo cuando carga entonces muestra el título y usuario correctos', async () => {
    renderDashboard();
    await esperarCarga();

    expect(screen.getByText('Vista gerencial consolidada', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('gerente_test')).toBeInTheDocument();
    expect(screen.getByTestId('mock-select')).toBeInTheDocument();
  });

  it('dado modo administrador de sede cuando carga entonces muestra título alterno, sin selector de sede y con tab de Aprobaciones activo', async () => {
    renderDashboard(true);
    await waitFor(() => expect(screen.getByText('Panel de Administrador de Sede')).toBeInTheDocument());

    expect(screen.queryByTestId('mock-select')).not.toBeInTheDocument();
    expect(screen.getByTestId('mock-movement-approval')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Auditoría/i })).toBeInTheDocument();
  });

  // ── 3. Actualizar / auto-refresh ──────────────────────────────────────────────

  it('dado clic en Actualizar cuando la petición resuelve entonces refresca datos y muestra toast de éxito', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();

    const llamadasIniciales = (apiClient.get as any).mock.calls.length;
    await user.click(screen.getByRole('button', { name: /Actualizar/i }));

    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Datos actualizados'));
    expect((apiClient.get as any).mock.calls.length).toBeGreaterThan(llamadasIniciales);
  });

  it('dado auto-refresh activo (por defecto) cuando transcurren 60s entonces vuelve a solicitar los datos', async () => {
    vi.useFakeTimers();
    renderDashboard();
    await vi.waitFor(() => expect(screen.getByText('Panel Ejecutivo')).toBeInTheDocument());

    const llamadasIniciales = (apiClient.get as any).mock.calls.length;
    await vi.advanceTimersByTimeAsync(60_000);

    await vi.waitFor(() =>
      expect((apiClient.get as any).mock.calls.length).toBeGreaterThan(llamadasIniciales)
    );
  });

  it('dado clic en el botón Auto (desactivarlo) cuando transcurren 60s entonces NO vuelve a solicitar los datos', async () => {
    vi.useFakeTimers();
    renderDashboard();
    await vi.waitFor(() => expect(screen.getByText('Panel Ejecutivo')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Auto/i }));

    const llamadasTrasDesactivar = (apiClient.get as any).mock.calls.length;
    await vi.advanceTimersByTimeAsync(60_000);

    expect((apiClient.get as any).mock.calls.length).toBe(llamadasTrasDesactivar);
  });

  // ── 4. Filtro de sede ──────────────────────────────────────────────────────────

  it('dado que el usuario selecciona una sede cuando cambia el filtro entonces refresca los datos con sede_id', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();

    const sedeBtn = await screen.findByTestId('select-item-42');
    await user.click(sedeBtn);

    await waitFor(() => {
      const llamada = (apiClient.get as any).mock.calls.find(
        (c: any[]) => c[0] === '/kpi-ejecutivo/' && c[1]?.params?.sede_id === '42'
      );
      expect(llamada).toBeDefined();
    });
  });

  // ── 5. Tab Resumen — KPIs consolidados ─────────────────────────────────────────

  it('dado datos completos cuando se muestra el tab Resumen entonces renderiza los KPIs de producción, MRP y cartera', async () => {
    renderDashboard();
    await esperarCarga();

    expect(screen.getByText('OPs en Proceso')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('120,5')).toBeInTheDocument();
    expect(screen.getByText('3.200,5')).toBeInTheDocument();
    expect(screen.getByText('OCS Pendientes')).toBeInTheDocument();
    expect(screen.getByText('Productos en Déficit')).toBeInTheDocument();
    expect(screen.getByText('$500,00')).toBeInTheDocument();
    expect(screen.getByText('$100,00')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
  });

  it('dado OCS pendientes mayor a cero cuando se muestra el Resumen entonces marca la alerta correspondiente', async () => {
    renderDashboard();
    await esperarCarga();

    expect(screen.getByText('Requieren decisión del ejecutivo')).toBeInTheDocument();
  });

  it('dado cero OCS pendientes cuando se muestra el Resumen entonces NO marca alerta de OCS', async () => {
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({ '/kpi-ejecutivo/': KPI_SIN_OCS })));
    renderDashboard();
    await esperarCarga();

    expect(screen.queryByText('Requieren decisión del ejecutivo')).not.toBeInTheDocument();
  });

  it('dado que la cartera vencida supera el 40% del límite de crédito cuando se muestra el Resumen entonces marca alerta de cartera', async () => {
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({ '/clientes/': CLIENTES_ALERTA })));
    renderDashboard();
    await esperarCarga();

    expect(screen.getByText('Supera el 40% del límite de crédito')).toBeInTheDocument();
    expect(screen.getByText('45% del límite de crédito')).toBeInTheDocument();
  });

  it('dado que la cartera vencida NO supera el 40% del límite de crédito cuando se muestra el Resumen entonces indica sin alerta de riesgo', async () => {
    renderDashboard();
    await esperarCarga();

    expect(screen.getByText('Sin alerta de riesgo')).toBeInTheDocument();
    expect(screen.queryByText('Supera el 40% del límite de crédito')).not.toBeInTheDocument();
  });

  // ── 6. Tab Producción — KPIs y donut de OPs ────────────────────────────────────

  it('dado datos de producción cuando se navega al tab Producción entonces muestra sus KPIs', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    expect(screen.getByText('kg Semana')).toBeInTheDocument();
    expect(screen.getByText('800,0')).toBeInTheDocument();
    expect(screen.getByText('45 min')).toBeInTheDocument();
  });

  it('dado ops_por_estado sin valores positivos cuando se muestra el donut entonces indica que no hay órdenes', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({ '/produccion/resumen/': PRODUCCION_RESUMEN_VACIO })));
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    expect(screen.getByText('Sin órdenes de producción')).toBeInTheDocument();
  });

  it('dado ops_por_estado con datos cuando se muestra el donut entonces renderiza la leyenda por estado', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    expect(screen.queryByText('Sin órdenes de producción')).not.toBeInTheDocument();
    expect(screen.getByText('Pendiente')).toBeInTheDocument();
    expect(screen.getByText('En Proceso')).toBeInTheDocument();
    expect(screen.getByText('Finalizada')).toBeInTheDocument();
  });

  // ── 7. Tab Producción — Tendencia (rango + agrupación) ─────────────────────────

  it('dado tendencia vacía cuando se muestra el gráfico entonces indica que no hay datos', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({ '/produccion/tendencia/': [] })));
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    expect(screen.getByText('Sin datos de tendencia')).toBeInTheDocument();
  });

  it('dado agrupación diaria por defecto cuando se muestra la tendencia entonces la descripción indica vista diaria', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    expect(screen.getByText(/vista diaria/i)).toBeInTheDocument();
    expect(screen.queryByText('Sin datos de tendencia')).not.toBeInTheDocument();
  });

  it('dado un rango de 7 días seleccionado cuando se procesa la tendencia entonces solo grafica los últimos 7 días', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    await user.click(screen.getByTestId('select-item-7'));

    // Los últimos 7 de los 40 días generados son 2026-07-04..2026-07-10
    await waitFor(() => expect(screen.getByText('07-04')).toBeInTheDocument());
    expect(screen.getByText('07-10')).toBeInTheDocument();
    expect(screen.queryByText('06-11')).not.toBeInTheDocument();
  });

  it('dado agrupación semanal seleccionada cuando se procesa la tendencia entonces agrupa en buckets de 7 días', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    await user.click(screen.getByRole('button', { name: 'Semanal' }));

    await waitFor(() => expect(screen.getByText(/agrupado por semana/i)).toBeInTheDocument());
    // rango por defecto = 30 días => últimos 30 de los 40 generados: 2026-06-11..2026-07-10
    // Semana 1: 06-11..06-17 (7 días) — Semana 5: 09-10 (2 días restantes)
    expect(screen.getByText('S1 (11-17)')).toBeInTheDocument();
    expect(screen.getByText('S5 (09-10)')).toBeInTheDocument();
  });

  it('dado agrupación mensual seleccionada cuando se procesa la tendencia entonces agrupa por mes calendario', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    // Ampliamos el rango a 90 para incluir los 40 días completos (jun + jul)
    await user.click(screen.getByTestId('select-item-90'));
    await user.click(screen.getByRole('button', { name: 'Mensual' }));

    await waitFor(() => expect(screen.getByText(/agrupado por mes/i)).toBeInTheDocument());
    expect(screen.getByText('Jun 2026')).toBeInTheDocument();
    expect(screen.getByText('Jul 2026')).toBeInTheDocument();
  });

  // ── 8. Tab Stock ───────────────────────────────────────────────────────────────

  it('dado datos de stock y alertas cuando se navega al tab Stock entonces muestra sus KPIs y la tabla completa', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Stock/i);

    expect(screen.getByText('Bodegas')).toBeInTheDocument();
    const tabla = screen.getByRole('table');
    expect(within(tabla).getByText('HP-001')).toBeInTheDocument();
    expect(within(tabla).getByText('HP-002')).toBeInTheDocument();
    expect(screen.getByText('2 de 2 productos con stock bajo mínimo')).toBeInTheDocument();
  });

  it('dado un término de búsqueda que coincide cuando se filtra el tab Stock entonces reduce la tabla de alertas', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Stock/i);

    await user.type(screen.getByPlaceholderText('Buscar producto…'), 'HP-002');

    await waitFor(() => expect(screen.getByText('1 de 2 productos con stock bajo mínimo')).toBeInTheDocument());
    const tabla = screen.getByRole('table');
    expect(within(tabla).getByText('HP-002')).toBeInTheDocument();
    expect(within(tabla).queryByText('HP-001')).not.toBeInTheDocument();
  });

  it('dado un término de búsqueda sin coincidencias cuando se filtra el tab Stock entonces muestra sin resultados', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Stock/i);

    await user.type(screen.getByPlaceholderText('Buscar producto…'), 'ZZZ-INEXISTENTE');

    await waitFor(() => expect(screen.getByText('Sin resultados')).toBeInTheDocument());
  });

  it('dado sin alertas de stock cuando se muestra el gráfico de faltantes entonces indica sin alertas críticas', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({ '/inventory/alertas-stock/': [] })));
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Stock/i);

    expect(screen.getByText('Sin alertas críticas')).toBeInTheDocument();
  });

  // ── 9. Tab Ventas ────────────────────────────────────────────────────────────

  it('dado pedidos y clientes cuando se navega al tab Ventas entonces muestra sus KPIs de cartera y ventas', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Ventas/i);

    expect(screen.getByText('Total Ventas Período')).toBeInTheDocument();
    expect(screen.getByText('$3.500,00')).toBeInTheDocument();
    expect(screen.getByText('3 pedidos')).toBeInTheDocument();
    expect(screen.getByText('Funnel de Pedidos')).toBeInTheDocument();
  });

  it('dado clientes sin saldo pendiente cuando se muestra el ranking de deudores entonces indica que no hay deudores', async () => {
    const user = setupUser();
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({ '/clientes/': CLIENTES_SIN_DEUDA })));
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Ventas/i);

    expect(screen.getByText('Sin deudores')).toBeInTheDocument();
  });

  // ── 10. Fetch — fallas individuales de sedes y de endpoints secundarios ───────

  it('dado que el endpoint de sedes falla cuando carga entonces no rompe y el selector queda sin sedes adicionales', async () => {
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/sedes/') return Promise.reject(new Error('500'));
      return mockApi(buildMockData())(url);
    });
    renderDashboard();
    await esperarCarga();

    expect(screen.getByTestId('mock-select')).toBeInTheDocument();
    expect(screen.queryByTestId('select-item-42')).not.toBeInTheDocument();
  });

  it('dado que producción, tendencia, alertas, stock, clientes y pedidos fallan simultáneamente cuando carga entonces usa fallbacks vacíos sin romper el render', async () => {
    const user = setupUser();
    const fallidos = [
      '/produccion/resumen/', '/produccion/tendencia/', '/inventory/alertas-stock/',
      '/inventory/stock/', '/clientes/', '/pedidos-venta/',
    ];
    (apiClient.get as any).mockImplementation((url: string) => {
      if (fallidos.includes(url)) return Promise.reject(new Error('500'));
      return mockApi(buildMockData())(url);
    });
    renderDashboard();
    await esperarCarga();

    await irATab(user, /Producción/i);
    expect(screen.getByText('Sin órdenes de producción')).toBeInTheDocument();
    expect(screen.getByText('Sin datos de tendencia')).toBeInTheDocument();

    await irATab(user, /Stock/i);
    expect(screen.getByText('Sin alertas críticas')).toBeInTheDocument();
    expect(screen.getByText('0 de 0 productos con stock bajo mínimo')).toBeInTheDocument();

    await irATab(user, /Ventas/i);
    expect(screen.getByText('Sin deudores')).toBeInTheDocument();
    expect(screen.getByText('Sin pedidos')).toBeInTheDocument();
  });

  // ── 11. Cartera — valores no numéricos / ausentes en el cliente ──────────────

  it('dado un cliente sin límite de crédito definido cuando se calcula la cartera entonces trata el límite como cero sin marcar alerta', async () => {
    const CLIENTE_SIN_LIMITE = [
      { id: 1, nombre_razon_social: 'Cliente Sin Límite', saldo_pendiente: '500', cartera_vencida: '100' },
    ];
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({ '/clientes/': CLIENTE_SIN_LIMITE })));
    renderDashboard();
    await esperarCarga();

    expect(screen.getByText('$500,00')).toBeInTheDocument();
    expect(screen.getByText('Sin alerta de riesgo')).toBeInTheDocument();
  });

  // ── 12. Ventas — ranking con dos entidades distintas (ordenamiento) ──────────

  it('dado pedidos de dos clientes y clientes con dos deudores distintos cuando se muestra Ventas entonces incluye ambas entidades en los rankings', async () => {
    const user = setupUser();
    const PEDIDOS_DOS_CLIENTES = [
      { id: 1, cliente: 1, cliente_nombre: 'Cliente Bajo', vendedor_nombre: 'Vendedor A', guia_remision: 'G1', fecha_pedido: '2026-07-01', estado: 'pendiente', esta_pagado: false, sede: 1, total: 100, anulado: false },
      { id: 2, cliente: 2, cliente_nombre: 'Cliente Alto', vendedor_nombre: 'Vendedor A', guia_remision: 'G2', fecha_pedido: '2026-07-02', estado: 'despachado', esta_pagado: true, sede: 1, total: 900, anulado: false },
    ];
    const CLIENTES_DOS_DEUDORES = [
      { id: 1, nombre_razon_social: 'Deudor Menor', saldo_pendiente: '100', limite_credito: 2000, cartera_vencida: '0' },
      { id: 2, nombre_razon_social: 'Deudor Mayor', saldo_pendiente: '900', limite_credito: 2000, cartera_vencida: '0' },
    ];
    (apiClient.get as any).mockImplementation(mockApi(buildMockData({
      '/pedidos-venta/': PEDIDOS_DOS_CLIENTES,
      '/clientes/': CLIENTES_DOS_DEUDORES,
    })));
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Ventas/i);

    expect(screen.getByText('Cliente Alto')).toBeInTheDocument();
    expect(screen.getByText('Cliente Bajo')).toBeInTheDocument();
    expect(screen.getByText('Deudor Mayor')).toBeInTheDocument();
    expect(screen.getByText('Deudor Menor')).toBeInTheDocument();
  });

  // ── 13. Exportar — guard de descarga concurrente entre tabs ──────────────────

  it('dado una descarga de Reportes en curso cuando se hace clic en un botón de exportación de otro tab entonces no dispara una nueva descarga', async () => {
    const user = setupUser();
    const pendiente = new Promise(() => {});
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/reporting/gerencial/ventas') return pendiente;
      return mockApi(buildMockData())(url);
    });
    renderDashboard();
    await esperarCarga();

    await irATab(user, /Reportes/i);
    await waitFor(() => expect(screen.getByText(/Centro de reportes gerenciales/i)).toBeInTheDocument());
    await user.click(screen.getByTestId('btn-export-ventas'));

    await irATab(user, /Producción/i);
    await user.click(screen.getByRole('button', { name: /Órdenes de Producción/i }));

    await waitFor(() => {
      const llamada = (apiClient.get as any).mock.calls.find((c: any[]) => c[0] === '/reporting/produccion/ordenes');
      expect(llamada).toBeUndefined();
    });
  });

  // ── 14. Fechas de reporte — inputs duplicados en Producción y Ventas ─────────

  it('dado que se cambian las fechas de reporte desde el tab Producción cuando se actualizan los inputs entonces el estado compartido de fechas se actualiza', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Producción/i);

    const inputs = Array.from(document.querySelectorAll('input[type="date"]')) as HTMLInputElement[];
    expect(inputs.length).toBe(2);
    fireEvent.change(inputs[0], { target: { value: '2026-02-01' } });
    fireEvent.change(inputs[1], { target: { value: '2026-02-28' } });

    await irATab(user, /Reportes/i);
    await waitFor(() => expect(screen.getByText(/Centro de reportes gerenciales/i)).toBeInTheDocument());
    const reportInputs = Array.from(document.querySelectorAll('input[type="date"]')) as HTMLInputElement[];
    expect(reportInputs[0].value).toBe('2026-02-01');
    expect(reportInputs[1].value).toBe('2026-02-28');
  });

  it('dado que se cambian las fechas de reporte desde el tab Ventas cuando se actualizan los inputs entonces el estado compartido de fechas se actualiza', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();
    await irATab(user, /Ventas/i);

    const inputs = Array.from(document.querySelectorAll('input[type="date"]')) as HTMLInputElement[];
    expect(inputs.length).toBe(2);
    fireEvent.change(inputs[0], { target: { value: '2026-03-01' } });
    fireEvent.change(inputs[1], { target: { value: '2026-03-31' } });

    await irATab(user, /Reportes/i);
    await waitFor(() => expect(screen.getByText(/Centro de reportes gerenciales/i)).toBeInTheDocument());
    const reportInputs = Array.from(document.querySelectorAll('input[type="date"]')) as HTMLInputElement[];
    expect(reportInputs[0].value).toBe('2026-03-01');
    expect(reportInputs[1].value).toBe('2026-03-31');
  });

  // ── 15. Tooltips de gráficos — formatter/content callbacks de recharts ───────

  it('dado hover sobre los distintos gráficos cuando se activa el tooltip entonces cada formatter muestra el valor esperado', async () => {
    const user = setupUser();
    renderDashboard();
    await esperarCarga();

    // Producción: donut (Pie) — formatter={(v) => [v, 'OPs']}
    await irATab(user, /Producción/i);
    await waitFor(() => expect(document.querySelectorAll('.recharts-sector').length).toBeGreaterThan(0), { timeout: 3000 });
    const donutCard = cardOf('Estado de Órdenes de Producción');
    const donutSector = donutCard.querySelector('.recharts-sector') as HTMLElement;
    fireEvent.mouseEnter(donutSector);
    fireEvent.mouseOver(donutSector);
    await waitFor(() => expect(donutCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('OPs'));

    // Producción: tendencia (Area) — contenido custom con "kg"
    const tendCard = cardOf('Tendencia de Producción');
    hoverAxisChart(tendCard, 800, 280, 400, 140);
    await waitFor(() => expect(tendCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('kg'));

    // Stock: bar (stock por bodega) + horizontal bar (top alertas)
    await irATab(user, /Stock/i);
    await waitFor(() => expect(document.querySelectorAll('.recharts-rectangle').length).toBeGreaterThan(0), { timeout: 3000 });
    const stockCard = cardOf('Stock por Bodega');
    hoverAxisChart(stockCard, 800, 260, 242, 100);
    await waitFor(() => expect(stockCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('Stock'));

    const alertasCard = cardOf('Top Alertas por Faltante');
    hoverAxisChart(alertasCard, 800, 260, 400, 30);
    await waitFor(() => expect(alertasCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('Faltante'));

    // Ventas: funnel, ventas por vendedor, cobranza (pie), top clientes, top deudores
    await irATab(user, /Ventas/i);
    await waitFor(() => expect(document.querySelectorAll('.recharts-rectangle, .recharts-sector').length).toBeGreaterThan(0), { timeout: 3000 });

    const funnelCard = cardOf('Funnel de Pedidos');
    hoverAxisChart(funnelCard, 800, 160, 400, 20);
    await waitFor(() => expect(funnelCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('Pedidos'));

    const vendedorCard = cardOf('Ventas por Vendedor');
    hoverAxisChart(vendedorCard, 800, 260, 242, 100);
    await waitFor(() => expect(vendedorCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('Ventas'));

    const cobranzaCard = cardOf('Estado de Cobranza');
    await waitFor(() => expect(cobranzaCard.querySelectorAll('.recharts-sector').length).toBeGreaterThan(0), { timeout: 3000 });
    const cobranzaSector = cobranzaCard.querySelector('.recharts-sector') as HTMLElement;
    fireEvent.mouseEnter(cobranzaSector);
    fireEvent.mouseOver(cobranzaSector);
    await waitFor(() => expect(cobranzaCard.querySelector('.recharts-tooltip-wrapper')).toBeInTheDocument());

    const topClientesCard = cardOf('Top Clientes por Compras');
    hoverAxisChart(topClientesCard, 800, 260, 400, 30);
    await waitFor(() => expect(topClientesCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('Compras'));

    const topDeudoresCard = cardOf('Top Clientes Deudores');
    hoverAxisChart(topDeudoresCard, 800, 260, 400, 30);
    await waitFor(() => expect(topDeudoresCard.querySelector('.recharts-tooltip-wrapper')).toHaveTextContent('Deuda'));
  }, 20000);
});
