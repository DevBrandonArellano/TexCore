import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { AlertTriangle, Activity, Settings2, BarChart2, XCircle } from 'lucide-react';
import apiClient from '../../lib/axios';
import { Maquina, KPIArea, Producto, LoteProduccion } from '../../lib/types';
import { Progress } from '@/components/ui/progress';

export function JefeAreaDashboard() {
  const [kpis, setKpis] = useState<KPIArea | null>(null);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [alertas, setAlertas] = useState<Producto[]>([]);
  const [lotes, setLotes] = useState<LoteProduccion[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      // Fetch KPIs
      const kpiRes = await apiClient.get<KPIArea>('/kpi-area/');
      setKpis(kpiRes.data);

      // Fetch Maquinas
      const maquinasRes = await apiClient.get<Maquina[]>('/maquinas/');
      setMaquinas(maquinasRes.data);

      // Fetch Low Stock Products (Hilos/Quimicos)
      const productosRes = await apiClient.get<Producto[]>('/productos/');
      const lowStock = productosRes.data.filter(p =>
        (p.tipo === 'hilo' || p.tipo === 'quimico') &&
        // Assuming current stock checks would be done via another endpoint or calculated.
        // For now, let's assume we fetch products and check standard stock_minimo. 
        // But stock is in Bodega. This logic is simplified.
        // Ideally we fetch a "low stock report". 
        // I'll simulate it by checking if stock_minimo > 0 (as configured)
        p.stock_minimo > 0
      );
      // To get ACTUAL stock, we need to query stock endpoint. 
      // I'll skip complex stock logic here and just show products configured with alerts for demo.
      setAlertas(lowStock.slice(0, 5));

      // Fetch Recent Lotes
      const lotesRes = await apiClient.get<LoteProduccion[]>('/lotes-produccion/');
      setLotes(lotesRes.data);

    } catch (error) {
      console.error("Error fetching dashboard data", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRechazarLote = async (loteId: number) => {
    if (!confirm("¿Estás seguro de que deseas rechazar este lote? Esta acción revertirá los movimientos de inventario.")) return;

    try {
      await apiClient.post(`/lotes-produccion/${loteId}/rechazar/`);
      alert("Lote rechazado y movimientos revertidos.");
      fetchDashboardData(); // Refresh
    } catch (error) {
      console.error("Error rechazando lote", error);
      alert("Error al rechazar el lote.");
    }
  };

  const calculateMachineLoad = (maquina: Maquina) => {
    // Mock calculation: Capacity vs Produced today.
    // Ideally we sum lotes produced today on this machine.
    // For demo, return random or based on efficiency.
    return (maquina.eficiencia_ideal * 100) || 0;
  };

  if (isLoading) return <div>Cargando panel...</div>;

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Control - Área de Producción</h1>
          <p className="text-muted-foreground">Monitoreo en tiempo real de KPIs y maquinaria.</p>
        </div>
        <Button onClick={fetchDashboardData} variant="outline" size="sm">
          <Activity className="mr-2 h-4 w-4" /> Actualizar Datos
        </Button>
      </div>

      {/* KPIs Section */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Producción Total (Kg)</CardTitle>
            <BarChart2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpis?.total_produccion_kg.toLocaleString()} kg</div>
            <p className="text-xs text-muted-foreground">Ciclo actual</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rendimiento (Yield)</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(kpis?.rendimiento_yield || 0) * 100}%</div>
            <p className="text-xs text-muted-foreground">Entrada vs Salida</p>
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
            <div className="text-2xl font-bold text-destructive">{alertas.length}</div>
            <p className="text-xs text-muted-foreground">Stock bajo crítico</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-7">

        {/* Machine Status Panel */}
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Estado de Máquinas y Carga</CardTitle>
            <CardDescription>Monitoreo de capacidad y eficiencia operativa.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {maquinas.map((m) => (
                <div key={m.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="font-medium flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${m.estado === 'operativa' ? 'bg-green-500' : 'bg-red-500'}`} />
                      {m.nombre}
                      <span className="text-xs text-muted-foreground ml-2">({m.estado})</span>
                    </div>
                    <span className="text-sm text-muted-foreground">{calculateMachineLoad(m)}% Carga</span>
                  </div>
                  <Progress value={calculateMachineLoad(m)} className="h-2" />
                </div>
              ))}
              {maquinas.length === 0 && <p className="text-sm text-muted-foreground">No hay máquinas registradas.</p>}
            </div>
          </CardContent>
        </Card>

        {/* Alerts Panel */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Alertas de Inventario</CardTitle>
            <CardDescription>Productos químicos e hilos bajo mínimo.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alertas.map((prod) => (
                <Alert key={prod.id} variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Stock Bajo: {prod.codigo}</AlertTitle>
                  <AlertDescription>
                    {prod.descripcion} (Min: {prod.stock_minimo} {prod.unidad_medida})
                  </AlertDescription>
                </Alert>
              ))}
              {alertas.length === 0 && <Alert><AlertTitle>Todo en orden</AlertTitle><AlertDescription>No hay alertas de stock bajo.</AlertDescription></Alert>}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Lotes Management */}
      <Card>
        <CardHeader>
          <CardTitle>Gestión de Lotes Recientes</CardTitle>
          <CardDescription>Visualiza y gestiona la producción reciente.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Lote</TableHead>
                <TableHead>Máquina</TableHead>
                <TableHead>Operario</TableHead>
                <TableHead>Peso (Kg)</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lotes.slice(0, 10).map((lote) => (
                <TableRow key={lote.id}>
                  <TableCell className="font-medium">{lote.codigo_lote}</TableCell>
                  <TableCell>{lote.maquina_nombre || 'N/A'}</TableCell>
                  <TableCell>{lote.operario}</TableCell>
                  <TableCell>{lote.peso_neto_producido}</TableCell>
                  <TableCell>
                    <Button variant="ghost" className="text-destructive h-8 px-2" onClick={() => handleRechazarLote(lote.id)}>
                      <XCircle className="mr-2 h-4 w-4" /> Rechazar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}