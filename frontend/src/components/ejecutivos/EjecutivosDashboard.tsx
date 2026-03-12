import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import {
  Package,
  Warehouse,
  History,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  TrendingUp,
  Activity,
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
const COLORS = ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4', '#84cc16'];

const abreviarBodega = (nombre: string, maxLen = 16) => {
  if (nombre.length <= maxLen) return nombre;
  return nombre.slice(0, maxLen - 1) + '…';
};

export function EjecutivosDashboard() {
  const { profile } = useAuth();
  const [productos, setProductos] = useState<Producto[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [lotes, setLotes] = useState<LoteProduccion[]>([]);
  const [alertas, setAlertas] = useState<AlertaStock[]>([]);
  const [stock, setStock] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = useCallback(async (showToast = false) => {
    if (showToast) setRefreshing(true);
    else setLoading(true);

    try {
      const [productosRes, bodegasRes, lotesRes, alertasRes, stockRes] = await Promise.all([
        apiClient.get<Producto[]>('/productos/'),
        apiClient.get<Bodega[]>('/bodegas/'),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/').catch(() => ({ data: [] })),
        apiClient.get<AlertaStock[]>('/inventory/alertas-stock/'),
        apiClient.get<StockItem[]>('/inventory/stock/'),
      ]);

      setProductos(productosRes.data);
      setBodegas(bodegasRes.data);
      setLotes(lotesRes.data);
      setAlertas(alertasRes.data);
      setStock(stockRes.data);

      if (showToast) toast.success('Datos actualizados');
    } catch (error) {
      console.error('Error cargando dashboard:', error);
      toast.error('Error al cargar los datos del dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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

  // Top alertas por faltante (para gráfico)
  const topAlertas = React.useMemo(() => {
    return [...alertas]
      .sort((a, b) => (b.faltante ?? 0) - (a.faltante ?? 0))
      .slice(0, 8)
      .map((a) => ({
        name: a.producto_codigo || a.producto.slice(0, 15),
        faltante: a.faltante ?? 0,
        bodega: a.bodega,
      }));
  }, [alertas]);

  const stockTotal = React.useMemo(() => {
    return stock.reduce((acc, s) => acc + parseFloat(s.cantidad || '0'), 0);
  }, [stock]);

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

      {/* KPIs */}
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
            <div className="text-2xl font-bold">{stockTotal.toLocaleString('es-CL', { minimumFractionDigits: 2 })}</div>
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
                  <Tooltip formatter={(v: number) => [v.toLocaleString('es-CL'), 'Stock']} />
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
                  <Tooltip formatter={(v: number) => [v.toLocaleString('es-CL'), 'Faltante']} />
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
                    return [`${Number(value).toLocaleString('es-CL')} (${pct}%)`, name];
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
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Alertas de Stock Bajo
          </CardTitle>
          <CardDescription>
            Productos por debajo del stock mínimo configurado
          </CardDescription>
        </CardHeader>
        <CardContent>
          {alertas.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No hay alertas de stock bajo en este momento.</p>
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
                  {alertas.map((alerta, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono">{alerta.producto_codigo}</TableCell>
                      <TableCell>{alerta.producto}</TableCell>
                      <TableCell>{alerta.bodega}</TableCell>
                      <TableCell className="text-right font-medium text-destructive">
                        {alerta.stock_actual}
                      </TableCell>
                      <TableCell className="text-right">{alerta.stock_minimo}</TableCell>
                      <TableCell className="text-right font-medium">
                        {(alerta.faltante ?? 0).toLocaleString('es-CL')}
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
        </CardContent>
      </Card>
    </div>
  );
}
