/**
 * RUP — Componente: EjecutivosDashboard
 * ======================================
 * Artefacto   : Diseño de Interfaz de Usuario / Vista
 * Patrón      : Container/Presentational — este componente es el contenedor
 *               de estado; los tabs son unidades de presentación independientes.
 * Principios  : SRP — cada tab tiene responsabilidad única de presentación.
 *               OCP — nuevos tabs se agregan sin modificar los existentes.
 *
 * Casos de Uso cubiertos:
 *   CU-EJ-01 Ver Resumen Ejecutivo (KPIs consolidados)
 *   CU-EJ-02 Ver Resumen de Producción (estado OPs, tendencia kg)
 *   CU-EJ-03 Ver Tendencia de Producción (serie temporal 30d)
 *   CU-EJ-04 Ver Planificación MRP (sugerencias y requerimientos)
 *   CU-EJ-05 Ver Inventario y Alertas de Stock
 *   CU-EJ-06 Ver Ventas, Cobranza y Exportar Reportes
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import {
  Package,
  Warehouse,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  TrendingUp,
  Activity,
  Search,
  Users,
  ShoppingBag,
  DollarSign,
  FileSpreadsheet,
  Download,
  Factory,
  ShoppingCart,
  CheckCircle2,
  Clock,
  AlertCircle,
  TrendingDown,
  Layers,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
  Area,
  AreaChart,
} from 'recharts';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { useAuth } from '../../lib/auth';
import type { Cliente, PedidoVenta, Sede, OrdenCompraSugerida, RequerimientoMaterial } from '../../lib/types';
import { MRPDashboard } from '../shared/MRPDashboard';

// ---------------------------------------------------------------------------
// Tipos locales
// ---------------------------------------------------------------------------

interface AlertaStock {
  producto: string;
  producto_codigo: string;
  bodega: string;
  stock_actual: string;
  stock_minimo: string;
  faltante?: number;
}

interface StockItem {
  id: number;
  producto: string;
  bodega: string;
  lote: string | null;
  cantidad: string;
}

interface KpiEjecutivo {
  produccion: {
    ops_pendiente: number;
    ops_en_proceso: number;
    ops_finalizada: number;
    kg_hoy: number;
    kg_semana: number;
    kg_mes: number;
    tiempo_promedio_lote_min: number;
  };
  mrp: {
    ocs_pendientes: number;
    ocs_aprobadas: number;
    ocs_rechazadas: number;
    productos_en_deficit: number;
  };
  stock: { productos_bajo_minimo: number };
  cartera: {
    cuentas_por_cobrar: number;
    cartera_vencida: number;
    pedidos_pendientes: number;
    pedidos_despachados: number;
  };
}

interface OpsEstadoItem {
  estado: string;
  value: number;
  fill: string;
}

interface ProduccionResumen {
  ops_por_estado: OpsEstadoItem[];
  kg_hoy: number;
  kg_semana: number;
  kg_mes: number;
  tiempo_promedio_lote_min: number;
}

interface TendenciaDia {
  fecha: string;
  kg: number;
}

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const REFRESH_INTERVAL_MS = 60_000;

const COLORS = [
  '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
  '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
  '#469990', '#dcbeff', '#9A6324', '#800000', '#aaffc3',
];

// ---------------------------------------------------------------------------
// Utilidades puras (sin efectos secundarios)
// ---------------------------------------------------------------------------

const fmt = (n: number, dec = 2) =>
  n.toLocaleString('es-EC', { minimumFractionDigits: dec, maximumFractionDigits: dec });

const abreviar = (s: string, max = 20) =>
  s.length <= max ? s : s.slice(0, max - 1) + '…';

const toNum = (v: unknown): number => {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return parseFloat(v) || 0;
  return 0;
};

const toArray = <T,>(d: unknown): T[] =>
  Array.isArray(d) ? d : ((d as { results?: T[] })?.results ?? []);

const descargarBlob = (blob: Blob, nombre: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

// ---------------------------------------------------------------------------
// Sub-componente: KPI Card reutilizable
// ---------------------------------------------------------------------------

interface KpiCardProps {
  titulo: string;
  valor: string | number;
  subtitulo?: string;
  icon: React.ReactNode;
  alerta?: boolean;
  alertaTexto?: string;
}

function KpiCard({ titulo, valor, subtitulo, icon, alerta, alertaTexto }: KpiCardProps) {
  return (
    <Card className={`overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1 ${alerta ? 'border-red-300 bg-red-50/90' : 'bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-slate-200/60'}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
        <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{titulo}</CardTitle>
        <div className={`p-2 rounded-full ${alerta ? 'bg-red-100 text-red-600' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'}`}>{icon}</div>
      </CardHeader>
      <CardContent className="relative z-10">
        <div className={`text-3xl font-extrabold tracking-tight ${alerta ? 'text-red-600' : 'text-slate-800 dark:text-slate-100'}`}>{valor}</div>
        {subtitulo && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitulo}</p>
        )}
        {alerta && alertaTexto && (
          <p className="text-xs text-red-500 font-semibold mt-2 flex items-center gap-1.5 bg-red-100/50 p-1.5 rounded-md w-fit">
            <AlertTriangle className="w-3.5 h-3.5" />
            {alertaTexto}
          </p>
        )}
        {/* Decorative background gradient */}
        {!alerta && (
          <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-full blur-2xl -z-10 opacity-60" />
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export function EjecutivosDashboard() {
  const { profile } = useAuth();

  // --- Estado global ---
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [filtroSedeId, setFiltroSedeId] = useState<string>('');
  const [activeTab, setActiveTab] = useState('resumen');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [descargando, setDescargando] = useState<string | null>(null);

  // --- Datos de cada tab ---
  const [kpiEjecutivo, setKpiEjecutivo] = useState<KpiEjecutivo | null>(null);
  const [produccionResumen, setProduccionResumen] = useState<ProduccionResumen | null>(null);
  const [tendencia, setTendencia] = useState<TendenciaDia[]>([]);
  const [alertas, setAlertas] = useState<AlertaStock[]>([]);
  const [stock, setStock] = useState<StockItem[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
  const [busquedaAlertas, setBusquedaAlertas] = useState('');
  const [reportFechas, setReportFechas] = useState({
    inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    fin: new Date().toISOString().split('T')[0],
  });

  // ---------------------------------------------------------------------------
  // Fetch
  // ---------------------------------------------------------------------------

  const fetchSedes = useCallback(async () => {
    try {
      const res = await apiClient.get<Sede[]>('/sedes/');
      setSedes(toArray(res.data));
    } catch {
      setSedes([]);
    }
  }, []);

  const fetchData = useCallback(async (showToast = false) => {
    if (showToast) setRefreshing(true);
    else setLoading(true);

    const params = filtroSedeId ? { sede_id: filtroSedeId } : {};

    try {
      const [
        kpiRes,
        prodRes,
        tendRes,
        alertasRes,
        stockRes,
        clientesRes,
        pedidosRes,
      ] = await Promise.all([
        apiClient.get<KpiEjecutivo>('/kpi-ejecutivo/', { params }),
        apiClient.get<ProduccionResumen>('/produccion/resumen/', { params }),
        apiClient.get<TendenciaDia[]>('/produccion/tendencia/', { params }),
        apiClient.get<AlertaStock[]>('/inventory/alertas-stock/', { params }),
        apiClient.get<StockItem[]>('/inventory/stock/', { params }),
        apiClient.get<Cliente[]>('/clientes/', { params }).catch(() => ({ data: [] })),
        apiClient.get<PedidoVenta[]>('/pedidos-venta/', { params: { ...params, limit: 200 } }).catch(() => ({ data: [] })),
      ]);

      setKpiEjecutivo(kpiRes.data);
      setProduccionResumen(prodRes.data);
      setTendencia(toArray(tendRes.data));
      setAlertas(toArray(alertasRes.data));
      setStock(toArray(stockRes.data));
      setClientes(toArray(clientesRes.data));
      setPedidos(toArray(pedidosRes.data));

      if (showToast) toast.success('Datos actualizados');
    } catch (err) {
      console.error('Error cargando dashboard ejecutivo:', err);
      toast.error('Error al cargar los datos del dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filtroSedeId]);

  useEffect(() => { fetchSedes(); }, [fetchSedes]);
  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => fetchData(), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [autoRefresh, fetchData]);

  // ---------------------------------------------------------------------------
  // Cálculos derivados — Ventas
  // ---------------------------------------------------------------------------

  const getPedidoTotal = (p: PedidoVenta) =>
    toNum(p.total) || (p.detalles?.reduce(
      (s: number, d: any) => s + toNum(d.peso) * toNum(d.precio_unitario), 0
    ) ?? 0);

  const ventasPorVendedor = useMemo(() => {
    const map = new Map<string, number>();
    pedidos.forEach((p) => {
      const v = (p as any).vendedor_nombre || 'Sin asignar';
      map.set(v, (map.get(v) ?? 0) + getPedidoTotal(p));
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name: abreviar(name, 18), value: Math.round(value * 100) / 100 }))
      .sort((a, b) => b.value - a.value).slice(0, 10);
  }, [pedidos]);

  const topClientesGerencial = useMemo(() => {
    const map = new Map<string, number>();
    pedidos.forEach((p) => {
      const c = (p as any).cliente_nombre || 'Sin nombre';
      map.set(c, (map.get(c) ?? 0) + getPedidoTotal(p));
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name: abreviar(name), value: Math.round(value * 100) / 100 }))
      .sort((a, b) => b.value - a.value).slice(0, 8);
  }, [pedidos]);

  const topDeudores = useMemo(() =>
    clientes
      .map(c => ({ name: abreviar(c.nombre_razon_social), deuda: toNum(c.saldo_pendiente) }))
      .filter(c => c.deuda > 0)
      .sort((a, b) => b.deuda - a.deuda).slice(0, 8),
    [clientes]);

  const distribucionPago = useMemo(() => {
    let pagado = 0, pendiente = 0;
    pedidos.forEach((p) => {
      const t = getPedidoTotal(p);
      if (p.esta_pagado) pagado += t; else pendiente += t;
    });
    return [
      { name: 'Pagado', value: Math.round(pagado * 100) / 100, color: '#10b981' },
      { name: 'Pendiente', value: Math.round(pendiente * 100) / 100, color: '#f59e0b' },
    ].filter(d => d.value > 0);
  }, [pedidos]);

  const stockPorBodega = useMemo(() => {
    const map = new Map<string, number>();
    stock.forEach(s => map.set(s.bodega, (map.get(s.bodega) ?? 0) + toNum(s.cantidad)));
    return Array.from(map.entries())
      .map(([name, value]) => ({ name: abreviar(name, 16), value: Math.round(value * 100) / 100 }))
      .filter(d => d.value > 0).sort((a, b) => b.value - a.value);
  }, [stock]);

  const alertasFiltradas = useMemo(() => {
    if (!busquedaAlertas.trim()) return alertas;
    const q = busquedaAlertas.trim().toLowerCase();
    return alertas.filter(a =>
      a.producto_codigo?.toLowerCase().includes(q) || a.producto?.toLowerCase().includes(q)
    );
  }, [alertas, busquedaAlertas]);

  const topAlertas = useMemo(() =>
    [...alertasFiltradas]
      .sort((a, b) => (b.faltante ?? 0) - (a.faltante ?? 0)).slice(0, 8)
      .map(a => ({ name: a.producto_codigo || abreviar(a.producto, 15), faltante: a.faltante ?? 0 })),
    [alertasFiltradas]);

  const totalVentas = useMemo(() => pedidos.reduce((a, p) => a + getPedidoTotal(p), 0), [pedidos]);
  const cuentasPorCobrar = useMemo(() => clientes.reduce((a, c) => a + toNum(c.saldo_pendiente), 0), [clientes]);
  const carteraVencida = useMemo(() => clientes.reduce((a, c) => a + toNum((c as any).cartera_vencida), 0), [clientes]);
  const limiteCartera = useMemo(() => clientes.reduce((a, c) => a + toNum((c as any).limite_credito), 0), [clientes]);

  // ---------------------------------------------------------------------------
  // Exportar Excel
  // ---------------------------------------------------------------------------

  const exportar = async (ruta: string, params: Record<string, string>, nombre: string) => {
    if (params.fecha_inicio && params.fecha_fin && params.fecha_inicio > params.fecha_fin) {
      toast.error('La fecha de inicio no puede ser posterior a la fecha de fin');
      return;
    }
    if (descargando) return;
    setDescargando(ruta);
    try {
      const res = await apiClient.get(`/reporting/${ruta}`, { params: { ...params, format: 'xlsx' }, responseType: 'blob' });
      descargarBlob(new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), nombre);
      toast.success('Reporte descargado');
    } catch {
      toast.error('Error al descargar el reporte');
    } finally {
      setDescargando(null);
    }
  };

  const exportVentas = () => exportar(
    'gerencial/ventas',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...(filtroSedeId && { sede_id: filtroSedeId }) },
    `ventas_gerencial_${reportFechas.inicio}.xlsx`
  );
  const exportTopClientes = () => exportar(
    'gerencial/top-clientes',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...(filtroSedeId && { sede_id: filtroSedeId }) },
    `top_clientes_${reportFechas.inicio}.xlsx`
  );
  const exportDeudores = () => exportar(
    'gerencial/deudores',
    { ...(filtroSedeId && { sede_id: filtroSedeId }) },
    'clientes_deudores.xlsx'
  );
  const exportOrdenes = () => exportar(
    'produccion/ordenes',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...(filtroSedeId && { sede_id: filtroSedeId }) },
    `ordenes_produccion_${reportFechas.inicio}.xlsx`
  );
  const exportLotes = () => exportar(
    'produccion/lotes',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...(filtroSedeId && { sede_id: filtroSedeId }) },
    `lotes_produccion_${reportFechas.inicio}.xlsx`
  );
  const exportTendencia = () => exportar(
    'produccion/tendencia',
    { fecha_inicio: reportFechas.inicio, fecha_fin: reportFechas.fin, ...(filtroSedeId && { sede_id: filtroSedeId }) },
    `tendencia_produccion_${reportFechas.inicio}.xlsx`
  );

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      </div>
    );
  }

  const kp = kpiEjecutivo;
  const pr = produccionResumen;

  // Semáforo: cartera vencida supera el 40% del límite de crédito total
  const alertaCartera = limiteCartera > 0 && carteraVencida / limiteCartera > 0.4;

  // ---------------------------------------------------------------------------
  // JSX
  // ---------------------------------------------------------------------------

  return (
    <div className="p-4 md:p-6 space-y-6 bg-slate-50/50 dark:bg-slate-950/50 min-h-screen">
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Panel Ejecutivo
          </h1>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mt-1">
            Vista gerencial consolidada — Hola, <span className="text-slate-700 dark:text-slate-300">{profile?.user?.username}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Selector de sede */}
          <Select value={filtroSedeId} onValueChange={setFiltroSedeId}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Todas las sedes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todas las sedes</SelectItem>
              {sedes.map(s => (
                <SelectItem key={s.id} value={String(s.id)}>{s.nombre}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="gap-1"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>

          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(v => !v)}
            className="gap-1"
          >
            <Activity className="w-4 h-4" />
            Auto
          </Button>
        </div>
      </div>

      {/* ── Tabs principales ── */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="resumen" className="gap-1"><BarChart3 className="w-4 h-4" />Resumen</TabsTrigger>
          <TabsTrigger value="produccion" className="gap-1"><Factory className="w-4 h-4" />Producción</TabsTrigger>
          <TabsTrigger value="mrp" className="gap-1"><Layers className="w-4 h-4" />MRP</TabsTrigger>
          <TabsTrigger value="stock" className="gap-1"><Warehouse className="w-4 h-4" />Stock</TabsTrigger>
          <TabsTrigger value="ventas" className="gap-1"><TrendingUp className="w-4 h-4" />Ventas</TabsTrigger>
          <TabsTrigger value="reportes" className="gap-1"><FileSpreadsheet className="w-4 h-4" />Reportes</TabsTrigger>
        </TabsList>

        {/* ════════════════════════════════════════════════════════════
            TAB 1: RESUMEN EJECUTIVO — CU-EJ-01
        ════════════════════════════════════════════════════════════ */}
        <TabsContent value="resumen" className="space-y-6 mt-4">
          <p className="text-sm text-muted-foreground">
            Semáforo de salud de planta — indicadores clave de todas las áreas.
          </p>

          {/* Producción */}
          <div>
            <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
              <Factory className="w-4 h-4 text-blue-500" /> Producción
            </h2>
            <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
              <KpiCard titulo="OPs en Proceso" valor={kp?.produccion.ops_en_proceso ?? '—'} icon={<Activity className="w-4 h-4" />} subtitulo="Órdenes activas ahora" />
              <KpiCard titulo="OPs Pendientes" valor={kp?.produccion.ops_pendiente ?? '—'} icon={<Clock className="w-4 h-4" />} subtitulo="Por iniciar" />
              <KpiCard titulo="kg Hoy" valor={kp ? fmt(kp.produccion.kg_hoy, 1) : '—'} icon={<TrendingUp className="w-4 h-4" />} subtitulo="Producido hoy" />
              <KpiCard titulo="kg Este Mes" valor={kp ? fmt(kp.produccion.kg_mes, 1) : '—'} icon={<BarChart3 className="w-4 h-4" />} subtitulo="Acumulado mensual" />
            </div>
          </div>

          {/* MRP / Compras */}
          <div>
            <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
              <ShoppingCart className="w-4 h-4 text-orange-500" /> MRP & Abastecimiento
            </h2>
            <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
              <KpiCard
                titulo="OCS Pendientes"
                valor={kp?.mrp.ocs_pendientes ?? '—'}
                icon={<ShoppingCart className="w-4 h-4" />}
                subtitulo="Órdenes de compra por aprobar"
                alerta={(kp?.mrp.ocs_pendientes ?? 0) > 0}
                alertaTexto="Requieren decisión del ejecutivo"
              />
              <KpiCard titulo="Productos en Déficit" valor={kp?.mrp.productos_en_deficit ?? '—'} icon={<AlertTriangle className="w-4 h-4" />} subtitulo="Con stock insuficiente" />
              <KpiCard titulo="OCS Aprobadas" valor={kp?.mrp.ocs_aprobadas ?? '—'} icon={<CheckCircle2 className="w-4 h-4" />} subtitulo="Órdenes aprobadas" />
              <KpiCard titulo="Alertas Stock" valor={kp?.stock.productos_bajo_minimo ?? '—'} icon={<Package className="w-4 h-4" />} subtitulo="Productos bajo mínimo" />
            </div>
          </div>

          {/* Cartera */}
          <div>
            <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-green-600" /> Cartera & Ventas
            </h2>
            <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
              <KpiCard titulo="Cuentas por Cobrar" valor={`$${fmt(cuentasPorCobrar)}`} icon={<DollarSign className="w-4 h-4" />} subtitulo="Saldo pendiente total" />
              <KpiCard
                titulo="Cartera Vencida"
                valor={`$${fmt(carteraVencida)}`}
                icon={<TrendingDown className="w-4 h-4" />}
                subtitulo={alertaCartera ? `${fmt((carteraVencida / limiteCartera) * 100, 0)}% del límite de crédito` : 'Sin alerta de riesgo'}
                alerta={alertaCartera}
                alertaTexto="Supera el 40% del límite de crédito"
              />
              <KpiCard titulo="Pedidos Pendientes" valor={kp?.cartera.pedidos_pendientes ?? '—'} icon={<ShoppingBag className="w-4 h-4" />} subtitulo="Por despachar" />
              <KpiCard titulo="Pedidos Despachados" valor={kp?.cartera.pedidos_despachados ?? '—'} icon={<CheckCircle2 className="w-4 h-4" />} subtitulo="Entregados" />
            </div>
          </div>
        </TabsContent>

        {/* ════════════════════════════════════════════════════════════
            TAB 2: PRODUCCIÓN — CU-EJ-02, CU-EJ-03
        ════════════════════════════════════════════════════════════ */}
        <TabsContent value="produccion" className="space-y-6 mt-4">
          {/* KPIs de producción */}
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
            <KpiCard titulo="kg Hoy" valor={pr ? fmt(pr.kg_hoy, 1) : '—'} icon={<TrendingUp className="w-4 h-4" />} subtitulo="Producido hoy" />
            <KpiCard titulo="kg Semana" valor={pr ? fmt(pr.kg_semana, 1) : '—'} icon={<BarChart3 className="w-4 h-4" />} subtitulo="Últimos 7 días" />
            <KpiCard titulo="kg Mes" valor={pr ? fmt(pr.kg_mes, 1) : '—'} icon={<Activity className="w-4 h-4" />} subtitulo="Mes en curso" />
            <KpiCard titulo="Tiempo Prom./Lote" valor={pr ? `${fmt(pr.tiempo_promedio_lote_min, 0)} min` : '—'} icon={<Clock className="w-4 h-4" />} subtitulo="Promedio por lote" />
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Donut: Estado de OPs */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Factory className="w-4 h-4 text-blue-500" />
                  Estado de Órdenes de Producción
                </CardTitle>
                <CardDescription>Distribución actual por estado</CardDescription>
              </CardHeader>
              <CardContent>
                {pr && pr.ops_por_estado.some(o => o.value > 0) ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={pr.ops_por_estado}
                        dataKey="value"
                        nameKey="estado"
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        label={({ estado, value }) => value > 0 ? `${estado}: ${value}` : ''}
                      >
                        {pr.ops_por_estado.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => [v, 'OPs']} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground">
                    Sin órdenes de producción
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Line chart: Tendencia 30 días */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-green-500" />
                  Tendencia de Producción — 30 días
                </CardTitle>
                <CardDescription>kg producidos por día</CardDescription>
              </CardHeader>
              <CardContent>
                {tendencia.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={tendencia} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                      <defs>
                        <linearGradient id="gradKg" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="fecha"
                        tick={{ fontSize: 10 }}
                        tickFormatter={v => v.slice(5)} /* MM-DD */
                        interval={4}
                      />
                      <YAxis tick={{ fontSize: 10 }} width={50} />
                      <Tooltip
                        formatter={(v: number) => [`${fmt(v, 1)} kg`, 'Producción']}
                        labelFormatter={l => `Fecha: ${l}`}
                      />
                      <Area type="monotone" dataKey="kg" stroke="#3b82f6" fill="url(#gradKg)" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground">
                    Sin datos de tendencia
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Exportes de producción */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4" /> Exportar Reportes de Producción
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-4">
                <div>
                  <Label className="text-xs">Fecha inicio</Label>
                  <Input type="date" className="w-36" value={reportFechas.inicio}
                    onChange={e => setReportFechas(p => ({ ...p, inicio: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Fecha fin</Label>
                  <Input type="date" className="w-36" value={reportFechas.fin}
                    onChange={e => setReportFechas(p => ({ ...p, fin: e.target.value }))} />
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" className="gap-1" onClick={exportOrdenes}>
                  <Download className="w-4 h-4" /> Órdenes de Producción
                </Button>
                <Button variant="outline" size="sm" className="gap-1" onClick={exportLotes}>
                  <Download className="w-4 h-4" /> Lotes de Producción
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ════════════════════════════════════════════════════════════
            TAB 3: MRP — CU-EJ-04
            Reutiliza MRPDashboard existente (OCP — sin modificar el componente)
        ════════════════════════════════════════════════════════════ */}
        <TabsContent value="mrp" className="mt-4">
          {/* KPIs rápidos del MRP para contexto ejecutivo */}
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4 mb-6">
            <KpiCard
              titulo="OCS Pendientes"
              valor={kp?.mrp.ocs_pendientes ?? '—'}
              icon={<ShoppingCart className="w-4 h-4" />}
              alerta={(kp?.mrp.ocs_pendientes ?? 0) > 0}
              alertaTexto="Pendientes de aprobación"
            />
            <KpiCard titulo="Productos en Déficit" valor={kp?.mrp.productos_en_deficit ?? '—'} icon={<AlertTriangle className="w-4 h-4" />} />
            <KpiCard titulo="OCS Aprobadas" valor={kp?.mrp.ocs_aprobadas ?? '—'} icon={<CheckCircle2 className="w-4 h-4" />} />
            <KpiCard titulo="OCS Rechazadas" valor={kp?.mrp.ocs_rechazadas ?? '—'} icon={<AlertCircle className="w-4 h-4" />} />
          </div>
          <MRPDashboard />
        </TabsContent>

        {/* ════════════════════════════════════════════════════════════
            TAB 4: STOCK — CU-EJ-05
        ════════════════════════════════════════════════════════════ */}
        <TabsContent value="stock" className="space-y-6 mt-4">
          {/* KPIs */}
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
            <KpiCard titulo="Productos" valor={alertas.length > 0 ? alertas.length : stock.length} icon={<Package className="w-4 h-4" />} subtitulo="Total en catálogo" />
            <KpiCard titulo="Bodegas" valor={Array.from(new Set(stock.map(s => s.bodega))).length} icon={<Warehouse className="w-4 h-4" />} subtitulo="Activas" />
            <KpiCard titulo="Stock Total" valor={fmt(stock.reduce((a, s) => a + toNum(s.cantidad), 0), 1)} icon={<Layers className="w-4 h-4" />} subtitulo="Unidades en sistema" />
            <KpiCard
              titulo="Alertas de Stock"
              valor={alertas.length}
              icon={<AlertTriangle className="w-4 h-4" />}
              alerta={alertas.length > 0}
              alertaTexto="Productos bajo mínimo"
            />
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Bar: stock por bodega */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Stock por Bodega</CardTitle>
                <CardDescription>Distribución actual de inventario</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={stockPorBodega} margin={{ top: 5, right: 10, left: 0, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip formatter={(v: number) => [fmt(v, 1), 'Stock']} />
                    <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                      {stockPorBodega.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Horizontal bar: top alertas */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-500" /> Top Alertas por Faltante
                </CardTitle>
                <CardDescription>Productos con mayor déficit de stock</CardDescription>
              </CardHeader>
              <CardContent>
                {topAlertas.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={topAlertas} layout="vertical" margin={{ left: 10, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tick={{ fontSize: 10 }} />
                      <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={80} />
                      <Tooltip formatter={(v: number) => [fmt(v, 1), 'Faltante']} />
                      <Bar dataKey="faltante" fill="#ef4444" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground">
                    <CheckCircle2 className="w-8 h-8 text-green-400 mr-2" /> Sin alertas críticas
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Tabla de alertas */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  Alertas de Stock Bajo
                </CardTitle>
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar producto…"
                    className="pl-8 w-52"
                    value={busquedaAlertas}
                    onChange={e => setBusquedaAlertas(e.target.value)}
                  />
                </div>
              </div>
              <CardDescription>
                {alertasFiltradas.length} de {alertas.length} productos con stock bajo mínimo
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="max-h-80 overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Código</TableHead>
                      <TableHead>Producto</TableHead>
                      <TableHead>Bodega</TableHead>
                      <TableHead className="text-right">Actual</TableHead>
                      <TableHead className="text-right">Mínimo</TableHead>
                      <TableHead className="text-right">Faltante</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {alertasFiltradas.map((a, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-mono text-xs">{a.producto_codigo}</TableCell>
                        <TableCell>{a.producto}</TableCell>
                        <TableCell className="text-xs">{a.bodega}</TableCell>
                        <TableCell className="text-right">{fmt(toNum(a.stock_actual), 1)}</TableCell>
                        <TableCell className="text-right">{fmt(toNum(a.stock_minimo), 1)}</TableCell>
                        <TableCell className="text-right font-bold text-red-600">
                          {a.faltante !== undefined ? fmt(a.faltante, 1) : '—'}
                        </TableCell>
                        <TableCell>
                          <Badge variant="destructive" className="text-xs">Bajo mínimo</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                    {alertasFiltradas.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                          Sin resultados
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ════════════════════════════════════════════════════════════
            TAB 5: VENTAS — CU-EJ-06
        ════════════════════════════════════════════════════════════ */}
        <TabsContent value="ventas" className="space-y-6 mt-4">
          {/* KPIs */}
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
            <KpiCard titulo="Cuentas por Cobrar" valor={`$${fmt(cuentasPorCobrar)}`} icon={<DollarSign className="w-4 h-4" />} subtitulo="Saldo pendiente total" />
            <KpiCard
              titulo="Cartera Vencida"
              valor={`$${fmt(carteraVencida)}`}
              icon={<TrendingDown className="w-4 h-4" />}
              alerta={alertaCartera}
              alertaTexto="Supera el 40% del límite de crédito"
              subtitulo={alertaCartera ? `${fmt((carteraVencida / limiteCartera) * 100, 0)}% del límite` : ''}
            />
            <KpiCard titulo="Total Ventas Período" valor={`$${fmt(totalVentas)}`} icon={<ShoppingBag className="w-4 h-4" />} subtitulo={`${pedidos.length} pedidos`} />
            <KpiCard titulo="Clientes Activos" valor={clientes.filter(c => (c as any).is_active !== false).length} icon={<Users className="w-4 h-4" />} subtitulo={`${clientes.filter(c => (c as any).tiene_beneficio).length} con beneficio`} />
          </div>

          {/* Funnel de pedidos */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Funnel de Pedidos</CardTitle>
              <CardDescription>Conversión: Pendiente → Despachado → Facturado</CardDescription>
            </CardHeader>
            <CardContent>
              {(() => {
                const counts = { pendiente: 0, despachado: 0, facturado: 0 };
                pedidos.forEach(p => { if (counts[p.estado] !== undefined) counts[p.estado]++; });
                const data = [
                  { estado: 'Pendientes', total: counts.pendiente, fill: '#f59e0b' },
                  { estado: 'Despachados', total: counts.despachado, fill: '#3b82f6' },
                  { estado: 'Facturados', total: counts.facturado, fill: '#10b981' },
                ];
                return (
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30 }}>
                      <XAxis type="number" tick={{ fontSize: 10 }} />
                      <YAxis dataKey="estado" type="category" tick={{ fontSize: 11 }} width={90} />
                      <Tooltip formatter={(v: number) => [v, 'Pedidos']} />
                      {data.map((d, i) => (
                        <Bar key={i} dataKey="total" fill={d.fill} radius={[0, 4, 4, 0]} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                );
              })()}
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Ventas por vendedor */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Ventas por Vendedor</CardTitle>
                <CardDescription>Top 10 por monto total</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={ventasPorVendedor} margin={{ top: 5, right: 10, left: 0, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-30} textAnchor="end" />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip formatter={(v: number) => [`$${fmt(v)}`, 'Ventas']} />
                    <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Estado de cobranza */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Estado de Cobranza</CardTitle>
                <CardDescription>Pagado vs Pendiente</CardDescription>
              </CardHeader>
              <CardContent>
                {distribucionPago.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie data={distribucionPago} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={95}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                        {distribucionPago.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                      <Tooltip formatter={(v: number) => [`$${fmt(v)}`, '']} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground">Sin pedidos</div>
                )}
              </CardContent>
            </Card>

            {/* Top clientes por monto */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Clientes por Compras</CardTitle>
                <CardDescription>Top 8 por monto total</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={topClientesGerencial} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tick={{ fontSize: 10 }} />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={90} />
                    <Tooltip formatter={(v: number) => [`$${fmt(v)}`, 'Compras']} />
                    <Bar dataKey="value" fill="#10b981" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Top deudores */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-500" /> Top Clientes Deudores
                </CardTitle>
                <CardDescription>Top 8 por saldo pendiente</CardDescription>
              </CardHeader>
              <CardContent>
                {topDeudores.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={topDeudores} layout="vertical" margin={{ left: 10, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tick={{ fontSize: 10 }} />
                      <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={90} />
                      <Tooltip formatter={(v: number) => [`$${fmt(v)}`, 'Deuda']} />
                      <Bar dataKey="deuda" fill="#ef4444" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground">
                    <CheckCircle2 className="w-8 h-8 text-green-400 mr-2" /> Sin deudores
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Exportes */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4" /> Exportar Reportes de Ventas
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-4">
                <div>
                  <Label className="text-xs">Fecha inicio</Label>
                  <Input type="date" className="w-36" value={reportFechas.inicio}
                    onChange={e => setReportFechas(p => ({ ...p, inicio: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Fecha fin</Label>
                  <Input type="date" className="w-36" value={reportFechas.fin}
                    onChange={e => setReportFechas(p => ({ ...p, fin: e.target.value }))} />
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" className="gap-1" onClick={exportVentas}>
                  <Download className="w-4 h-4" /> Reporte de Ventas
                </Button>
                <Button variant="outline" size="sm" className="gap-1" onClick={exportTopClientes}>
                  <Download className="w-4 h-4" /> Top Clientes
                </Button>
                <Button variant="outline" size="sm" className="gap-1" onClick={exportDeudores}>
                  <Download className="w-4 h-4" /> Cartera Deudores
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        {/* ════════════════════════════════════════════════════════════
            TAB 6: REPORTES DE GERENCIA — CU-EJ-07
            Centraliza todos los exports ejecutivos en un único panel.
        ════════════════════════════════════════════════════════════ */}
        <TabsContent value="reportes" className="space-y-6 mt-4">
          <p className="text-sm text-muted-foreground">
            Centro de reportes gerenciales — descarga los reportes Excel del período seleccionado.
          </p>

          {/* Selector de rango de fechas compartido */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-blue-500" /> Rango del Período
              </CardTitle>
              <CardDescription>Aplica a todos los reportes con filtro de fecha</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4 items-end">
                <div>
                  <Label className="text-xs">Fecha inicio</Label>
                  <Input
                    type="date"
                    className="w-36"
                    value={reportFechas.inicio}
                    onChange={e => setReportFechas(p => ({ ...p, inicio: e.target.value }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Fecha fin</Label>
                  <Input
                    type="date"
                    className="w-36"
                    value={reportFechas.fin}
                    onChange={e => setReportFechas(p => ({ ...p, fin: e.target.value }))}
                  />
                </div>
                <p className="text-xs text-muted-foreground pb-1">
                  Sede: <span className="font-medium">{sedes.find(s => String(s.id) === filtroSedeId)?.nombre ?? 'Todas'}</span>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* KPIs resumen para contexto */}
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
            <KpiCard
              titulo="Ventas del Período"
              valor={`$${fmt(totalVentas)}`}
              icon={<DollarSign className="w-4 h-4" />}
              subtitulo={`${pedidos.length} pedidos`}
            />
            <KpiCard
              titulo="Cartera Vencida"
              valor={`$${fmt(carteraVencida)}`}
              icon={<TrendingDown className="w-4 h-4" />}
              alerta={alertaCartera}
              alertaTexto="Supera el 40% del límite"
            />
            <KpiCard
              titulo="kg Producidos (mes)"
              valor={kp ? fmt(kp.produccion.kg_mes, 1) : '—'}
              icon={<Factory className="w-4 h-4" />}
              subtitulo="Mes en curso"
            />
            <KpiCard
              titulo="Alertas de Stock"
              valor={alertas.length}
              icon={<AlertTriangle className="w-4 h-4" />}
              alerta={alertas.length > 0}
              alertaTexto="Productos bajo mínimo"
            />
          </div>

          {/* Reportes Gerenciales de Ventas */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-green-600" /> Reportes de Ventas y Cartera
              </CardTitle>
              <CardDescription>
                Análisis de ventas, clientes y cobranza — requiere rango de fechas
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <TrendingUp className="w-4 h-4 text-blue-500" /> Ventas Gerencial
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Detalle completo de ventas del período: cliente, vendedor, producto, monto y estado de pago.
                  </p>
                  <Button variant="outline" size="sm" className="w-full gap-1 mt-2"
                    onClick={exportVentas} disabled={!!descargando}
                    data-testid="btn-export-ventas">
                    {descargando === 'gerencial/ventas'
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Download className="w-4 h-4" />} Descargar
                  </Button>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <Users className="w-4 h-4 text-purple-500" /> Top Clientes
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Ranking de clientes por monto comprado en el período. Útil para identificar cuentas clave.
                  </p>
                  <Button variant="outline" size="sm" className="w-full gap-1 mt-2"
                    onClick={exportTopClientes} disabled={!!descargando}
                    data-testid="btn-export-top-clientes">
                    {descargando === 'gerencial/top-clientes'
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Download className="w-4 h-4" />} Descargar
                  </Button>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <AlertTriangle className="w-4 h-4 text-red-500" /> Cartera Deudores
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Clientes con saldo pendiente, límite de crédito y antigüedad de cartera. Sin filtro de fecha.
                  </p>
                  <Button variant="outline" size="sm" className="w-full gap-1 mt-2"
                    onClick={exportDeudores} disabled={!!descargando}
                    data-testid="btn-export-deudores">
                    {descargando === 'gerencial/deudores'
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Download className="w-4 h-4" />} Descargar
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Reportes de Producción */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Factory className="w-4 h-4 text-blue-500" /> Reportes de Producción
              </CardTitle>
              <CardDescription>
                Órdenes, lotes y tendencia de producción por período
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <Activity className="w-4 h-4 text-blue-500" /> Órdenes de Producción
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Detalle de OPs: producto, fórmula, peso requerido vs producido, estado, operario y máquina.
                  </p>
                  <Button variant="outline" size="sm" className="w-full gap-1 mt-2"
                    onClick={exportOrdenes} disabled={!!descargando}
                    data-testid="btn-export-ordenes">
                    {descargando === 'produccion/ordenes'
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Download className="w-4 h-4" />} Descargar
                  </Button>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <Layers className="w-4 h-4 text-orange-500" /> Lotes de Producción
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Lotes producidos con peso bruto, tara, peso neto, duración por lote, turno y operario.
                  </p>
                  <Button variant="outline" size="sm" className="w-full gap-1 mt-2"
                    onClick={exportLotes} disabled={!!descargando}
                    data-testid="btn-export-lotes">
                    {descargando === 'produccion/lotes'
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Download className="w-4 h-4" />} Descargar
                  </Button>
                </div>

                <div className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <TrendingUp className="w-4 h-4 text-green-500" /> Tendencia Diaria
                  </div>
                  <p className="text-xs text-muted-foreground">
                    kg producidos por día en el rango seleccionado. Ideal para análisis de productividad.
                  </p>
                  <Button variant="outline" size="sm" className="w-full gap-1 mt-2"
                    onClick={exportTendencia} disabled={!!descargando}
                    data-testid="btn-export-tendencia">
                    {descargando === 'produccion/tendencia'
                      ? <RefreshCw className="w-4 h-4 animate-spin" />
                      : <Download className="w-4 h-4" />} Descargar
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tabla resumen de alertas de stock para referencia rápida */}
          {alertas.length > 0 && (
            <Card className="border-orange-200">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" /> Alertas de Stock Vigentes
                </CardTitle>
                <CardDescription>
                  {alertas.length} productos bajo mínimo — referencia para decisiones de abastecimiento
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="max-h-56 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Código</TableHead>
                        <TableHead>Producto</TableHead>
                        <TableHead>Bodega</TableHead>
                        <TableHead className="text-right">Actual</TableHead>
                        <TableHead className="text-right">Mínimo</TableHead>
                        <TableHead className="text-right">Faltante</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...alertas]
                        .sort((a, b) => (b.faltante ?? 0) - (a.faltante ?? 0))
                        .slice(0, 10)
                        .map((a, i) => (
                          <TableRow key={i}>
                            <TableCell className="font-mono text-xs">{a.producto_codigo}</TableCell>
                            <TableCell className="text-sm">{a.producto}</TableCell>
                            <TableCell className="text-xs text-muted-foreground">{a.bodega}</TableCell>
                            <TableCell className="text-right text-sm">{fmt(toNum(a.stock_actual), 1)}</TableCell>
                            <TableCell className="text-right text-sm">{fmt(toNum(a.stock_minimo), 1)}</TableCell>
                            <TableCell className="text-right font-bold text-red-600 text-sm">
                              {a.faltante !== undefined ? fmt(a.faltante, 1) : '—'}
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
