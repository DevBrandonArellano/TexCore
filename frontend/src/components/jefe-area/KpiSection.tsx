import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { AlertTriangle, Activity, Settings2, BarChart2, Gauge } from 'lucide-react';
import type { KPIArea } from '../../lib/types';
import { claseSeveridadOee } from './maquinaUtils';

interface KpiSectionProps {
  kpis: KPIArea | null;
  alertasCount: number;
}

function KpiSectionImpl({ kpis, alertasCount }: KpiSectionProps) {
  return (
    // UX-2: en lg (no xl) 5 tarjetas en 3 columnas queda 3+2 (más equilibrado
    // que el 4+1 de un grid a 2 columnas); en xl+ entran las 5 en una fila.
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 flex-shrink-0">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Producción Total (Kg)</CardTitle>
          <BarChart2 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{kpis?.total_produccion_kg?.toLocaleString()} kg</div>
          <p className="text-xs text-muted-foreground">Ciclo actual</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Rendimiento (Yield)</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{((kpis?.rendimiento_yield || 0) * 100).toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">
            FPY 1ª calidad: {((kpis?.first_pass_yield || 0) * 100).toFixed(1)}%
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tiempo Promedio</CardTitle>
          <Settings2 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{kpis?.tiempo_promedio_lote_min} min</div>
          <p className="text-xs text-muted-foreground">Por lote operado</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Alertas Activas</CardTitle>
          <AlertTriangle className="h-4 w-4 text-destructive" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-destructive">{alertasCount}</div>
          <p className="text-xs text-muted-foreground">Stock bajo crítico</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">OEE (histórico)</CardTitle>
          <Gauge className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${claseSeveridadOee(kpis?.oee?.oee || 0)}`}>
            {((kpis?.oee?.oee || 0) * 100).toFixed(1)}%
          </div>
          <p className="text-xs text-muted-foreground">
            Disp. {((kpis?.oee?.disponibilidad || 0) * 100).toFixed(1)}% · Desem. {((kpis?.oee?.rendimiento || 0) * 100).toFixed(1)}% · Cal. {((kpis?.oee?.calidad || 0) * 100).toFixed(1)}%
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export const KpiSection = React.memo(KpiSectionImpl);
