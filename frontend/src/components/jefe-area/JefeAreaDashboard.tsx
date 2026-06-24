import React, { useEffect, useState } from 'react';
import { ManageMaquinas } from './ManageMaquinas';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { AlertTriangle, Activity, Settings2, BarChart2, XCircle, CheckCircle, Layout, ListChecks, ClipboardList, ChevronLeft, ChevronRight, Zap, PlusCircle } from 'lucide-react';
import { EtapasProduccion } from '../produccion/EtapasProduccion';
import { FlujoProduccion } from '../produccion/FlujoProduccion';
import { TrazabilidadProducto } from '../produccion/TrazabilidadProducto';
import { GitBranch } from 'lucide-react';
import apiClient from '../../lib/axios';
import { Maquina, KPIArea, Producto, LoteProduccion, User, OrdenProduccion, Bodega, FormulaColor } from '../../lib/types';
import { Progress } from '../ui/progress';
import { useAuth } from '../../lib/auth';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';

const ITEMS_PER_PAGE = 20;

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
  const [productos, setProductos] = useState<Producto[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [assignments, setAssignments] = useState<Record<number, { maquinaId: string, operarioId: string }>>({});
  const [isMaquinaDialogOpen, setIsMaquinaDialogOpen] = useState(false);
  const [selectedMaquina, setSelectedMaquina] = useState<Partial<Maquina> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [maquinasCarga, setMaquinasCarga] = useState<Record<number, number>>({});
  const [currentAlertasPage, setCurrentAlertasPage] = useState(1);
  const [currentLotesPage, setCurrentLotesPage] = useState(1);
  const [isNuevaOrdenOpen, setIsNuevaOrdenOpen] = useState(false);
  const [trazaOrdenId, setTrazaOrdenId] = useState<number | null>(null);
  const [isSubmittingOrden, setIsSubmittingOrden] = useState(false);
  const [nuevaOrdenForm, setNuevaOrdenForm] = useState({
    codigo: '',
    peso_neto_requerido: '',
    producto_entrada: '',
    bodega_entrada: '',
    producto_salida: '',
    bodega_salida: '',
    formula_color: '',
    observaciones: '',
  });

  useEffect(() => {
    if (profile) {
      fetchDashboardData();
    }
  }, [profile]);

  useEffect(() => {
    setCurrentAlertasPage(1);
  }, [alertas.length]);

  useEffect(() => {
    setCurrentLotesPage(1);
  }, [lotes.length]);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      const [kpiRes, maquinasRes, ordenesRes, usersRes, productosRes, lotesRes, bodegasRes, formulasRes] = await Promise.all([
        apiClient.get<KPIArea>('/kpi-area/'),
        apiClient.get<Maquina[]>('/maquinas/'),
        apiClient.get<OrdenProduccion[]>('/ordenes-produccion/'),
        apiClient.get<User[]>('/users/'),
        apiClient.get<Producto[]>('/productos/'),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/'),
        apiClient.get('/bodegas/'),
        apiClient.get('/formulas-color/'),
      ]);

      setKpis(kpiRes.data);
      setMaquinas(Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || []);
      setOrdenes(Array.isArray(ordenesRes.data) ? ordenesRes.data : (ordenesRes.data as any).results || []);
      setOperarios(Array.isArray(usersRes.data) ? usersRes.data : (usersRes.data as any).results || []);
      setLotes(Array.isArray(lotesRes.data) ? lotesRes.data : (lotesRes.data as any).results || []);
      setBodegas(Array.isArray(bodegasRes.data) ? bodegasRes.data : (bodegasRes.data as any).results || []);
      setFormulas(Array.isArray(formulasRes.data) ? formulasRes.data : (formulasRes.data as any).results || []);

      // Extraer datos para cálculos
      const maquinasData = Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || [];
      const lotesData = Array.isArray(lotesRes.data) ? lotesRes.data : (lotesRes.data as any).results || [];
      const productosData = Array.isArray(productosRes.data) ? productosRes.data : (productosRes.data as any).results || [];
      setProductos(productosData);

      // Calcular carga real de trabajo por máquina
      const today = new Date().toISOString().split('T')[0];
      const cargas: Record<number, number> = {};

      maquinasData.forEach((m: Maquina) => {
        const produccionHoy = (lotesData as LoteProduccion[])
          .filter((l: LoteProduccion) => l.maquina === m.id && l.hora_final.startsWith(today))
          .reduce((sum: number, l: LoteProduccion) => sum + Number(l.peso_neto_producido), 0);

        const capacidad = Number(m.capacidad_maxima) || 1;
        cargas[m.id] = Math.min(Math.round((produccionHoy / capacidad) * 100), 100);
      });
      setMaquinasCarga(cargas);

      const lowStock = (productosData as Producto[]).filter((p: Producto) =>
        (p.tipo === 'hilo' || p.tipo === 'quimico') &&
        p.stock_minimo > 0
      );
      setAlertas(lowStock.slice(0, 5));

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

  const handleCrearOrden = async () => {
    if (!nuevaOrdenForm.codigo || !nuevaOrdenForm.peso_neto_requerido || !nuevaOrdenForm.producto_entrada || !nuevaOrdenForm.bodega_entrada || !nuevaOrdenForm.producto_salida || !nuevaOrdenForm.bodega_salida) {
      toast.error('Completa todos los campos obligatorios');
      return;
    }
    setIsSubmittingOrden(true);
    try {
      const payload: Record<string, unknown> = {
        codigo: nuevaOrdenForm.codigo,
        peso_neto_requerido: parseFloat(nuevaOrdenForm.peso_neto_requerido),
        producto_entrada: parseInt(nuevaOrdenForm.producto_entrada),
        bodega_entrada: parseInt(nuevaOrdenForm.bodega_entrada),
        producto_salida: parseInt(nuevaOrdenForm.producto_salida),
        bodega_salida: parseInt(nuevaOrdenForm.bodega_salida),
        area: profile?.user.area,
      };
      if (nuevaOrdenForm.formula_color) payload.formula_color = parseInt(nuevaOrdenForm.formula_color);
      if (nuevaOrdenForm.observaciones) payload.observaciones = nuevaOrdenForm.observaciones;

      await apiClient.post('/ordenes-produccion/', payload);
      toast.success('Orden de producción creada correctamente');
      setIsNuevaOrdenOpen(false);
      setNuevaOrdenForm({ codigo: '', peso_neto_requerido: '', producto_entrada: '', bodega_entrada: '', producto_salida: '', bodega_salida: '', formula_color: '', observaciones: '' });
      fetchDashboardData();
    } catch (error: any) {
      const msgs = error?.response?.data ? Object.entries(error.response.data).map(([k, v]) => `${k}: ${v}`).join(' | ') : 'Error al crear la orden';
      toast.error(msgs);
    } finally {
      setIsSubmittingOrden(false);
    }
  };

  const calculateMachineLoad = (maquina: Maquina) => {
    return maquinasCarga[maquina.id] || 0;
  };

  const totalAlertasPages = Math.max(1, Math.ceil(alertas.length / ITEMS_PER_PAGE));
  const safeAlertasPage = Math.min(Math.max(1, currentAlertasPage), totalAlertasPages);
  const paginatedAlertas = alertas.slice(
    (safeAlertasPage - 1) * ITEMS_PER_PAGE,
    safeAlertasPage * ITEMS_PER_PAGE
  );

  const totalLotesPages = Math.max(1, Math.ceil(lotes.length / ITEMS_PER_PAGE));
  const safeLotesPage = Math.min(Math.max(1, currentLotesPage), totalLotesPages);
  const paginatedLotes = lotes.slice(
    (safeLotesPage - 1) * ITEMS_PER_PAGE,
    safeLotesPage * ITEMS_PER_PAGE
  );

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
    <div className="flex flex-col h-full space-y-6 p-4">
      <div className="flex justify-between items-center flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Control - Área de Producción</h1>
          <p className="text-muted-foreground">Monitoreo en tiempo real de KPIs y maquinaria.</p>
        </div>
        <Button onClick={fetchDashboardData} variant="outline" size="sm">
          <Activity className="mr-2 h-4 w-4" /> Actualizar Datos
        </Button>
      </div>

      {/* KPIs Section */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 flex-shrink-0">
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
      <Card className="flex flex-col flex-1 min-h-0">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ListChecks className="h-5 w-5 text-blue-500" />
              <div>
                <CardTitle>Órdenes de Producción de tu Área</CardTitle>
                <CardDescription>Crea órdenes y asigna máquinas y personal para producirlas.</CardDescription>
              </div>
            </div>
            <Button size="sm" onClick={() => setIsNuevaOrdenOpen(true)}>
              <PlusCircle className="h-4 w-4 mr-2" />
              Nueva Orden
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto min-h-0">
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

      {/* Producción en curso — trazabilidad de transformaciones máquina a máquina */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-primary" /> Producción en Curso — Trazabilidad
          </CardTitle>
          <CardDescription>
            Registra cada transformación de máquina (cambio de código y merma) y consulta el flujo completo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {ordenes.filter(o => o.estado === 'en_proceso').length > 0 ? (
            <div className="space-y-3">
              {ordenes.filter(o => o.estado === 'en_proceso').map((orden) => (
                <div key={orden.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg bg-slate-50/50">
                  <div className="flex items-center gap-2 min-w-0">
                    <Badge variant="outline" className="font-mono text-[10px] text-blue-600 border-blue-200 bg-blue-50">{orden.codigo}</Badge>
                    <span className="font-medium text-slate-800 truncate">{orden.producto_nombre}</span>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => setTrazaOrdenId(orden.id)}>
                    <GitBranch className="mr-2 h-4 w-4" /> Ver flujo / Registrar
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-lg border border-dashed">
              <GitBranch className="h-8 w-8 text-muted-foreground mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">No hay órdenes en proceso en tu área.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Diálogo: timeline de trazabilidad + registro de transformaciones */}
      <Dialog open={trazaOrdenId !== null} onOpenChange={(o) => !o && setTrazaOrdenId(null)}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Flujo de Producción</DialogTitle>
            <DialogDescription>Transformaciones máquina a máquina de la orden seleccionada.</DialogDescription>
          </DialogHeader>
          {trazaOrdenId !== null && (
            <TrazabilidadProducto ordenId={trazaOrdenId} allowRegister />
          )}
        </DialogContent>
      </Dialog>

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-7 flex-shrink-0">

        {/* Machine Status Panel */}
        <Card className="col-span-4 flex flex-col h-auto">
          <CardHeader className="flex-shrink-0">
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-500" />
              Estado de Máquinas y Carga
            </CardTitle>
            <CardDescription>Monitoreo de capacidad, avance y personal asignado.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto min-h-0">
            <div className="space-y-4">
              {maquinas.map((m) => {
                const carga = calculateMachineLoad(m);
                const estadoColor = m.estado === 'operativa' ? 'bg-green-500/20 border-green-200' : m.estado === 'mantenimiento' ? 'bg-amber-500/20 border-amber-200' : 'bg-red-500/20 border-red-200';
                const estadoTextColor = m.estado === 'operativa' ? 'text-green-700' : m.estado === 'mantenimiento' ? 'text-amber-700' : 'text-red-700';

                return (
                  <div key={m.id} className={`p-4 border rounded-lg ${estadoColor} hover:shadow-md transition-all`}>
                    {/* Header con nombre y estado */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <div className={`h-3 w-3 rounded-full ${m.estado === 'operativa' ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]' : m.estado === 'mantenimiento' ? 'bg-amber-500' : 'bg-red-500'}`} />
                          <h4 className="font-bold text-sm">{m.nombre}</h4>
                          <Badge className={`text-[9px] font-medium ${m.estado === 'operativa' ? 'bg-green-100 text-green-800' : m.estado === 'mantenimiento' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'}`}>
                            {m.estado === 'operativa' ? '✓ Operativa' : m.estado === 'mantenimiento' ? '⚙ Mantenimiento' : '✕ Inactiva'}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">Capacidad: {m.capacidad_maxima} Kg/Turno</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEditMaquina(m)} title="Editar máquina">
                          <Settings2 className="h-4 w-4 text-gray-600" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleToggleEstadoMaquina(m)}
                          title={m.estado === 'operativa' ? 'Desactivar' : 'Activar'}
                        >
                          <Activity className={`h-4 w-4 ${m.estado === 'operativa' ? 'text-green-600' : 'text-gray-400'}`} />
                        </Button>
                      </div>
                    </div>

                    {/* Barra de carga/avance */}
                    <div className="mb-2">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-700">Avance de Carga</span>
                        <span className={`text-xs font-bold ${carga > 80 ? 'text-red-600' : carga > 60 ? 'text-amber-600' : 'text-green-600'}`}>
                          {carga}%
                        </span>
                      </div>
                      <Progress value={carga} className="h-2.5 rounded-full" />
                    </div>

                    {/* Operarios asignados */}
                    <div className="mt-3">
                      <p className="text-xs font-medium text-gray-700 mb-2">
                        Operarios Asignados ({m.operarios_nombres?.length || 0})
                      </p>
                      {m.operarios_nombres && m.operarios_nombres.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {m.operarios_nombres.map((name, i) => (
                            <Badge key={i} variant="secondary" className="bg-blue-100 text-blue-900 text-[11px] font-normal">
                              👤 {name}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground italic">Sin operarios asignados</p>
                      )}
                    </div>
                  </div>
                );
              })}
              {maquinas.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-lg border border-dashed">
                  <Zap className="w-8 h-8 text-muted-foreground mb-2 opacity-50" />
                  <p className="text-sm text-muted-foreground">No hay máquinas registradas en esta área.</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Alerts Panel */}
        <Card className="col-span-3 flex flex-col h-[400px]">
          <CardHeader className="flex-shrink-0">
            <CardTitle>Alertas de Inventario</CardTitle>
            <CardDescription>Productos químicos e hilos bajo mínimo.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto min-h-0">
            <div className="space-y-2">
              {paginatedAlertas.map((prod) => (
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
            {alertas.length > 0 && (
              <div className="flex items-center justify-between mt-4">
                <span className="text-sm text-muted-foreground">
                  Página {safeAlertasPage} de {totalAlertasPages}
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentAlertasPage((p) => Math.max(1, p - 1))}
                    disabled={safeAlertasPage === 1}
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Anterior
                  </Button>
                  <span className="flex items-center gap-1 text-sm">
                    <span className="text-muted-foreground">Ir a</span>
                    <Input
                      type="number"
                      min={1}
                      max={totalAlertasPages}
                      defaultValue={safeAlertasPage}
                      key={safeAlertasPage}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          const v = parseInt((e.target as HTMLInputElement).value, 10);
                          if (!isNaN(v) && v >= 1 && v <= totalAlertasPages) setCurrentAlertasPage(v);
                        }
                      }}
                      onBlur={(e) => {
                        const v = parseInt(e.target.value, 10);
                        if (!isNaN(v) && v >= 1 && v <= totalAlertasPages) setCurrentAlertasPage(v);
                      }}
                      className="w-14 h-8 text-center py-0 px-1"
                    />
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentAlertasPage((p) => Math.min(totalAlertasPages, p + 1))}
                    disabled={safeAlertasPage === totalAlertasPages}
                  >
                    Siguiente
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Lotes Management */}
      <Card className="flex flex-col flex-shrink-0 mb-6">
        <CardHeader className="flex-shrink-0">
          <CardTitle>Gestión de Lotes Recientes</CardTitle>
          <CardDescription>Visualiza y gestiona la producción reciente.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
              <TableRow>
                <TableHead>Lote</TableHead>
                <TableHead>Máquina</TableHead>
                <TableHead>Operario</TableHead>
                <TableHead>Peso (Kg)</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedLotes.map((lote) => (
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
          </div>
          {lotes.length > 0 && (
            <div className="flex items-center justify-between mt-4 px-4 pb-4">
              <span className="text-sm text-muted-foreground">
                Página {safeLotesPage} de {totalLotesPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentLotesPage((p) => Math.max(1, p - 1))}
                  disabled={safeLotesPage === 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Anterior
                </Button>
                <span className="flex items-center gap-1 text-sm">
                  <span className="text-muted-foreground">Ir a</span>
                  <Input
                    type="number"
                    min={1}
                    max={totalLotesPages}
                    defaultValue={safeLotesPage}
                    key={safeLotesPage}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        const v = parseInt((e.target as HTMLInputElement).value, 10);
                        if (!isNaN(v) && v >= 1 && v <= totalLotesPages) setCurrentLotesPage(v);
                      }
                    }}
                    onBlur={(e) => {
                      const v = parseInt(e.target.value, 10);
                      if (!isNaN(v) && v >= 1 && v <= totalLotesPages) setCurrentLotesPage(v);
                    }}
                    className="w-14 h-8 text-center py-0 px-1"
                  />
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentLotesPage((p) => Math.min(totalLotesPages, p + 1))}
                  disabled={safeLotesPage === totalLotesPages}
                >
                  Siguiente
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      {/* Flujo de Producción - Visualización General */}
      {profile?.user.area && (
        <FlujoProduccion />
      )}

      {/* Etapas de Producción - Configuración */}
      {profile?.user.area && (
        <EtapasProduccion areaId={profile.user.area} />
      )}

      {/* Gestión avanzada de máquinas con merma */}
      <Card className="flex-shrink-0">
        <CardHeader>
          <CardTitle>Gestión de Máquinas</CardTitle>
          <CardDescription>Administra máquinas, estados y configuración de merma vendible.</CardDescription>
        </CardHeader>
        <CardContent>
          <ManageMaquinas areaId={profile?.user.area ?? undefined} />
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

      {/* Diálogo: Nueva Orden de Producción */}
      <Dialog open={isNuevaOrdenOpen} onOpenChange={setIsNuevaOrdenOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Nueva Orden de Producción</DialogTitle>
            <DialogDescription>
              Crea una orden para tu área. Define el producto que entra, el que sale y las bodegas correspondientes.
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label htmlFor="op-codigo">Código de Orden <span className="text-destructive">*</span></Label>
              <Input
                id="op-codigo"
                placeholder="Ej: OP-TINT-001"
                value={nuevaOrdenForm.codigo}
                onChange={(e) => setNuevaOrdenForm(f => ({ ...f, codigo: e.target.value }))}
              />
            </div>

            <div className="col-span-2">
              <Label htmlFor="op-peso">Peso Requerido (kg) <span className="text-destructive">*</span></Label>
              <Input
                id="op-peso"
                type="number"
                step="0.001"
                placeholder="500.000"
                value={nuevaOrdenForm.peso_neto_requerido}
                onChange={(e) => setNuevaOrdenForm(f => ({ ...f, peso_neto_requerido: e.target.value }))}
              />
            </div>

            <div>
              <Label>Producto de Entrada <span className="text-destructive">*</span></Label>
              <Select value={nuevaOrdenForm.producto_entrada} onValueChange={(v) => setNuevaOrdenForm(f => ({ ...f, producto_entrada: v }))}>
                <SelectTrigger><SelectValue placeholder="Producto que entra" /></SelectTrigger>
                <SelectContent>
                  {productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.codigo} — {p.descripcion}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Bodega de Entrada <span className="text-destructive">*</span></Label>
              <Select value={nuevaOrdenForm.bodega_entrada} onValueChange={(v) => setNuevaOrdenForm(f => ({ ...f, bodega_entrada: v }))}>
                <SelectTrigger><SelectValue placeholder="Bodega origen" /></SelectTrigger>
                <SelectContent>
                  {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Producto de Salida <span className="text-destructive">*</span></Label>
              <Select value={nuevaOrdenForm.producto_salida} onValueChange={(v) => setNuevaOrdenForm(f => ({ ...f, producto_salida: v }))}>
                <SelectTrigger><SelectValue placeholder="Producto que sale" /></SelectTrigger>
                <SelectContent>
                  {productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.codigo} — {p.descripcion}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Bodega de Salida <span className="text-destructive">*</span></Label>
              <Select value={nuevaOrdenForm.bodega_salida} onValueChange={(v) => setNuevaOrdenForm(f => ({ ...f, bodega_salida: v }))}>
                <SelectTrigger><SelectValue placeholder="Bodega destino" /></SelectTrigger>
                <SelectContent>
                  {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div className="col-span-2">
              <Label>Fórmula de Color (opcional)</Label>
              <Select value={nuevaOrdenForm.formula_color} onValueChange={(v) => setNuevaOrdenForm(f => ({ ...f, formula_color: v }))}>
                <SelectTrigger><SelectValue placeholder="Sin fórmula asignada" /></SelectTrigger>
                <SelectContent>
                  {formulas.map(fc => <SelectItem key={fc.id} value={fc.id.toString()}>{fc.codigo} — {fc.nombre_color}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div className="col-span-2">
              <Label htmlFor="op-obs">Observaciones</Label>
              <Textarea
                id="op-obs"
                placeholder="Indicaciones adicionales..."
                value={nuevaOrdenForm.observaciones}
                onChange={(e) => setNuevaOrdenForm(f => ({ ...f, observaciones: e.target.value }))}
                rows={2}
                className="resize-none"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsNuevaOrdenOpen(false)}>Cancelar</Button>
            <Button onClick={handleCrearOrden} disabled={isSubmittingOrden}>
              {isSubmittingOrden ? 'Creando...' : 'Crear Orden'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}