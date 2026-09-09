import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { TabsContent } from '../ui/tabs';
import { Package, Warehouse, Layers, AlertTriangle, Search, CheckCircle2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { KpiCard } from './KpiCard';
import { StockBodegaModal, type StockItem } from './DrillDownModals';
import { fmt, toNum } from './utils';
import type { AlertaStock } from './types';

const COLORS = [
  '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
  '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
  '#469990', '#dcbeff', '#9A6324', '#800000', '#aaffc3',
];

interface StockTabProps {
  alertas: AlertaStock[];
  stock: StockItem[];
  busquedaAlertas: string;
  setBusquedaAlertas: (v: string) => void;
  bodegaSeleccionada: string | null;
  setBodegaSeleccionada: (v: string | null) => void;
  stockPorBodega: { name: string; fullBodegaName: string; value: number }[];
  alertasFiltradas: AlertaStock[];
  topAlertas: { name: string; faltante: number }[];
}

function StockTabImpl({
  alertas,
  stock,
  busquedaAlertas,
  setBusquedaAlertas,
  bodegaSeleccionada,
  setBodegaSeleccionada,
  stockPorBodega,
  alertasFiltradas,
  topAlertas,
}: StockTabProps) {
  return (
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
            <CardDescription>Distribución actual de inventario (Click para ver detalles)</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={stockPorBodega} margin={{ top: 5, right: 10, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => [fmt(v, 1), 'Stock']} cursor={{fill: 'transparent'}} />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                  {stockPorBodega.map((item, i) => (
                    <Cell
                      key={i}
                      fill={COLORS[i % COLORS.length]}
                      className="cursor-pointer hover:opacity-80 transition-opacity"
                      onClick={() => setBodegaSeleccionada(item.fullBodegaName)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <StockBodegaModal
          bodegaSeleccionada={bodegaSeleccionada}
          onClose={() => setBodegaSeleccionada(null)}
          stock={stock}
        />

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
  );
}

export const StockTab = React.memo(StockTabImpl);
