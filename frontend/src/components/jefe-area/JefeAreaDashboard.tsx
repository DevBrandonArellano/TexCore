import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { AlertTriangle, Activity, Settings2, BarChart2, XCircle, CheckCircle, UserPlus, Layout, ListChecks, Plus, Monitor, ClipboardList } from 'lucide-react';
import apiClient from '../../lib/axios';
import { Maquina, KPIArea, Producto, LoteProduccion, User, OrdenProduccion } from '../../lib/types';
import { Progress } from '../ui/progress';
import { useAuth } from '../../lib/auth';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';

function MaquinaDialog({
  open,
  onOpenChange,
  maquina,
  operarios,
  areaId,
  onSave
}: {
  open: boolean,
  onOpenChange: (open: boolean) => void,
  maquina: Partial<Maquina> | null,
  operarios: User[],
  areaId: number | undefined,
  onSave: () => void
}) {
  const [formData, setFormData] = useState({
    nombre: '',
    capacidad_maxima: '',
    eficiencia_ideal: '0.85',
    estado: 'operativa',
    operarios: [] as number[]
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (maquina) {
      setFormData({
        nombre: maquina.nombre || '',
        capacidad_maxima: maquina.capacidad_maxima?.toString() || '',
        eficiencia_ideal: maquina.eficiencia_ideal?.toString() || '0.85',
        estado: maquina.estado || 'operativa',
        operarios: maquina.operarios || []
      });
    } else {
      setFormData({
        nombre: '',
        capacidad_maxima: '',
        eficiencia_ideal: '0.85',
        estado: 'operativa',
        operarios: []
      });
    }
  }, [maquina, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const data = {
        ...formData,
        area: areaId,
        capacidad_maxima: parseFloat(formData.capacidad_maxima),
        eficiencia_ideal: parseFloat(formData.eficiencia_ideal),
      };

      if (maquina?.id) {
        await apiClient.put(`/maquinas/${maquina.id}/`, data);
        toast.success("Máquina actualizada correctamente.");
      } else {
        await apiClient.post('/maquinas/', data);
        toast.success("Máquina creada correctamente.");
      }
      onSave();
      onOpenChange(false);
    } catch (error) {
      toast.error("Error al guardar la máquina.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleOperario = (id: number) => {
    setFormData(prev => ({
      ...prev,
      operarios: prev.operarios.includes(id)
        ? prev.operarios.filter(oid => oid !== id)
        : [...prev.operarios, id]
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{maquina?.id ? 'Editar Máquina' : 'Nueva Máquina'}</DialogTitle>
          <DialogDescription>Configura los detalles técnicos y el personal a cargo.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre de la Máquina</Label>
            <Input id="nombre" value={formData.nombre} onChange={e => setFormData({ ...formData, nombre: e.target.value })} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="capacidad">Capacidad (Kg/Turno)</Label>
              <Input id="capacidad" type="number" step="0.01" value={formData.capacidad_maxima} onChange={e => setFormData({ ...formData, capacidad_maxima: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="estado">Estado Inicial</Label>
              <Select value={formData.estado} onValueChange={v => setFormData({ ...formData, estado: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="operativa">Operativa</SelectItem>
                  <SelectItem value="mantenimiento">Mantenimiento</SelectItem>
                  <SelectItem value="inactiva">Inactiva</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Operarios Asignados (Control)</Label>
            <ScrollArea className="h-32 border rounded-md p-2 bg-slate-50">
              <div className="space-y-2">
                {operarios.map(u => (
                  <div key={u.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`u-${u.id}`}
                      checked={formData.operarios.includes(u.id)}
                      onCheckedChange={() => toggleOperario(u.id)}
                    />
                    <Label htmlFor={`u-${u.id}`} className="text-sm font-normal cursor-pointer">
                      {u.username}
                    </Label>
                  </div>
                ))}
                {operarios.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">No hay operarios en esta área.</p>}
              </div>
            </ScrollArea>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Guardando...' : 'Guardar'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function JefeAreaDashboard() {
  const { profile } = useAuth();
  const [kpis, setKpis] = useState<KPIArea | null>(null);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [alertas, setAlertas] = useState<Producto[]>([]);
  const [lotes, setLotes] = useState<LoteProduccion[]>([]);
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [operarios, setOperarios] = useState<User[]>([]);
  const [assignments, setAssignments] = useState<Record<number, { maquinaId: string, operarioId: string }>>({});
  const [isMaquinaDialogOpen, setIsMaquinaDialogOpen] = useState(false);
  const [selectedMaquina, setSelectedMaquina] = useState<Partial<Maquina> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [maquinasCarga, setMaquinasCarga] = useState<Record<number, number>>({});

  useEffect(() => {
    if (profile) {
      fetchDashboardData();
    }
  }, [profile]);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      const [kpiRes, maquinasRes, ordenesRes, usersRes, productosRes, lotesRes] = await Promise.all([
        apiClient.get<KPIArea>('/kpi-area/'),
        apiClient.get<Maquina[]>('/maquinas/'),
        apiClient.get<OrdenProduccion[]>('/ordenes-produccion/'),
        apiClient.get<User[]>('/users/'),
        apiClient.get<Producto[]>('/productos/'),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/')
      ]);

      setKpis(kpiRes.data);
      setMaquinas(maquinasRes.data);
      setOrdenes(ordenesRes.data);
      setOperarios(usersRes.data);

      // Calcular carga real de trabajo por máquina
      const today = new Date().toISOString().split('T')[0];
      const cargas: Record<number, number> = {};

      maquinasRes.data.forEach(m => {
        const produccionHoy = lotesRes.data
          .filter(l => l.maquina === m.id && l.hora_final.startsWith(today))
          .reduce((sum, l) => sum + Number(l.peso_neto_producido), 0);

        const capacidad = Number(m.capacidad_maxima) || 1;
        cargas[m.id] = Math.min(Math.round((produccionHoy / capacidad) * 100), 100);
      });
      setMaquinasCarga(cargas);

      const lowStock = productosRes.data.filter(p =>
        (p.tipo === 'hilo' || p.tipo === 'quimico') &&
        p.stock_minimo > 0
      );
      setAlertas(lowStock.slice(0, 5));
      setLotes(lotesRes.data);

    } catch (error) {
      console.error("Error fetching dashboard data", error);
      toast.error("Error al cargar los datos del panel.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRechazarLote = async (loteId: number) => {
    if (!window.confirm("¿Estás seguro de que deseas rechazar este lote? Esta acción revertirá los movimientos de inventario.")) return;

    try {
      await apiClient.post(`/lotes-produccion/${loteId}/rechazar/`);
      window.alert("Lote rechazado y movimientos revertidos.");
      fetchDashboardData(); // Refresh
    } catch (error) {
      console.error("Error rechazando lote", error);
      window.alert("Error al rechazar el lote.");
    }
  };

  const handleAsignarOrden = async (ordenId: number, maquinaId: string, operarioId: string) => {
    if (!maquinaId || !operarioId) {
      toast.error("Debes seleccionar una máquina y un operario.");
      return;
    }

    try {
      await apiClient.patch(`/ordenes-produccion/${ordenId}/`, {
        maquina_asignada: parseInt(maquinaId),
        operario_asignado: parseInt(operarioId),
        estado: 'en_proceso'
      });
      toast.success("Orden asignada e iniciada correctamente.");
      fetchDashboardData();
    } catch (error) {
      console.error("Error asignando orden", error);
      toast.error("Error al asignar la orden.");
    }
  };

  const calculateMachineLoad = (maquina: Maquina) => {
    return maquinasCarga[maquina.id] || 0;
  };

  const handleEditMaquina = (maquina: Maquina) => {
    setSelectedMaquina(maquina);
    setIsMaquinaDialogOpen(true);
  };

  const handleToggleEstadoMaquina = async (maquina: Maquina) => {
    const nuevoEstado = maquina.estado === 'operativa' ? 'inactiva' : 'operativa';
    try {
      await apiClient.patch(`/maquinas/${maquina.id}/`, { estado: nuevoEstado });
      toast.success(`Máquina ${maquina.nombre} ahora está ${nuevoEstado}.`);
      fetchDashboardData();
    } catch (error) {
      toast.error("Error al cambiar el estado de la máquina.");
    }
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

      {/* Assignment Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-blue-500" />
            <div>
              <CardTitle>Planificación y Asignación de Órdenes</CardTitle>
              <CardDescription>Asigna máquinas y personal a las órdenes creadas por Jefe de Planta.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {ordenes.filter(o => o.estado === 'pendiente').length > 0 ? (
            <div className="space-y-4">
              {ordenes.filter(o => o.estado === 'pendiente').map((orden) => {
                // local states for the selectors in each row if needed, but for simplicity we can use refs or just inline buttons
                return (
                  <div key={orden.id} className="flex flex-col md:flex-row items-start md:items-center gap-4 p-4 border rounded-lg bg-slate-50/50">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="font-mono text-[10px] text-blue-600 border-blue-200 bg-blue-50">{orden.codigo}</Badge>
                        <span className="font-bold text-slate-800">{orden.producto_nombre}</span>
                        {orden.observaciones && (
                          <Badge variant="secondary" className="bg-amber-100 text-amber-700 border-amber-200 text-[10px]">
                            <ClipboardList className="w-3 h-3 mr-1" /> Nota
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground space-y-1">
                        <p>Requerido: <span className="font-semibold text-slate-700">{orden.peso_neto_requerido} Kg</span> | Fórmula: <span className="text-slate-700">{orden.formula_color_nombre}</span></p>
                        {orden.observaciones && <p className="italic text-amber-600 text-[11px] leading-tight">"{orden.observaciones}"</p>}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                      <div className="w-40">
                        <Select onValueChange={(val) => setAssignments(prev => ({
                          ...prev,
                          [orden.id]: { ...prev[orden.id], maquinaId: val }
                        }))}>
                          <SelectTrigger className="h-9 bg-white">
                            <SelectValue placeholder="Máquina" />
                          </SelectTrigger>
                          <SelectContent>
                            {maquinas.map(m => (
                              <SelectItem key={m.id} value={m.id.toString()}>{m.nombre}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="w-40">
                        <Select onValueChange={(val) => setAssignments(prev => ({
                          ...prev,
                          [orden.id]: { ...prev[orden.id], operarioId: val }
                        }))}>
                          <SelectTrigger className="h-9 bg-white">
                            <SelectValue placeholder="Operario" />
                          </SelectTrigger>
                          <SelectContent>
                            {operarios.map(u => (
                              <SelectItem key={u.id} value={u.id.toString()}>{u.username}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <Button
                        size="sm"
                        onClick={() => handleAsignarOrden(
                          orden.id,
                          assignments[orden.id]?.maquinaId || '',
                          assignments[orden.id]?.operarioId || ''
                        )}
                        disabled={!maquinas.length || !operarios.length}
                      >
                        <CheckCircle className="mr-2 h-4 w-4" /> Asignar
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-lg border border-dashed">
              <Layout className="h-8 w-8 text-muted-foreground mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">No hay órdenes pendientes de asignación en tu área.</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-7">

        {/* Machine Status Panel */}
        <Card className="col-span-4">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Estado de Máquinas y Carga</CardTitle>
              <CardDescription>Monitoreo de capacidad y eficiencia operativa.</CardDescription>
            </div>
            <Button size="sm" onClick={() => { setSelectedMaquina(null); setIsMaquinaDialogOpen(true); }}>
              <Plus className="mr-2 h-4 w-4" /> Nueva Máquina
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {maquinas.map((m) => (
                <div key={m.id} className="p-3 border rounded-lg bg-slate-50/50 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-medium flex items-center gap-2">
                      <div className={`h-2.5 w-2.5 rounded-full ${m.estado === 'operativa' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} />
                      <span className="text-sm font-semibold">{m.nombre}</span>
                      <Badge variant="outline" className="text-[10px] h-4">
                        {m.capacidad_maxima} Kg/Turno
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleEditMaquina(m)}>
                        <Settings2 className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className={`h-7 w-7 ${m.estado === 'operativa' ? 'text-red-500' : 'text-green-500'}`}
                        onClick={() => handleToggleEstadoMaquina(m)}
                      >
                        <Activity className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-1">
                    <span>Carga: {calculateMachineLoad(m)}%</span>
                    <span>{m.operarios_nombres?.length || 0} Operarios</span>
                  </div>
                  <Progress value={calculateMachineLoad(m)} className="h-1.5" />
                  {m.operarios_nombres && m.operarios_nombres.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.operarios_nombres.map((name, i) => (
                        <span key={i} className="text-[10px] bg-white border px-1.5 py-0.5 rounded text-muted-foreground">
                          {name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {maquinas.length === 0 && <p className="text-sm text-muted-foreground text-center py-6">No hay máquinas registradas en esta área.</p>}
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
                  <TableCell>{lote.operario_nombre || 'N/A'}</TableCell>
                  <TableCell>{lote.peso_neto_producido} Kg</TableCell>
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
      <MaquinaDialog
        open={isMaquinaDialogOpen}
        onOpenChange={setIsMaquinaDialogOpen}
        maquina={selectedMaquina}
        operarios={operarios}
        areaId={profile?.user.area ?? undefined}
        onSave={fetchDashboardData}
      />
    </div>
  );
}