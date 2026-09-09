import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { TabsContent } from '../ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import {
  TrendingUp, BarChart3, Activity, Clock, Factory, FileSpreadsheet, Download, Printer, RefreshCw, Layers,
} from 'lucide-react';
import {
  BarChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
  Area, AreaChart,
} from 'recharts';
import { KpiCard } from './KpiCard';
import { fmt } from './utils';
import { ProductoHistorialModal } from './DrillDownModals';
import type { ProduccionResumen, ProduccionProductoItem, TendenciaDia } from './types';

interface ProduccionTabProps {
  pr: ProduccionResumen | null;
  datosTendenciaProcesados: { fecha: string; kg: number }[];
  rangoTendencia: number;
  setRangoTendencia: (v: number) => void;
  agrupacionTendencia: 'diario' | 'semanal' | 'mensual';
  setAgrupacionTendencia: (v: 'diario' | 'semanal' | 'mensual') => void;
  reportFechas: { inicio: string; fin: string };
  setReportFechas: React.Dispatch<React.SetStateAction<{ inicio: string; fin: string }>>;
  exportOrdenes: () => void;
  exportLotes: () => void;
  productosPorProducto: ProduccionProductoItem[];
  cargandoProductosPorProducto: boolean;
  productoSeleccionado: ProduccionProductoItem | null;
  historialProducto: TendenciaDia[];
  cargandoHistorialProducto: boolean;
  imprimiendoProduccionPorProducto: boolean;
  onVerHistorialProducto: (item: ProduccionProductoItem) => void;
  onCerrarHistorialProducto: () => void;
  onImprimirProduccionPorProducto: () => void;
}

function ProduccionTabImpl({
  pr,
  datosTendenciaProcesados,
  rangoTendencia,
  setRangoTendencia,
  agrupacionTendencia,
  setAgrupacionTendencia,
  reportFechas,
  setReportFechas,
  exportOrdenes,
  exportLotes,
  productosPorProducto,
  cargandoProductosPorProducto,
  productoSeleccionado,
  historialProducto,
  cargandoHistorialProducto,
  imprimiendoProduccionPorProducto,
  onVerHistorialProducto,
  onCerrarHistorialProducto,
  onImprimirProduccionPorProducto,
}: ProduccionTabProps) {
  return (
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

        {/* Area chart: Tendencia de Producción con controles interactivos */}
        <Card className="transition-all duration-300 hover:shadow-2xl hover:-translate-y-0.5 border-slate-200/60 dark:border-slate-800/60 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                Tendencia de Producción
              </CardTitle>
              <CardDescription>Kilogramos producidos — {agrupacionTendencia === 'diario' ? 'vista diaria' : agrupacionTendencia === 'semanal' ? 'agrupado por semana' : 'agrupado por mes'}</CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
              {/* Selector de Rango */}
              <Select value={String(rangoTendencia)} onValueChange={(v) => setRangoTendencia(Number(v))}>
                <SelectTrigger className="h-8 w-36 text-xs">
                  <SelectValue placeholder="Rango" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">Últimos 7 días</SelectItem>
                  <SelectItem value="15">Últimos 15 días</SelectItem>
                  <SelectItem value="30">Últimos 30 días</SelectItem>
                  <SelectItem value="90">Últimos 90 días</SelectItem>
                </SelectContent>
              </Select>

              {/* Toggle Diario / Semanal / Mensual */}
              <div className="flex items-center border border-slate-200 dark:border-slate-800 rounded-lg p-0.5 bg-slate-100/50 dark:bg-slate-900/50 h-8">
                {(['diario', 'semanal', 'mensual'] as const).map(opcion => (
                  <button
                    key={opcion}
                    onClick={() => setAgrupacionTendencia(opcion)}
                    className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-200 capitalize ${
                      agrupacionTendencia === opcion
                        ? 'bg-white dark:bg-slate-800 shadow-sm text-blue-600 dark:text-blue-400'
                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                    }`}
                  >
                    {opcion.charAt(0).toUpperCase() + opcion.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {datosTendenciaProcesados.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={datosTendenciaProcesados} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <defs>
                    <linearGradient id="gradKg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(217,91%,60%)" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="hsl(217,91%,60%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(215,28%,93%)" />
                  <XAxis
                    dataKey="fecha"
                    tick={{ fontSize: 9, fill: 'hsl(215,16%,47%)' }}
                    tickFormatter={v => agrupacionTendencia === 'diario' ? v.slice(5) : v}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis tick={{ fontSize: 9, fill: 'hsl(215,16%,47%)' }} width={40} axisLine={false} tickLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="backdrop-blur-xl bg-white/90 dark:bg-slate-950/90 border border-blue-100/60 dark:border-blue-900/40 p-3 rounded-2xl shadow-2xl space-y-1.5 animate-in fade-in-0 zoom-in-95 duration-150">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{label}</p>
                            <div className="flex items-center gap-2">
                              <div className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm shadow-blue-300 animate-pulse" />
                              <p className="text-base font-black tabular-nums text-slate-800 dark:text-slate-100">
                                {fmt(Number(payload[0].value), 1)} <span className="text-xs font-semibold text-slate-400">kg</span>
                              </p>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area type="monotone" dataKey="kg" stroke="hsl(217,91%,60%)" fill="url(#gradKg)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: 'hsl(217,91%,60%)', strokeWidth: 2, stroke: '#fff' }} />
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

      {/* Producción por Producto — CU-EJ-08/09: drill-down ejecutivo */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-500" /> Producción por Producto
            </CardTitle>
            <CardDescription>
              Detalle por producto en el rango seleccionado — clic en un producto para ver su historial diario
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-1 shrink-0"
            onClick={onImprimirProduccionPorProducto}
            disabled={imprimiendoProduccionPorProducto}
            data-testid="btn-imprimir-produccion-producto"
          >
            {imprimiendoProduccionPorProducto
              ? <RefreshCw className="w-4 h-4 animate-spin" />
              : <Printer className="w-4 h-4" />} Imprimir
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead className="text-right">Kg Total</TableHead>
                <TableHead className="text-right"># Lotes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cargandoProductosPorProducto ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    Cargando producción por producto…
                  </TableCell>
                </TableRow>
              ) : productosPorProducto.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    Sin producción registrada en el rango seleccionado.
                  </TableCell>
                </TableRow>
              ) : (
                productosPorProducto.map((item) => (
                  <TableRow
                    key={item.producto_id}
                    className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900"
                    onClick={() => onVerHistorialProducto(item)}
                    data-testid={`fila-producto-${item.producto_id}`}
                  >
                    <TableCell className="font-mono text-xs">{item.producto_codigo}</TableCell>
                    <TableCell>{item.producto_nombre}</TableCell>
                    <TableCell className="text-right font-medium">{fmt(item.kg_total, 1)}</TableCell>
                    <TableCell className="text-right">{item.num_lotes}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

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

      <ProductoHistorialModal
        producto={productoSeleccionado}
        historial={historialProducto}
        cargando={cargandoHistorialProducto}
        onClose={onCerrarHistorialProducto}
      />
    </TabsContent>
  );
}

export const ProduccionTab = React.memo(ProduccionTabImpl);
