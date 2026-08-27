import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Tabs } from '../ui/tabs';
import { VentasTab } from './VentasTab';
import type { Cliente, PedidoVenta } from '../../lib/types';

// VentasTab es puramente presentacional (no importa apiClient/useAuth/sonner):
// los 4 <Bar onClick> solo leen data.payload y llaman a un setter que llega
// por props. El único bloqueo real para testearlo es que recharts no dibuja
// nada dentro de ResponsiveContainer en jsdom (mide 0x0). El shim parcial que
// ya existe en el repo (EjecutivosDashboard.test.tsx) solo fuerza el tamaño y
// deja el SVG real — aquí se usa un shim COMPLETO, local a este archivo, que
// convierte cada <Bar> en botones deterministas (uno por item de `data`), sin
// depender de que jsdom calcule geometría SVG.
const ChartDataCtx = React.createContext<any[]>([]);
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<any>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
    BarChart: ({ data, children }: any) => (
      <ChartDataCtx.Provider value={data}><div>{children}</div></ChartDataCtx.Provider>
    ),
    Bar: ({ dataKey, onClick }: any) => {
      const data = React.useContext(ChartDataCtx);
      return (
        <div data-testid={`bar-${dataKey}`}>
          {data.map((item: any, i: number) => (
            <button key={i} onClick={() => onClick?.({ payload: item }, i)}>
              {`bar-${dataKey}-${i}`}
            </button>
          ))}
        </div>
      );
    },
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    Cell: () => null,
    PieChart: ({ children }: any) => <div>{children}</div>,
    Pie: () => null,
  };
});

function renderVentasTab(overrides: Partial<React.ComponentProps<typeof VentasTab>> = {}) {
  const props: React.ComponentProps<typeof VentasTab> = {
    pedidos: [] as PedidoVenta[],
    clientes: [] as Cliente[],
    cuentasPorCobrar: 1000,
    carteraVencida: 200,
    limiteCartera: 5000,
    alertaCartera: false,
    totalVentas: 3000,
    ventasPorVendedor: [{ name: 'Juan', fullName: 'Juan Pérez', value: 500 }],
    topClientesGerencial: [{ name: 'Cliente A', fullName: 'Cliente A SA', value: 800 }],
    topDeudores: [{ name: 'Deudor A', fullName: 'Deudor A SA', deuda: 300, obj: {} as Cliente }],
    distribucionPago: [{ name: 'Pagado', value: 700, color: '#22c55e' }],
    funnelData: [{ estado: 'Pendiente', key: 'pendiente', total: 5, fill: '#f59e0b' }],
    modalEstadoPedido: null,
    setModalEstadoPedido: vi.fn(),
    modalVendedor: null,
    setModalVendedor: vi.fn(),
    modalClienteCompras: null,
    setModalClienteCompras: vi.fn(),
    modalClienteDeudor: null,
    setModalClienteDeudor: vi.fn(),
    reportFechas: { inicio: '', fin: '' },
    setReportFechas: vi.fn(),
    exportVentas: vi.fn(),
    exportTopClientes: vi.fn(),
    exportDeudores: vi.fn(),
    ...overrides,
  };
  const utils = render(
    <Tabs defaultValue="ventas">
      <VentasTab {...props} />
    </Tabs>,
  );
  return { ...utils, props };
}

describe('VentasTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('dado los KPIs cuando renderiza entonces muestra los valores formateados', () => {
    renderVentasTab({ cuentasPorCobrar: 1234.5, totalVentas: 9000, clientes: [
      { is_active: true, tiene_beneficio: true } as any,
      { is_active: false, tiene_beneficio: false } as any,
    ] });
    expect(screen.getByText('$1.234,50')).toBeInTheDocument();
    expect(screen.getByText('$9.000,00')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument(); // clientes activos (is_active !== false)
  });

  it('dado alertaCartera en true cuando renderiza entonces muestra el porcentaje del limite', () => {
    renderVentasTab({ carteraVencida: 2000, limiteCartera: 5000, alertaCartera: true });
    expect(screen.getByText('40% del límite')).toBeInTheDocument();
  });

  it('dado click en una barra del funnel cuando el payload trae key entonces llama setModalEstadoPedido', async () => {
    const { props } = renderVentasTab();
    await userEvent.click(screen.getByText('bar-total-0'));
    expect(props.setModalEstadoPedido).toHaveBeenCalledWith('pendiente');
  });

  it('dado click en una barra de ventas por vendedor cuando el payload trae fullName entonces llama setModalVendedor', async () => {
    const { props } = renderVentasTab();
    // Dos <Bar dataKey="value"> en la página (Ventas por Vendedor y Top Clientes),
    // ambos con data-testid="bar-value" en el orden en que aparecen en el JSX.
    const barrasValue = screen.getAllByTestId('bar-value');
    await userEvent.click(within(barrasValue[0]).getByText('bar-value-0'));
    expect(props.setModalVendedor).toHaveBeenCalledWith('Juan Pérez');
    expect(props.setModalClienteCompras).not.toHaveBeenCalled();
  });

  it('dado click en una barra de top clientes cuando el payload trae fullName entonces llama setModalClienteCompras', async () => {
    const { props } = renderVentasTab();
    const barrasValue = screen.getAllByTestId('bar-value');
    await userEvent.click(within(barrasValue[1]).getByText('bar-value-0'));
    expect(props.setModalClienteCompras).toHaveBeenCalledWith('Cliente A SA');
    expect(props.setModalVendedor).not.toHaveBeenCalled();
  });

  it('dado click en una barra de deudores cuando el payload trae fullName entonces llama setModalClienteDeudor', async () => {
    const { props } = renderVentasTab();
    await userEvent.click(screen.getByText('bar-deuda-0'));
    expect(props.setModalClienteDeudor).toHaveBeenCalledWith('Deudor A SA');
  });

  it('dado distribucionPago vacia cuando renderiza entonces oculta el grafico y muestra Sin pedidos', () => {
    renderVentasTab({ distribucionPago: [] });
    expect(screen.getByText('Sin pedidos')).toBeInTheDocument();
  });

  it('dado topDeudores vacio cuando renderiza entonces muestra el fallback Sin deudores', () => {
    renderVentasTab({ topDeudores: [] });
    expect(screen.getByText('Sin deudores')).toBeInTheDocument();
  });

  it('dado click en los botones de exportar cuando se activan entonces llaman a sus props', async () => {
    const { props } = renderVentasTab();
    await userEvent.click(screen.getByRole('button', { name: /Reporte de Ventas/i }));
    await userEvent.click(screen.getByRole('button', { name: /Top Clientes/i }));
    await userEvent.click(screen.getByRole('button', { name: /Cartera Deudores/i }));
    expect(props.exportVentas).toHaveBeenCalledTimes(1);
    expect(props.exportTopClientes).toHaveBeenCalledTimes(1);
    expect(props.exportDeudores).toHaveBeenCalledTimes(1);
  });

  it('dado cambio en las fechas de reporte cuando se editan entonces llama setReportFechas', async () => {
    const { props, container } = renderVentasTab();
    const fechas = container.querySelectorAll('input[type="date"]');
    fechas[0].dispatchEvent(new Event('focus', { bubbles: true }));
    await userEvent.type(fechas[0] as HTMLInputElement, '2026-01-01');
    expect(props.setReportFechas).toHaveBeenCalled();
  });

  it('dado modalEstadoPedido no nulo cuando renderiza entonces monta PedidosEstadoModal abierto', () => {
    renderVentasTab({
      modalEstadoPedido: 'pendiente',
      pedidos: [{ id: 1, estado: 'pendiente', cliente_nombre: 'Cliente X' } as any],
    });
    expect(screen.getByText(/Pedidos en Estado:/i)).toBeInTheDocument();
  });

  it('dado PedidosEstadoModal abierto cuando se cierra entonces llama setModalEstadoPedido con null', async () => {
    const { props } = renderVentasTab({ modalEstadoPedido: 'pendiente' });
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(props.setModalEstadoPedido).toHaveBeenCalledWith(null);
  });

  it('dado modalVendedor no nulo cuando se cierra entonces llama setModalVendedor con null', async () => {
    const { props } = renderVentasTab({ modalVendedor: 'Juan Pérez' });
    expect(screen.getByText(/Ventas del Vendedor:/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(props.setModalVendedor).toHaveBeenCalledWith(null);
  });

  it('dado modalClienteCompras no nulo cuando se cierra entonces llama setModalClienteCompras con null', async () => {
    const { props } = renderVentasTab({ modalClienteCompras: 'Cliente A SA' });
    expect(screen.getByText(/Historial de Compras:/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(props.setModalClienteCompras).toHaveBeenCalledWith(null);
  });

  it('dado modalClienteDeudor no nulo cuando se cierra entonces llama setModalClienteDeudor con null', async () => {
    const { props } = renderVentasTab({
      modalClienteDeudor: 'Deudor A SA',
      topDeudores: [{ name: 'Deudor A', fullName: 'Deudor A SA', deuda: 300, obj: { nombre_razon_social: 'Deudor A SA', saldo_pendiente: 300 } as any }],
    });
    expect(screen.getByText('Perfil de Riesgo Financiero')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /cerrar/i }));
    expect(props.setModalClienteDeudor).toHaveBeenCalledWith(null);
  });
});
