import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { TabsContent } from '../ui/tabs';
import {
  DollarSign, TrendingDown, ShoppingBag, Users, FileSpreadsheet, Download, AlertTriangle, CheckCircle2,
} from 'lucide-react';
import { BarChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, Bar } from 'recharts';
import { KpiCard } from './KpiCard';
import {
  PedidosEstadoModal,
  VentasVendedorModal,
  ClienteComprasModal,
  ClienteDeudorModal,
} from './DrillDownModals';
import { fmt } from './utils';
import type { Cliente, PedidoVenta } from '../../lib/types';

interface VentasTabProps {
  pedidos: PedidoVenta[];
  clientes: Cliente[];
  cuentasPorCobrar: number;
  carteraVencida: number;
  limiteCartera: number;
  alertaCartera: boolean;
  totalVentas: number;
  ventasPorVendedor: { name: string; fullName: string; value: number }[];
  topClientesGerencial: { name: string; fullName: string; value: number }[];
  topDeudores: { name: string; fullName: string; deuda: number; obj: Cliente }[];
  distribucionPago: { name: string; value: number; color: string }[];
  funnelData: { estado: string; key: string; total: number; fill: string }[];
  modalEstadoPedido: string | null;
  setModalEstadoPedido: (v: string | null) => void;
  modalVendedor: string | null;
  setModalVendedor: (v: string | null) => void;
  modalClienteCompras: string | null;
  setModalClienteCompras: (v: string | null) => void;
  modalClienteDeudor: string | null;
  setModalClienteDeudor: (v: string | null) => void;
  reportFechas: { inicio: string; fin: string };
  setReportFechas: React.Dispatch<React.SetStateAction<{ inicio: string; fin: string }>>;
  exportVentas: () => void;
  exportTopClientes: () => void;
  exportDeudores: () => void;
}

function VentasTabImpl({
  pedidos,
  clientes,
  cuentasPorCobrar,
  carteraVencida,
  limiteCartera,
  alertaCartera,
  totalVentas,
  ventasPorVendedor,
  topClientesGerencial,
  topDeudores,
  distribucionPago,
  funnelData,
  modalEstadoPedido,
  setModalEstadoPedido,
  modalVendedor,
  setModalVendedor,
  modalClienteCompras,
  setModalClienteCompras,
  modalClienteDeudor,
  setModalClienteDeudor,
  reportFechas,
  setReportFechas,
  exportVentas,
  exportTopClientes,
  exportDeudores,
}: VentasTabProps) {
  return (
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
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={funnelData} layout="vertical" margin={{ left: 10, right: 30 }}>
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis dataKey="estado" type="category" tick={{ fontSize: 11 }} width={90} />
              <Tooltip formatter={(v: number) => [v, 'Pedidos']} cursor={{fill: 'transparent'}} />
              <Bar
                dataKey="total"
                radius={[0, 4, 4, 0]}
                onClick={(data) => {
                  if (data && data.payload && data.payload.key) {
                    setModalEstadoPedido(data.payload.key);
                  }
                }}
                className="cursor-pointer hover:opacity-80 transition-opacity"
              >
                {funnelData.map((d, i) => (
                  <Cell key={i} fill={d.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
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
                <Tooltip formatter={(v: number) => [`$${fmt(v)}`, 'Ventas']} cursor={{fill: 'transparent'}} />
                <Bar
                  dataKey="value"
                  fill="#6366f1"
                  radius={[4, 4, 0, 0]}
                  onClick={(data) => {
                    if (data && data.payload && data.payload.fullName) {
                      setModalVendedor(data.payload.fullName);
                    }
                  }}
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                />
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
                <Tooltip formatter={(v: number) => [`$${fmt(v)}`, 'Compras']} cursor={{fill: 'transparent'}} />
                <Bar
                  dataKey="value"
                  fill="#10b981"
                  radius={[0, 4, 4, 0]}
                  onClick={(data) => {
                    if (data && data.payload && data.payload.fullName) {
                      setModalClienteCompras(data.payload.fullName);
                    }
                  }}
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                />
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
                  <Tooltip formatter={(v: number) => [`$${fmt(v)}`, 'Deuda']} cursor={{fill: 'transparent'}} />
                  <Bar
                    dataKey="deuda"
                    fill="#ef4444"
                    radius={[0, 4, 4, 0]}
                    onClick={(data) => {
                      if (data && data.payload && data.payload.fullName) {
                        setModalClienteDeudor(data.payload.fullName);
                      }
                    }}
                    className="cursor-pointer hover:opacity-80 transition-opacity"
                  />
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

      {/* Modales de Interacción de Ventas (Separados para cumplir SRP / ISO 25010) */}
      <PedidosEstadoModal
        estado={modalEstadoPedido}
        onClose={() => setModalEstadoPedido(null)}
        pedidos={pedidos}
      />
      <VentasVendedorModal
        vendedor={modalVendedor}
        onClose={() => setModalVendedor(null)}
        pedidos={pedidos}
      />
      <ClienteComprasModal
        cliente={modalClienteCompras}
        onClose={() => setModalClienteCompras(null)}
        pedidos={pedidos}
      />
      <ClienteDeudorModal
        clienteNombre={modalClienteDeudor}
        onClose={() => setModalClienteDeudor(null)}
        topDeudores={topDeudores as any}
      />
    </TabsContent>
  );
}

export const VentasTab = React.memo(VentasTabImpl);
