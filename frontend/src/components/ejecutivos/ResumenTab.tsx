import React from 'react';
import { TabsContent } from '../ui/tabs';
import {
  Factory, ShoppingCart, DollarSign, Activity, Clock, TrendingUp, BarChart3,
  AlertTriangle, CheckCircle2, Package, TrendingDown, ShoppingBag,
} from 'lucide-react';
import { KpiCard } from './KpiCard';
import { fmt } from './utils';
import type { KpiEjecutivo } from './types';

interface ResumenTabProps {
  kp: KpiEjecutivo | null;
  cuentasPorCobrar: number;
  carteraVencida: number;
  limiteCartera: number;
  alertaCartera: boolean;
}

function ResumenTabImpl({ kp, cuentasPorCobrar, carteraVencida, limiteCartera, alertaCartera }: ResumenTabProps) {
  return (
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
  );
}

export const ResumenTab = React.memo(ResumenTabImpl);
