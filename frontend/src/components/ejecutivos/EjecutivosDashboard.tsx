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
  History,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  TrendingUp,
  Activity,
  Search,
  BarChart2,
  Users,
  ShoppingBag,
  DollarSign,
  FileSpreadsheet,
  Download,
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
} from 'recharts';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { useAuth } from '../../lib/auth';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import type { Cliente, PedidoVenta, Sede } from '../../lib/types';

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

interface Producto {
  id: number;
  codigo: string;
  descripcion: string;
}

interface Bodega {
  id: number;
  nombre: string;
}

interface LoteProduccion {
  id: number;
  codigo_lote: string;
}

const REFRESH_INTERVAL_MS = 60000; // 1 minuto
const COLORS = [
  '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6',
  '#bfef45', '#fabed4', '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3',
  '#808000', '#ffd8b1', '#000075', '#a9a9a9'
];

const abreviarBodega = (nombre: string, maxLen = 16) => {
  if (nombre.length <= maxLen) return nombre;
  return nombre.slice(0, maxLen - 1) + '…';
};

const formatoMoneda = (valor: number, decimals = 2) =>
  valor.toLocaleString('es-EC', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

export function EjecutivosDashboard() {
  const { profile } = useAuth();
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [filtroSedeId, setFiltroSedeId] = useState<string>(''); // '' = todas
  const [productos, setProductos] = useState<Producto[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [lotes, setLotes] = useState<LoteProduccion[]>([]);
  const [alertas, setAlertas] = useState<AlertaStock[]>([]);
  const [stock, setStock] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [busquedaAlertas, setBusquedaAlertas] = useState('');
  const [activeTab, setActiveTab] = useState<'stock' | 'ventas'>('stock');
  // Ventas (gerencial)
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
  const [reportFechas, setReportFechas] = useState({
    inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    fin: new Date().toISOString().split('T')[0],
  });

  const fetchSedes = useCallback(async () => {
    try {
      const res = await apiClient.get<Sede[]>('/sedes/');
      setSedes(Array.isArray(res.data) ? res.data : (res.data as any).results || []);
    } catch {
      setSedes([]);
    }
  }, []);

  const fetchData = useCallback(async (showToast = false) => {
    if (showToast) setRefreshing(true);
    else setLoading(true);

    try {
      const commonParams = filtroSedeId ? { sede_id: filtroSedeId } : {};
      const ventasParams = { limit: 100, ...commonParams };

      const [
        productosRes,
        bodegasRes,
        lotesRes,
        alertasRes,
        stockRes,
        clientesRes,
        pedidosRes,
      ] = await Promise.all([
        apiClient.get<Producto[]>('/productos/', { params: commonParams }),
        apiClient.get<Bodega[]>('/bodegas/', { params: commonParams }),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/', { params: commonParams }).catch(() => ({ data: [] })),
        apiClient.get<AlertaStock[]>('/inventory/alertas-stock/', { params: commonParams }),
        apiClient.get<StockItem[]>('/inventory/stock/', { params: commonParams }),
        apiClient.get<Cliente[]>('/clientes/', { params: commonParams }).catch(() => ({ data: [] })),
        apiClient.get<PedidoVenta[]>('/pedidos-venta/', { params: ventasParams }).catch(() => ({ data: [] })),
      ]);

      setProductos(Array.isArray(productosRes.data) ? productosRes.data : (productosRes.data as any).results || []);
      setBodegas(Array.isArray(bodegasRes.data) ? bodegasRes.data : (bodegasRes.data as any).results || []);
      setLotes(Array.isArray(lotesRes.data) ? lotesRes.data : (lotesRes.data as any).results || []);
      setAlertas(Array.isArray(alertasRes.data) ? alertasRes.data : (alertasRes.data as any).results || []);
      setStock(Array.isArray(stockRes.data) ? stockRes.data : (stockRes.data as any).results || []);
      setClientes(Array.isArray(clientesRes.data) ? clientesRes.data : (clientesRes.data as any).results || []);
      setPedidos(Array.isArray(pedidosRes.data) ? pedidosRes.data : (pedidosRes.data as any).results || []);

      if (showToast) toast.success('Datos actualizados');
    } catch (error) {
      console.error('Error cargando dashboard:', error);
      toast.error('Error al cargar los datos del dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filtroSedeId]);

  useEffect(() => {
    fetchSedes();
    fetchData();
  }, [fetchData, fetchSedes]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => fetchData(), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [autoRefresh, fetchData]);

  // Agrupar stock por bodega para gráficos (ordenado por valor desc, sin ceros)
  const stockPorBodega = React.useMemo(() => {
    const map = new Map<string, number>();
    stock.forEach((item) => {
      const actual = map.get(item.bodega) ?? 0;
      map.set(item.bodega, actual + parseFloat(item.cantidad || '0'));
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name, value: Math.round(value * 100) / 100 }))
      .filter((d) => d.value > 0)
      .sort((a, b) => b.value - a.value);
  }, [stock]);

  // Alertas filtradas por búsqueda (producto y código)
  const alertasFiltradas = React.useMemo(() => {
    if (!busquedaAlertas.trim()) return alertas;
    const q = busquedaAlertas.trim().toLowerCase();
    return alertas.filter(
      (a) =>
        (a.producto_codigo || '').toLowerCase().includes(q) ||
        (a.producto || '').toLowerCase().includes(q)
    );
  }, [alertas, busquedaAlertas]);

  // Top alertas por faltante (para gráfico) - usa alertas filtradas
  const topAlertas = React.useMemo(() => {
    return [...alertasFiltradas]
      .sort((a, b) => (b.faltante ?? 0) - (a.faltante ?? 0))
      .slice(0, 8)
      .map((a) => ({
        name: a.producto_codigo || a.producto.slice(0, 15),
        faltante: a.faltante ?? 0,
        bodega: a.bodega,
      }));
  }, [alertasFiltradas]);

  const stockTotal = React.useMemo(() => {
    return stock.reduce((acc, s) => acc + parseFloat(s.cantidad || '0'), 0);
  }, [stock]);

  const cuentasPorCobrar = useMemo(() => {
    return clientes.reduce(
      (acc, c) =>
        acc +
        (typeof c.saldo_pendiente === 'string'
          ? parseFloat(c.saldo_pendiente)
          : c.saldo_pendiente || 0),
      0
    );
  }, [clientes]);

  const carteraVencida = useMemo(() => {
    return clientes.reduce(
      (acc, c) =>
        acc + parseFloat(c.cartera_vencida?.toString() || '0'),
      0
    );
  }, [clientes]);

  const getPedidoTotal = (p: PedidoVenta) =>
    p.total ?? (p.detalles?.reduce(
      (s: number, d: { peso: number; precio_unitario: number }) =>
        s + d.peso * d.precio_unitario,
      0
    ) ?? 0);

  const totalVentasPeriodo = useMemo(() => {
    return pedidos.reduce((acc, p) => acc + getPedidoTotal(p), 0);
  }, [pedidos]);

  const ventasPorVendedor = useMemo(() => {
    const map = new Map<string, number>();
    pedidos.forEach((p) => {
      const vendedor = p.vendedor_nombre || 'Sin asignar';
      const total = map.get(vendedor) ?? 0;
      map.set(vendedor, total + getPedidoTotal(p));
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name, value: Math.round(value * 1000) / 1000 }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10);
  }, [pedidos]);

  const topClientesGerencial = useMemo(() => {
    const map = new Map<string, number>();
    pedidos.forEach((p) => {
      const cliente = p.cliente_nombre || 'Sin nombre';
      const total = map.get(cliente) ?? 0;
      map.set(cliente, total + getPedidoTotal(p));
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name: name.length > 25 ? name.slice(0, 24) + '…' : name, value: Math.round(value * 1000) / 1000 }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [pedidos]);

  const topDeudores = useMemo(() => {
    return clientes
      .map(c => ({
        name: c.nombre_razon_social.length > 25 ? c.nombre_razon_social.slice(0, 24) + '…' : c.nombre_razon_social,
        deuda: typeof c.saldo_pendiente === 'string' ? parseFloat(c.saldo_pendiente) : (c.saldo_pendiente || 0)
      }))
      .filter(c => c.deuda > 0)
      .sort((a, b) => b.deuda - a.deuda)
      .slice(0, 8);
  }, [clientes]);

  const distribucionPago = useMemo(() => {
    let pagado = 0;
    let pendiente = 0;
    pedidos.forEach((p) => {
      const total = getPedidoTotal(p);
      if (p.esta_pagado) pagado += total;
      else pendiente += total;
    });
    return [
      { name: 'Pagado', value: Math.round(pagado * 1000) / 1000, color: '#10b981' },
      { name: 'Pendiente', value: Math.round(pendiente * 1000) / 1000, color: '#f59e0b' },
    ].filter((d) => d.value > 0);
  }, [pedidos]);

  const handleExportVentasGerencial = async () => {
    try {
      const sedeParam = filtroSedeId ? `&sede_id=${filtroSedeId}` : '';
      const url = `/reporting/gerencial/ventas?fecha_inicio=${reportFechas.inicio}&fecha_fin=${reportFechas.fin}${sedeParam}&format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      const downloadName = filtroSedeId ? `ventas_gerencial_sede_${filtroSedeId}_${reportFechas.inicio}.xlsx` : `ventas_gerencial_${reportFechas.inicio}.xlsx`;
      link.download = downloadName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      toast.success('Excel descargado correctamente.');
    } catch (error: unknown) {
      const err = error as { response?: { status?: number } };
      if (err.response?.status === 404) {
        toast.error('No se encontraron datos para estos parámetros.');
      } else {
        toast.error('Error al exportar el reporte.');
      }
    }
  };

  const handleExportTopClientesGerencial = async () => {
    try {
      const sedeParam = filtroSedeId ? `&sede_id=${filtroSedeId}` : '';
      const url = `/reporting/gerencial/top-clientes?fecha_inicio=${reportFechas.inicio}&fecha_fin=${reportFechas.fin}${sedeParam}&format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      const downloadName = filtroSedeId ? `top_clientes_gerencial_sede_${filtroSedeId}_${reportFechas.inicio}.xlsx` : `top_clientes_gerencial_${reportFechas.inicio}.xlsx`;
      link.setAttribute('download', downloadName);
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
      toast.success('Excel descargado correctamente.');
    } catch {
      toast.error('Error al exportar el reporte.');
    }
  };

  const handleExportDeudoresGerencial = async () => {
    try {
      const sedeParam = filtroSedeId ? `&sede_id=${filtroSedeId}` : '';
      const url = `/reporting/gerencial/deudores?format=xlsx${sedeParam}`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', filtroSedeId ? `clientes_deudores_gerencial_sede_${filtroSedeId}.xlsx` : 'clientes_deudores_gerencial.xlsx');
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
      toast.success('Excel descargado correctamente.');
    } catch {
      toast.error('Error al exportar el reporte.');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full space-y-6 p-4">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-9 w-64 mb-2" />
            <Skeleton className="h-5 w-96" />
          </div>
        </div>
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full space-y-6 p-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Reportes Gerenciales
          </h1>
          <p className="text-muted-foreground">
            Bienvenido, {profile?.user?.first_name || profile?.user?.username}.
            Resumen de inventario en tiempo real. Actualizado: {format(new Date(), "PPp", { locale: es })}.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden lg:flex items-center gap-2 mr-2">
            <Label className="text-xs text-muted-foreground whitespace-nowrap">Sede</Label>
            <Select
              value={filtroSedeId}
              onValueChange={(v) => setFiltroSedeId(v === '__all__' ? '' : v)}
            >
              <SelectTrigger className="h-8 w-64">
                <SelectValue placeholder="Todas las sedes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Todas</SelectItem>
                {sedes.map((s) => (
                  <SelectItem key={s.id} value={s.id.toString()}>
                    {s.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Activity className="w-4 h-4 mr-1" />
            {autoRefresh ? 'Auto-actualizar ON' : 'Auto-actualizar OFF'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(true)}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'stock' | 'ventas')} className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="stock" className="gap-2">
            <BarChart2 className="w-4 h-4" /> Stock
          </TabsTrigger>
          <TabsTrigger value="ventas" className="gap-2">
            <ShoppingBag className="w-4 h-4" /> Ventas
          </TabsTrigger>
        </TabsList>

        <TabsContent value="stock" className="space-y-6 mt-0">
          {/* Dashboard Reporte Gerencia - Stock */}
          <div className="rounded-lg border bg-slate-50/50 dark:bg-slate-900/20 px-4 py-2">
            <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300">
              Dashboard de Inventario – Reporte Gerencia
            </h2>
            <p className="text-sm text-muted-foreground">
              KPIs y gráficos consolidados para la toma de decisiones.
            </p>
          </div>

          {/* KPIs Stock */}
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Productos</CardTitle>
                <Package className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{productos.length}</div>
                <p className="text-xs text-muted-foreground">en catálogo</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Bodegas</CardTitle>
                <Warehouse className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{bodegas.length}</div>
                <p className="text-xs text-muted-foreground">activas</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Lotes</CardTitle>
                <History className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{lotes.length}</div>
                <p className="text-xs text-muted-foreground">de producción</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Stock Total</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stockTotal.toLocaleString('es-EC', { minimumFractionDigits: 2 })} kg</div>
                <p className="text-xs text-muted-foreground">unidades en inventario</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Alertas Stock</CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${alertas.length > 0 ? 'text-destructive' : ''}`}>
                  {alertas.length}
                </div>
                <p className="text-xs text-muted-foreground">
                  {alertas.length === 0 ? 'sin alertas' : 'productos bajo mínimo'}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Gráficos */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Stock por Bodega
                </CardTitle>
                <CardDescription>Distribución del inventario actual</CardDescription>
              </CardHeader>
              <CardContent>
                {stockPorBodega.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={stockPorBodega} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip formatter={(v: number) => [v.toLocaleString('es-EC'), 'Stock']} />
                      <Bar dataKey="value" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Stock" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    No hay datos de stock
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-destructive" />
                  Top Alertas por Faltante
                </CardTitle>
                <CardDescription>Productos con mayor déficit vs stock mínimo</CardDescription>
              </CardHeader>
              <CardContent>
                {topAlertas.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart
                      data={topAlertas}
                      layout="vertical"
                      margin={{ top: 10, right: 30, left: 60, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis type="number" tick={{ fontSize: 12 }} />
                      <YAxis type="category" dataKey="name" width={55} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => [v.toLocaleString('es-EC'), 'Faltante']} />
                      <Bar dataKey="faltante" fill="#ef4444" radius={[0, 4, 4, 0]} name="Faltante" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    No hay alertas de stock
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Distribución % por Bodega */}
          {stockPorBodega.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Distribución % por Bodega</CardTitle>
                <CardDescription>Proporción del inventario por ubicación</CardDescription>
              </CardHeader>
              <CardContent className="min-h-[280px]">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart margin={{ top: 20, right: 140, bottom: 20, left: 20 }}>
                    <Pie
                      data={stockPorBodega}
                      dataKey="value"
                      nameKey="name"
                      cx="38%"
                      cy="50%"
                      outerRadius={95}
                      innerRadius={42}
                      paddingAngle={2}
                      isAnimationActive
                    >
                      {stockPorBodega.map((entry, i) => (
                        <Cell key={entry.name} fill={COLORS[i % COLORS.length]} stroke="var(--background)" strokeWidth={1} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number, name: string) => {
                        const total = stockPorBodega.reduce((a, x) => a + x.value, 0);
                        const pct = total > 0 ? ((Number(value) / total) * 100).toFixed(1) : '0';
                        return [`${Number(value).toLocaleString('es-EC')} (${pct}%)`, name];
                      }}
                    />
                    <Legend
                      layout="vertical"
                      align="right"
                      verticalAlign="middle"
                      formatter={(value, entry) => {
                        const item = stockPorBodega.find((d) => d.name === value);
                        if (!item) return value;
                        const total = stockPorBodega.reduce((a, x) => a + x.value, 0);
                        const pct = total > 0 ? ((item.value / total) * 100).toFixed(1) : '0';
                        return `${abreviarBodega(value)} ${pct}%`;
                      }}
                      wrapperStyle={{ paddingLeft: 12 }}
                      iconType="circle"
                      iconSize={8}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Tabla de Alertas */}
          <Card>
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    Alertas de Stock Bajo
                  </CardTitle>
                  <CardDescription>
                    Productos por debajo del stock mínimo configurado
                  </CardDescription>
                </div>
                <div className="relative w-full sm:w-72">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar por producto o código..."
                    value={busquedaAlertas}
                    onChange={(e) => setBusquedaAlertas(e.target.value)}
                    className="pl-9"
                    disabled={alertas.length === 0}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {alertas.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No hay alertas de stock bajo en este momento.</p>
                </div>
              ) : (
                <>
                  {alertasFiltradas.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <Search className="w-10 h-10 mx-auto mb-3 opacity-50" />
                      <p>No hay alertas que coincidan con &quot;{busquedaAlertas}&quot;</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Código</TableHead>
                            <TableHead>Producto</TableHead>
                            <TableHead>Bodega</TableHead>
                            <TableHead className="text-right">Stock Actual</TableHead>
                            <TableHead className="text-right">Stock Mínimo</TableHead>
                            <TableHead className="text-right">Faltante</TableHead>
                            <TableHead>Estado</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {alertasFiltradas.map((alerta, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="font-mono">{alerta.producto_codigo}</TableCell>
                              <TableCell>{alerta.producto}</TableCell>
                              <TableCell>{alerta.bodega}</TableCell>
                              <TableCell className="text-right font-medium text-destructive">
                                {alerta.stock_actual}
                              </TableCell>
                              <TableCell className="text-right">{alerta.stock_minimo}</TableCell>
                              <TableCell className="text-right font-medium">
                                {(alerta.faltante ?? 0).toLocaleString('es-EC')}
                              </TableCell>
                              <TableCell>
                                <Badge variant="destructive" className="gap-1">
                                  <AlertTriangle className="w-3 h-3" />
                                  Stock Bajo
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                  {busquedaAlertas && alertasFiltradas.length > 0 && (
                    <p className="text-sm text-muted-foreground mt-2">
                      Mostrando {alertasFiltradas.length} de {alertas.length} alertas
                    </p>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ventas" className="space-y-6 mt-0">
          {/* Dashboard Reporte Gerencia - Ventas */}
          <div className="rounded-lg border bg-slate-50/50 dark:bg-slate-900/20 px-4 py-2">
            <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300">
              Dashboard de Ventas – Reporte Gerencia
            </h2>
            <p className="text-sm text-muted-foreground">
              KPIs y gráficos consolidados para la toma de decisiones.
            </p>
          </div>

          {/* KPIs Gerenciales */}
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
            <Card className="bg-primary/5 border-primary/20">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Cuentas por Cobrar</CardTitle>
                <DollarSign className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">
                  ${formatoMoneda(cuentasPorCobrar)}
                </div>
                <p className="text-xs text-muted-foreground">total cartera</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Cartera Vencida</CardTitle>
                <AlertTriangle className="h-4 w-4 text-destructive" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${carteraVencida > 0 ? 'text-destructive' : ''}`}>
                  ${formatoMoneda(carteraVencida)}
                </div>
                <p className="text-xs text-muted-foreground">en mora</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Ventas (últimos)</CardTitle>
                <ShoppingBag className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${formatoMoneda(totalVentasPeriodo)}</div>
                <p className="text-xs text-muted-foreground">{pedidos.length} pedidos</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Clientes</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{clientes.length.toLocaleString('es-EC')}</div>
                <p className="text-xs text-muted-foreground">en directorio</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Beneficiarios</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{clientes.filter((c) => c.tiene_beneficio).length.toLocaleString('es-EC')}</div>
                <p className="text-xs text-muted-foreground">con beneficios</p>
              </CardContent>
            </Card>
          </div>

          {/* Gráficos gerenciales */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Ventas por Vendedor
                </CardTitle>
                <CardDescription>Distribución del monto facturado por responsable</CardDescription>
              </CardHeader>
              <CardContent>
                {ventasPorVendedor.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={ventasPorVendedor} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${formatoMoneda(v)}`} />
                      <Tooltip formatter={(v: number) => [`$${formatoMoneda(v)}`, 'Ventas']} />
                      <Bar dataKey="value" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Ventas" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    No hay datos de ventas por vendedor
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Top Clientes por Monto
                </CardTitle>
                <CardDescription>Mayores compradores (últimos registros)</CardDescription>
              </CardHeader>
              <CardContent>
                {topClientesGerencial.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart
                      data={topClientesGerencial}
                      layout="vertical"
                      margin={{ top: 10, right: 40, left: 80, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `$${formatoMoneda(v)}`} />
                      <YAxis type="category" dataKey="name" width={75} tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v: number) => [`$${formatoMoneda(v)}`, 'Monto']} />
                      <Bar dataKey="value" fill="#8b5cf6" radius={[0, 4, 4, 0]} name="Monto" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    No hay datos de clientes
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Segunda Fila de Gráficos: Cobranza y Deudores */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Distribución Pagado vs Pendiente */}
            <Card>
              <CardHeader>
                <CardTitle>Estado de Cobranza</CardTitle>
                <CardDescription>Proporción de ventas pagadas vs pendientes</CardDescription>
              </CardHeader>
              <CardContent className="min-h-[260px]">
                {distribucionPago.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart margin={{ top: 20, right: 120, bottom: 20, left: 20 }}>
                      <Pie
                        data={distribucionPago}
                        dataKey="value"
                        nameKey="name"
                        cx="40%"
                        cy="50%"
                        outerRadius={90}
                        innerRadius={40}
                        paddingAngle={2}
                        isAnimationActive
                      >
                        {distribucionPago.map((entry, i) => (
                          <Cell key={entry.name} fill={entry.color} stroke="var(--background)" strokeWidth={1} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number, name: string) => [`$${formatoMoneda(Number(v))}`, name]} />
                      <Legend layout="vertical" align="right" verticalAlign="middle" />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[260px] flex items-center justify-center text-muted-foreground">
                    No hay datos de cobranza
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top Clientes Deudores */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-destructive" />
                  Top Clientes Deudores
                </CardTitle>
                <CardDescription>Clientes con mayor deuda pendiente registrada</CardDescription>
              </CardHeader>
              <CardContent>
                {topDeudores.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart
                      data={topDeudores}
                      layout="vertical"
                      margin={{ top: 10, right: 30, left: 80, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `$${formatoMoneda(v)}`} />
                      <YAxis type="category" dataKey="name" width={75} tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v: number) => [`$${formatoMoneda(v)}`, 'Deuda']} />
                      <Bar dataKey="deuda" fill="#ef4444" radius={[0, 4, 4, 0]} name="Deuda" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[260px] flex items-center justify-center text-muted-foreground">
                    No hay clientes con deuda
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Reportes Excel - Compacto */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5" />
                Exportar Reportes
              </CardTitle>
              <CardDescription>
                Descarga datos consolidados en Excel para análisis externo.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-1">
                  <Label className="text-xs">Desde</Label>
                  <Input
                    type="date"
                    value={reportFechas.inicio}
                    onChange={(e) => setReportFechas({ ...reportFechas, inicio: e.target.value })}
                    className="w-40"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Hasta</Label>
                  <Input
                    type="date"
                    value={reportFechas.fin}
                    onChange={(e) => setReportFechas({ ...reportFechas, fin: e.target.value })}
                    className="w-40"
                  />
                </div>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button variant="outline" size="sm" className="gap-2" onClick={handleExportVentasGerencial}>
                  <Download className="w-4 h-4" /> Ventas detalladas
                </Button>
                <Button variant="outline" size="sm" className="gap-2" onClick={handleExportTopClientesGerencial}>
                  <Download className="w-4 h-4" /> Top clientes
                </Button>
                <Button variant="outline" size="sm" className="gap-2" onClick={handleExportDeudoresGerencial}>
                  <Download className="w-4 h-4" /> Cartera vencida
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
