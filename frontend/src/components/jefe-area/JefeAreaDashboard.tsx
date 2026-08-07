import React, { useEffect, useMemo, useState } from 'react';
import { ManageMaquinas } from './ManageMaquinas';
import { ManageLineas } from './ManageLineas';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { AlertTriangle, Activity, Settings2, BarChart2, XCircle, CheckCircle, Layout, ListChecks, ClipboardList, ChevronLeft, ChevronRight, Zap, Share2, OctagonPause, Gauge } from 'lucide-react';
import { EtapasProduccion } from '../produccion/EtapasProduccion';
import { FlujoProduccion } from '../produccion/FlujoProduccion';
import { TrazabilidadProducto } from '../produccion/TrazabilidadProducto';
import { GitBranch } from 'lucide-react';
import { BuscadorLotes } from '../empaquetado/BuscadorLotes';
import apiClient from '../../lib/axios';

import { Maquina, KPIArea, Producto, LoteProduccion, User, OrdenProduccion, LineaProduccion, OeeResultado } from '../../lib/types';
import { RegistrarParoModal } from './RegistrarParoModal';
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

const ITEMS_PER_PAGE = 20;

// UX-1: semáforo de severidad para OEE — 85% es el benchmark de "clase mundial"
// (OEE for Operators — Productivity Press); 60% es un umbral típico de planta
// aceptable/en mejora. Por debajo de 60% se considera crítico.
function claseSeveridadOee(oee: number): string {
  if (oee >= 0.85) return 'text-green-600';
  if (oee >= 0.60) return 'text-amber-600';
  return 'text-red-600';
}

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

function MaquinaCardInline({
  m, carga, compartida, onEdit, onToggle, oee, onRegistrarParo,
}: {
  m: Maquina;
  carga: number;
  compartida: boolean;
  onEdit: (m: Maquina) => void;
  onToggle: (m: Maquina) => void;
  oee?: OeeResultado;
  onRegistrarParo: (m: Maquina) => void;
}) {
  const estadoColor =
    m.estado === 'operativa' ? 'bg-green-500/20 border-green-200' :
    m.estado === 'mantenimiento' ? 'bg-amber-500/20 border-amber-200' :
    'bg-red-500/20 border-red-200';

  return (
    <div className={`p-4 border rounded-lg ${estadoColor} hover:shadow-md transition-all`}>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-3 gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <div className={`h-3 w-3 rounded-full shrink-0 ${
              m.estado === 'operativa' ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]' :
              m.estado === 'mantenimiento' ? 'bg-amber-500' : 'bg-red-500'
            }`} />
            <h4 className="font-bold text-sm break-words">{m.nombre}</h4>
            <Badge className={`shrink-0 text-[9px] font-medium ${
              m.estado === 'operativa' ? 'bg-green-100 text-green-800' :
              m.estado === 'mantenimiento' ? 'bg-amber-100 text-amber-800' :
              'bg-red-100 text-red-800'
            }`}>
              {m.estado === 'operativa' ? '✓ Operativa' :
               m.estado === 'mantenimiento' ? '⚙ Mantenimiento' : '✕ Inactiva'}
            </Badge>
            {compartida && (
              <Badge variant="outline" className="shrink-0 text-[9px] gap-1 border-blue-300 text-blue-700 bg-blue-50">
                <Share2 className="h-2.5 w-2.5" />
                Recurso Compartido
              </Badge>
            )}
            {oee && (
              <Badge variant="outline" className="shrink-0 text-[9px] gap-1 border-purple-300 text-purple-700 bg-purple-50">
                OEE {(oee.oee * 100).toFixed(1)}%
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">Capacidad: {m.capacidad_maxima} Kg/Turno</p>
        </div>
        <div className="flex items-center gap-1 shrink-0 self-end sm:self-auto">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(m)} title="Editar máquina">
            <Settings2 className="h-4 w-4 text-gray-600" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => onToggle(m)}
            title={m.estado === 'operativa' ? 'Desactivar' : 'Activar'}
          >
            <Activity className={`h-4 w-4 ${m.estado === 'operativa' ? 'text-green-600' : 'text-gray-400'}`} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 gap-1 text-gray-600"
            onClick={() => onRegistrarParo(m)}
            title="Registrar Paro"
          >
            <OctagonPause className="h-4 w-4" />
            Paro
          </Button>
        </div>
      </div>

      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-700">Avance de Carga</span>
          <span className={`text-xs font-bold ${carga > 80 ? 'text-red-600' : carga > 60 ? 'text-amber-600' : 'text-green-600'}`}>
            {carga}%
          </span>
        </div>
        <Progress value={carga} className="h-2.5 rounded-full" />
      </div>

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
}

export function JefeAreaDashboard() {
  const { profile } = useAuth();
  const [kpis, setKpis] = useState<KPIArea | null>(null);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [alertas, setAlertas] = useState<Producto[]>([]);
  const [lotes, setLotes] = useState<LoteProduccion[]>([]);
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [operarios, setOperarios] = useState<User[]>([]);
  const [lineas, setLineas] = useState<LineaProduccion[]>([]);
  const [assignments, setAssignments] = useState<Record<number, { maquinaId: string, operarioId: string }>>({});
  const [isMaquinaDialogOpen, setIsMaquinaDialogOpen] = useState(false);
  const [selectedMaquina, setSelectedMaquina] = useState<Partial<Maquina> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [maquinasCarga, setMaquinasCarga] = useState<Record<number, number>>({});
  const [maquinasOee, setMaquinasOee] = useState<Record<number, OeeResultado>>({});
  const [currentAlertasPage, setCurrentAlertasPage] = useState(1);
  const [currentLotesPage, setCurrentLotesPage] = useState(1);
  const [trazaOrdenId, setTrazaOrdenId] = useState<number | null>(null);
  const [paroModalMaquina, setParoModalMaquina] = useState<{ id: number; nombre: string } | null>(null);

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
      const [kpiRes, maquinasRes, ordenesRes, usersRes, productosRes, lotesRes, lineasRes] = await Promise.all([
        apiClient.get<KPIArea>('/kpi-area/'),
        apiClient.get<Maquina[]>('/maquinas/'),
        apiClient.get<OrdenProduccion[]>('/ordenes-produccion/'),
        apiClient.get<User[]>('/users/'),
        apiClient.get<Producto[]>('/productos/'),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/'),
        apiClient.get<LineaProduccion[]>('/lineas-produccion/'),
      ]);

      setKpis(kpiRes.data);
      setMaquinas(Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || []);
      setOrdenes(Array.isArray(ordenesRes.data) ? ordenesRes.data : (ordenesRes.data as any).results || []);
      setOperarios(Array.isArray(usersRes.data) ? usersRes.data : (usersRes.data as any).results || []);
      setLotes(Array.isArray(lotesRes.data) ? lotesRes.data : (lotesRes.data as any).results || []);
      setLineas(Array.isArray(lineasRes.data) ? lineasRes.data : (lineasRes.data as any).results || []);

      // Extraer datos para cálculos
      const maquinasData = Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || [];
      const lotesData = Array.isArray(lotesRes.data) ? lotesRes.data : (lotesRes.data as any).results || [];
      const productosData = Array.isArray(productosRes.data) ? productosRes.data : (productosRes.data as any).results || [];

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

      // OEE por máquina (R4) — un GET por máquina; el área es pequeña por diseño (RBAC).
      const oeeEntries = await Promise.all(
        maquinasData.map(async (m: Maquina) => {
          try {
            const res = await apiClient.get<OeeResultado>(`/maquinas/${m.id}/oee/`);
            return [m.id, res.data] as const;
          } catch {
            return null;
          }
        })
      );
      const oeePorMaquina: Record<number, OeeResultado> = {};
      oeeEntries.forEach((entry) => {
        if (entry) oeePorMaquina[entry[0]] = entry[1];
      });
      setMaquinasOee(oeePorMaquina);

    } catch (error) {
      console.error("Error fetching dashboard data", error);
      toast.error("Error al cargar los datos del panel.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRechazarLote = async (loteId: number) => {
    // El backend exige `justificacion` no vacía (ISO 9001: causa del rechazo
    // trazable). Pedimos el motivo y lo enviamos; sin motivo se aborta.
    const motivo = window.prompt(
      "Motivo del rechazo del lote (requerido). Esta acción revertirá los movimientos de inventario:"
    );
    if (motivo === null) return; // el usuario canceló
    if (!motivo.trim()) {
      window.alert("Debes indicar un motivo para rechazar el lote.");
      return;
    }

    try {
      await apiClient.post(`/lotes-produccion/${loteId}/rechazar/`, { justificacion: motivo.trim() });
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

  // Agrupa máquinas por línea (TOC: la carga se calcula por área, no por línea).
  // 'compartida' viene del backend (>1 línea activa) — fuente de verdad única.
  const gruposPorLinea = useMemo(() => {
    const compartidaIds = new Set<number>(
      lineas.flatMap((l) =>
        (l.maquinas_detail ?? []).filter((d) => d.compartida).map((d) => d.id),
      ),
    );
    const asignadas = new Set<number>();
    const grupos = lineas.map((l) => {
      const ms = maquinas.filter((m) => l.maquinas.includes(m.id));
      ms.forEach((m) => asignadas.add(m.id));
      return { linea: l, maquinas: ms };
    });
    return { grupos, sinLinea: maquinas.filter((m) => !asignadas.has(m.id)), compartidaIds };
  }, [lineas, maquinas]);

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
    <div className="flex flex-col space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Panel de Control - Área de Producción</h1>
          <p className="text-sm text-muted-foreground">Monitoreo en tiempo real de KPIs y maquinaria.</p>
        </div>
        <Button onClick={fetchDashboardData} variant="outline" size="sm" className="self-start sm:self-auto">
          <Activity className="mr-2 h-4 w-4" /> Actualizar Datos
        </Button>
      </div>

      {/* KPIs Section */}
      {/* UX-2: en lg (no xl) 5 tarjetas en 3 columnas queda 3+2 (más equilibrado
          que el 4+1 de un grid a 2 columnas); en xl+ entran las 5 en una fila. */}
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
            <div className="text-2xl font-bold text-destructive">{alertas.length}</div>
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

      {/* Assignment Section */}
      <Card className="flex flex-col flex-1 min-h-0">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ListChecks className="h-5 w-5 text-blue-500" />
              <div>
                <CardTitle>Órdenes de Producción de tu Área</CardTitle>
                <CardDescription>Asigna máquinas y personal a las órdenes creadas por el Jefe de Planta.</CardDescription>
              </div>
            </div>
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

      {/* Buscador y Reetiquetado Supervisado de Lotes */}
      <BuscadorLotes />

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-7 flex-shrink-0">


        {/* Machine Status Panel */}
        <Card className="col-span-4 flex flex-col h-auto">
          <CardHeader className="flex-shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-500" />
                  Estado de Máquinas y Carga
                </CardTitle>
                <CardDescription>Monitoreo de capacidad, avance y personal asignado por célula de manufactura.</CardDescription>

              </div>
              <ManageLineas areaId={profile?.user.area ?? undefined} onChange={fetchDashboardData} />
            </div>
          </CardHeader>

          <CardContent className="flex-1 overflow-y-auto min-h-0">
            <div className="space-y-4">
              {gruposPorLinea.grupos.length === 0 && gruposPorLinea.sinLinea.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-lg border border-dashed">
                  <Zap className="w-8 h-8 text-muted-foreground mb-2 opacity-50" />
                  <p className="text-sm text-muted-foreground">No hay máquinas registradas en esta área.</p>
                </div>
              ) : gruposPorLinea.grupos.length === 0 ? (
                // Sin líneas: lista plana (comportamiento original)
                gruposPorLinea.sinLinea.map((m) => (
                  <MaquinaCardInline
                    key={m.id}
                    m={m}
                    carga={calculateMachineLoad(m)}
                    compartida={false}
                    onEdit={handleEditMaquina}
                    onToggle={handleToggleEstadoMaquina}
                    oee={maquinasOee[m.id]}
                    onRegistrarParo={(mm) => setParoModalMaquina({ id: mm.id, nombre: mm.nombre })}
                  />
                ))
              ) : (
                <>
                  {gruposPorLinea.grupos.map(({ linea, maquinas: ms }) => (
                    <div key={linea.id}>
                      <div className="flex items-center gap-2 mb-2 px-1">
                        <h5 className="text-sm font-semibold text-slate-700">{linea.nombre}</h5>
                        <Badge
                          variant={linea.estado === 'activa' ? 'default' : 'secondary'}
                          className="text-[9px]"
                        >
                          {linea.estado}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {ms.length} máquina{ms.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="space-y-3 pl-2 border-l-2 border-slate-200">
                        {ms.map((m) => (
                          <MaquinaCardInline
                            key={`${linea.id}-${m.id}`}
                            m={m}
                            carga={calculateMachineLoad(m)}
                            compartida={gruposPorLinea.compartidaIds.has(m.id)}
                            onEdit={handleEditMaquina}
                            onToggle={handleToggleEstadoMaquina}
                            oee={maquinasOee[m.id]}
                            onRegistrarParo={(mm) => setParoModalMaquina({ id: mm.id, nombre: mm.nombre })}
                          />
                        ))}
                        {ms.length === 0 && (
                          <p className="text-xs text-muted-foreground italic py-2">Sin máquinas asignadas</p>
                        )}
                      </div>
                    </div>
                  ))}
                  {gruposPorLinea.sinLinea.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2 px-1">
                        <h5 className="text-sm font-semibold text-slate-500">Sin línea</h5>
                        <span className="text-xs text-muted-foreground">
                          {gruposPorLinea.sinLinea.length} máquina{gruposPorLinea.sinLinea.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="space-y-3 pl-2 border-l-2 border-slate-100">
                        {gruposPorLinea.sinLinea.map((m) => (
                          <MaquinaCardInline
                            key={m.id}
                            m={m}
                            carga={calculateMachineLoad(m)}
                            compartida={false}
                            onEdit={handleEditMaquina}
                            onToggle={handleToggleEstadoMaquina}
                            oee={maquinasOee[m.id]}
                            onRegistrarParo={(mm) => setParoModalMaquina({ id: mm.id, nombre: mm.nombre })}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </>
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

      {/* Gestión de líneas de producción (células de manufactura flexible) */}
      <Card className="flex-shrink-0">
        <CardHeader>
          <CardTitle>Líneas de Producción</CardTitle>
          <CardDescription>
            Agrupa máquinas en células de manufactura flexible. Las máquinas compartidas entre líneas
            activas se marcan como "Recurso Compartido" para maximizar el OEE.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ManageLineas
            areaId={profile?.user.area ?? undefined}
            onChange={fetchDashboardData}
          />
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

      <RegistrarParoModal
        open={paroModalMaquina !== null}
        onOpenChange={(open) => !open && setParoModalMaquina(null)}
        maquinaId={paroModalMaquina?.id ?? null}
        maquinaNombre={paroModalMaquina?.nombre}
        onRegistrado={fetchDashboardData}
      />

    </div>
  );
}