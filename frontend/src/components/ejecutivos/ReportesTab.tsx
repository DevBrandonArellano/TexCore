import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { TabsContent } from '../ui/tabs';
import {
  BarChart3, DollarSign, TrendingDown, Factory, AlertTriangle, TrendingUp, Users, Activity,
  Layers, RefreshCw, Download,
} from 'lucide-react';
import { KpiCard } from './KpiCard';
import { fmt, toNum } from './utils';
import type { Sede } from '../../lib/types';
import type { AlertaStock, KpiEjecutivo } from './types';

interface ReportesTabProps {
  sedes: Sede[];
  filtroSedeId: string;
  reportFechas: { inicio: string; fin: string };
  setReportFechas: React.Dispatch<React.SetStateAction<{ inicio: string; fin: string }>>;
  totalVentas: number;
  pedidosLength: number;
  carteraVencida: number;
  alertaCartera: boolean;
  kp: KpiEjecutivo | null;
  alertas: AlertaStock[];
  descargando: string | null;
  exportVentas: () => void;
  exportTopClientes: () => void;
  exportDeudores: () => void;
  exportOrdenes: () => void;
  exportLotes: () => void;
  exportTendencia: () => void;
}

function ReportesTabImpl({
  sedes,
  filtroSedeId,
  reportFechas,
  setReportFechas,
  totalVentas,
  pedidosLength,
  carteraVencida,
  alertaCartera,
  kp,
  alertas,
  descargando,
  exportVentas,
  exportTopClientes,
  exportDeudores,
  exportOrdenes,
  exportLotes,
  exportTendencia,
}: ReportesTabProps) {
  return (
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
          subtitulo={`${pedidosLength} pedidos`}
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
  );
}

export const ReportesTab = React.memo(ReportesTabImpl);
