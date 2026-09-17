import React, { useState, useEffect, useCallback } from 'react';
import {
  PlanProduccion,
  DetallePlanProduccion,
  NecesidadReposicion,
  Sede,
  Bodega,
  Maquina,
} from '../../lib/types';
import apiClient from '../../lib/axios';
import { getApiErrorMessage } from '../../lib/apiError';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import {
  Calendar,
  CheckCircle2,
  Clock,
  Layers,
  AlertTriangle,
  Play,
  PlusCircle,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  FileSpreadsheet,
} from 'lucide-react';

interface PlanProduccionMTSProps {
  sedes?: Sede[];
  bodegas?: Bodega[];
  maquinas?: Maquina[];
  selectedSedeId?: number | null;
}

export function PlanProduccionMTS({
  sedes = [],
  bodegas = [],
  maquinas = [],
  selectedSedeId,
}: PlanProduccionMTSProps) {
  const [planes, setPlanes] = useState<PlanProduccion[]>([]);
  const [necesidades, setNecesidades] = useState<NecesidadReposicion[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingAlertas, setLoadingAlertas] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'planes' | 'sugerencias'>('planes');
  const [filtroEstado, setFiltroEstado] = useState<string>('todos');

  // Modal para Generar OP desde Detalle
  const [selectedDetalle, setSelectedDetalle] = useState<DetallePlanProduccion | null>(null);
  const [selectedPlanForOP, setSelectedPlanForOP] = useState<PlanProduccion | null>(null);
  const [isOPModalOpen, setIsOPModalOpen] = useState<boolean>(false);
  const [opBodegaSalida, setOpBodegaSalida] = useState<string>('');
  const [opPrioridad, setOpPrioridad] = useState<string>('normal');
  const [opPesoRequerido, setOpPesoRequerido] = useState<string>('');
  const [isGeneratingOP, setIsGeneratingOP] = useState<boolean>(false);

  // Modal para Crear Plan desde Alertas
  const [isCrearPlanModalOpen, setIsCrearPlanModalOpen] = useState<boolean>(false);
  const [nuevoPlanCodigo, setNuevoPlanCodigo] = useState<string>('');
  const [nuevoPlanSedeId, setNuevoPlanSedeId] = useState<string>(selectedSedeId ? String(selectedSedeId) : '');
  const [nuevoPlanFechaInicio, setNuevoPlanFechaInicio] = useState<string>(
    new Date().toISOString().slice(0, 10)
  );
  const [nuevoPlanFechaFin, setNuevoPlanFechaFin] = useState<string>(
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
  );
  const [isCreatingPlan, setIsCreatingPlan] = useState<boolean>(false);

  const fetchPlanes = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (selectedSedeId) params.sede = String(selectedSedeId);
      if (filtroEstado !== 'todos') params.estado = filtroEstado;

      const res = await apiClient.get<any>('/planes-produccion/', { params });
      const results = res.data.results ? res.data.results : res.data;
      setPlanes(Array.isArray(results) ? results : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Error al cargar los planes de producción'));
    } finally {
      setLoading(false);
    }
  }, [selectedSedeId, filtroEstado]);

  const fetchNecesidades = useCallback(async () => {
    try {
      setLoadingAlertas(true);
      const params: Record<string, string> = {};
      if (selectedSedeId) params.sede = String(selectedSedeId);

      const res = await apiClient.get<NecesidadReposicion[]>(
        '/planes-produccion/necesidades-reposicion/',
        { params }
      );
      setNecesidades(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Error al consultar necesidades de reposición'));
    } finally {
      setLoadingAlertas(false);
    }
  }, [selectedSedeId]);

  useEffect(() => {
    fetchPlanes();
    fetchNecesidades();
  }, [fetchPlanes, fetchNecesidades]);

  const handleAprobarPlan = async (planId: number) => {
    try {
      await apiClient.post(`/planes-produccion/${planId}/aprobar/`);
      toast.success('Plan de producción aprobado correctamente');
      fetchPlanes();
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'No se pudo aprobar el plan'));
    }
  };

  const handleCerrarPlan = async (planId: number) => {
    try {
      await apiClient.post(`/planes-produccion/${planId}/cerrar/`);
      toast.success('Plan de producción cerrado correctamente');
      fetchPlanes();
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'No se pudo cerrar el plan'));
    }
  };

  const openGenerarOPDialog = (plan: PlanProduccion, detalle: DetallePlanProduccion) => {
    setSelectedPlanForOP(plan);
    setSelectedDetalle(detalle);
    setOpPesoRequerido(String(detalle.saldo_pendiente || detalle.cantidad_planificada));
    const primeraBodega = bodegas.length > 0 ? String(bodegas[0].id) : '';
    setOpBodegaSalida(primeraBodega);
    setOpPrioridad('normal');
    setIsOPModalOpen(true);
  };

  const handleGenerarOPSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanForOP || !selectedDetalle) return;

    try {
      setIsGeneratingOP(true);
      const payload = {
        detalle_plan_id: selectedDetalle.id,
        bodega_salida_id: opBodegaSalida ? Number(opBodegaSalida) : undefined,
        prioridad: opPrioridad,
        peso_solicitado: opPesoRequerido ? Number(opPesoRequerido) : undefined,
      };

      const res = await apiClient.post(
        `/planes-produccion/${selectedPlanForOP.id}/generar-orden/`,
        payload
      );
      toast.success(res.data?.mensaje || 'Orden de producción MTS generada exitosamente');
      setIsOPModalOpen(false);
      fetchPlanes();
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Error al generar la orden de producción'));
    } finally {
      setIsGeneratingOP(false);
    }
  };

  const handleCrearPlanDesdeAlertasSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nuevoPlanSedeId) {
      toast.error('Seleccione una sede para el plan');
      return;
    }

    if (necesidades.length === 0) {
      toast.warning('No existen déficits de stock detectados para generar un plan.');
      return;
    }

    try {
      setIsCreatingPlan(true);
      const items = necesidades.map(n => ({
        producto_id: n.producto_id,
        deficit: Number(n.deficit),
      }));

      const payload = {
        sede_id: Number(nuevoPlanSedeId),
        codigo: nuevoPlanCodigo.trim() || undefined,
        fecha_inicio: nuevoPlanFechaInicio,
        fecha_fin: nuevoPlanFechaFin,
        aprobar_inmediatamente: true,
        items,
      };

      await apiClient.post('/planes-produccion/crear-desde-alertas/', payload);
      toast.success('Plan de reposición creado y aprobado exitosamente a partir de alertas');
      setIsCrearPlanModalOpen(false);
      setActiveTab('planes');
      fetchPlanes();
      fetchNecesidades();
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Error al crear plan desde alertas'));
    } finally {
      setIsCreatingPlan(false);
    }
  };

  const getBadgeEstado = (estado: string) => {
    switch (estado) {
      case 'borrador':
        return <Badge variant="outline" className="text-slate-600 border-slate-300">Borrador</Badge>;
      case 'aprobado':
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200">Aprobado</Badge>;
      case 'en_ejecucion':
        return <Badge className="bg-amber-100 text-amber-800 border-amber-200">En Ejecución</Badge>;
      case 'cerrado':
        return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200">Cerrado</Badge>;
      case 'cancelado':
        return <Badge variant="destructive">Cancelado</Badge>;
      default:
        return <Badge>{estado}</Badge>;
    }
  };

  const getBadgeDetalleEstado = (estado: string) => {
    switch (estado) {
      case 'pendiente':
        return <Badge variant="outline" className="text-slate-500">Pendiente</Badge>;
      case 'en_proceso':
        return <Badge className="bg-indigo-100 text-indigo-800">En Proceso</Badge>;
      case 'completado':
        return <Badge className="bg-emerald-100 text-emerald-800">Completado</Badge>;
      case 'sobreproducido':
        return <Badge className="bg-purple-100 text-purple-800">Sobreproducido</Badge>;
      default:
        return <Badge>{estado}</Badge>;
    }
  };

  return (
    <Card className="border border-slate-200 shadow-sm">
      <CardHeader className="pb-3 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="text-xl font-bold flex items-center gap-2 text-slate-800">
              <Layers className="w-5 h-5 text-indigo-600" />
              Planificación y Producción Contra Stock (MTS)
            </CardTitle>
            <CardDescription>
              Control de reposición planificada, metas de stock mínimo y balance de desviación.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                fetchPlanes();
                fetchNecesidades();
              }}
              disabled={loading}
              className="gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
            {necesidades.length > 0 && (
              <Button
                size="sm"
                onClick={() => setIsCrearPlanModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                Crear Plan desde Déficits ({necesidades.length})
              </Button>
            )}
          </div>
        </div>

        {/* Pestañas internas */}
        <div className="flex gap-2 pt-4 border-b border-slate-100">
          <button
            type="button"
            onClick={() => setActiveTab('planes')}
            className={`pb-2.5 px-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'planes'
                ? 'border-indigo-600 text-indigo-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Planes de Producción MTS ({planes.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sugerencias')}
            className={`pb-2.5 px-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'sugerencias'
                ? 'border-indigo-600 text-indigo-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            Alertas de Stock Mínimo ({necesidades.length})
          </button>
        </div>
      </CardHeader>

      <CardContent className="pt-4">
        {activeTab === 'planes' && (
          <div className="space-y-4">
            {/* Filtro por estado */}
            <div className="flex items-center gap-2">
              <Label className="text-xs text-slate-500 font-medium">Filtrar Estado:</Label>
              <Select value={filtroEstado} onValueChange={setFiltroEstado}>
                <SelectTrigger className="w-44 h-8 text-xs">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos los Estados</SelectItem>
                  <SelectItem value="borrador">Borrador</SelectItem>
                  <SelectItem value="aprobado">Aprobado</SelectItem>
                  <SelectItem value="en_ejecucion">En Ejecución</SelectItem>
                  <SelectItem value="cerrado">Cerrado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {loading ? (
              <div className="py-12 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" /> Cargando planes de producción...
              </div>
            ) : planes.length === 0 ? (
              <div className="py-12 text-center text-slate-500 border border-dashed rounded-lg">
                <FileSpreadsheet className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                <p className="font-medium">No se encontraron planes de producción registrados.</p>
                <p className="text-xs text-slate-400 mt-1">
                  Genere un nuevo plan desde las alertas de stock mínimo o cargue una orden.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {planes.map(plan => (
                  <div
                    key={plan.id}
                    className="border border-slate-200 rounded-lg p-4 bg-white hover:border-slate-300 transition-all shadow-sm"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2.5">
                          <span className="font-bold text-slate-900 text-base">{plan.codigo}</span>
                          {getBadgeEstado(plan.estado)}
                          <span className="text-xs text-slate-400">
                            Sede: <strong className="text-slate-700">{plan.sede_nombre || plan.sede}</strong>
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            {plan.fecha_inicio} al {plan.fecha_fin}
                          </span>
                          {plan.supervisor_nombre && (
                            <span>Supervisor: <strong className="text-slate-600">{plan.supervisor_nombre}</strong></span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {plan.estado === 'borrador' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleAprobarPlan(plan.id)}
                            className="text-blue-700 border-blue-200 hover:bg-blue-50 text-xs h-8 gap-1"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Aprobar Plan
                          </Button>
                        )}
                        {plan.estado === 'en_ejecucion' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleCerrarPlan(plan.id)}
                            className="text-emerald-700 border-emerald-200 hover:bg-emerald-50 text-xs h-8 gap-1"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Cerrar Plan
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Tabla de detalles/renglones */}
                    <div className="mt-3 overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-50 text-slate-600 border-y border-slate-200 font-semibold">
                            <th className="py-2 px-3">Producto Objetivo</th>
                            <th className="py-2 px-2 text-right">Planificado</th>
                            <th className="py-2 px-2 text-right">Ejecutado</th>
                            <th className="py-2 px-2 text-right text-emerald-700">1ra Calidad</th>
                            <th className="py-2 px-2 text-right text-amber-700">2da Calidad</th>
                            <th className="py-2 px-2 text-right text-blue-700">Saldo Pendiente</th>
                            <th className="py-2 px-2 text-center">Cumplimiento</th>
                            <th className="py-2 px-2 text-center">Desviación</th>
                            <th className="py-2 px-2 text-center">Estado</th>
                            <th className="py-2 px-3 text-right">Acción</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {plan.detalles.map(det => {
                            const cump = Number(det.cumplimiento_porcentaje || 0);
                            const desv = Number(det.desviacion_porcentaje || 0);

                            return (
                              <tr key={det.id} className="hover:bg-slate-50/70 transition-colors">
                                <td className="py-2.5 px-3">
                                  <div className="font-semibold text-slate-800">{det.producto_objetivo_codigo}</div>
                                  <div className="text-[11px] text-slate-500 truncate max-w-xs">
                                    {det.producto_objetivo_descripcion}
                                  </div>
                                </td>
                                <td className="py-2.5 px-2 text-right font-medium">
                                  {Number(det.cantidad_planificada).toFixed(2)} {det.producto_objetivo_unidad}
                                </td>
                                <td className="py-2.5 px-2 text-right font-medium text-slate-700">
                                  {Number(det.cantidad_ejecutada).toFixed(2)} {det.producto_objetivo_unidad}
                                </td>
                                <td className="py-2.5 px-2 text-right font-bold text-emerald-700">
                                  {Number(det.cantidad_aceptada).toFixed(2)}
                                </td>
                                <td className="py-2.5 px-2 text-right font-medium text-amber-700">
                                  {Number(det.cantidad_segunda).toFixed(2)}
                                </td>
                                <td className="py-2.5 px-2 text-right font-bold text-blue-700">
                                  {Number(det.saldo_pendiente).toFixed(2)}
                                </td>
                                <td className="py-2.5 px-2 text-center">
                                  <div className="w-20 mx-auto">
                                    <div className="text-[11px] font-semibold text-slate-700 mb-0.5">{cump.toFixed(1)}%</div>
                                    <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full ${
                                          cump >= 100 ? 'bg-emerald-500' : cump >= 50 ? 'bg-blue-500' : 'bg-amber-500'
                                        }`}
                                        style={{ width: `${Math.min(100, cump)}%` }}
                                      />
                                    </div>
                                  </div>
                                </td>
                                <td className="py-2.5 px-2 text-center">
                                  <span
                                    className={`inline-flex items-center gap-0.5 text-[11px] font-semibold ${
                                      desv > 5
                                        ? 'text-purple-700'
                                        : desv >= 0
                                        ? 'text-emerald-700'
                                        : 'text-red-600'
                                    }`}
                                  >
                                    {desv > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                    {desv > 0 ? `+${desv.toFixed(1)}%` : `${desv.toFixed(1)}%`}
                                  </span>
                                </td>
                                <td className="py-2.5 px-2 text-center">
                                  {getBadgeDetalleEstado(det.estado)}
                                </td>
                                <td className="py-2.5 px-3 text-right">
                                  {plan.estado !== 'borrador' && plan.estado !== 'cerrado' && Number(det.saldo_pendiente) > 0 && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => openGenerarOPDialog(plan, det)}
                                      className="text-xs h-7 px-2 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 gap-1 font-semibold"
                                    >
                                      <Play className="w-3 h-3" />
                                      Generar OP
                                    </Button>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'sugerencias' && (
          <div className="space-y-4">
            {loadingAlertas ? (
              <div className="py-12 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" /> Analizando existencias contra stock mínimo...
              </div>
            ) : necesidades.length === 0 ? (
              <div className="py-12 text-center text-slate-500 border border-dashed rounded-lg">
                <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
                <p className="font-semibold text-slate-700">Stock en niveles óptimos</p>
                <p className="text-xs text-slate-400 mt-1">
                  Todos los productos cuentan con existencias superiores a su stock mínimo definido.
                </p>
              </div>
            ) : (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold">
                      <th className="py-2.5 px-3">Sede</th>
                      <th className="py-2.5 px-3">Código</th>
                      <th className="py-2.5 px-3">Descripción</th>
                      <th className="py-2.5 px-2">Tipo</th>
                      <th className="py-2.5 px-3 text-right">Stock Actual</th>
                      <th className="py-2.5 px-3 text-right">Stock Mínimo</th>
                      <th className="py-2.5 px-3 text-right text-red-700">Déficit (Reposición)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {necesidades.map((item, idx) => (
                      <tr key={`${item.producto_id}-${idx}`} className="hover:bg-slate-50 transition-colors">
                        <td className="py-2 px-3 text-slate-600">{item.sede_nombre}</td>
                        <td className="py-2 px-3 font-semibold text-slate-800">{item.producto_codigo}</td>
                        <td className="py-2 px-3 text-slate-700">{item.producto_descripcion}</td>
                        <td className="py-2 px-2">
                          <Badge variant="outline" className="text-[10px]">{item.tipo}</Badge>
                        </td>
                        <td className="py-2 px-3 text-right font-medium">
                          {Number(item.stock_actual).toFixed(2)} {item.unidad_medida}
                        </td>
                        <td className="py-2 px-3 text-right text-slate-600">
                          {Number(item.stock_minimo).toFixed(2)} {item.unidad_medida}
                        </td>
                        <td className="py-2 px-3 text-right font-bold text-red-600">
                          {Number(item.deficit).toFixed(2)} {item.unidad_medida}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </CardContent>

      {/* Modal para Generar OP desde Detalle de Plan */}
      <Dialog open={isOPModalOpen} onOpenChange={setIsOPModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Play className="w-5 h-5 text-indigo-600" />
              Generar Orden de Producción (MTS)
            </DialogTitle>
            <DialogDescription>
              Crear una OP formal conectada a la meta de stock planificada.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleGenerarOPSubmit} className="space-y-4 py-2">
            <div className="space-y-1">
              <Label className="text-xs">Producto Objetivo</Label>
              <div className="text-sm font-bold text-slate-800">
                {selectedDetalle?.producto_objetivo_codigo} - {selectedDetalle?.producto_objetivo_descripcion}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="opPesoRequerido" className="text-xs">Cantidad a Requerir ({selectedDetalle?.producto_objetivo_unidad})</Label>
                <Input
                  id="opPesoRequerido"
                  type="number"
                  step="0.01"
                  required
                  value={opPesoRequerido}
                  onChange={e => setOpPesoRequerido(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="opPrioridad" className="text-xs">Prioridad</Label>
                <Select value={opPrioridad} onValueChange={setOpPrioridad}>
                  <SelectTrigger id="opPrioridad" className="h-9 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="baja">Baja</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="alta">Alta</SelectItem>
                    <SelectItem value="urgente">Urgente</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1">
              <Label htmlFor="opBodegaSalida" className="text-xs">Bodega de Destino (PT)</Label>
              <Select value={opBodegaSalida} onValueChange={setOpBodegaSalida}>
                <SelectTrigger id="opBodegaSalida" className="h-9 text-sm">
                  <SelectValue placeholder="Seleccionar bodega" />
                </SelectTrigger>
                <SelectContent>
                  {bodegas.map(b => (
                    <SelectItem key={b.id} value={String(b.id)}>
                      {b.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <DialogFooter className="pt-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsOPModalOpen(false)}
                disabled={isGeneratingOP}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={isGeneratingOP}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {isGeneratingOP ? 'Generando OP...' : 'Lanzar Orden MTS'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal para Crear Plan desde Alertas de Stock */}
      <Dialog open={isCrearPlanModalOpen} onOpenChange={setIsCrearPlanModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-indigo-600" />
              Generar Plan desde Alertas de Stock
            </DialogTitle>
            <DialogDescription>
              Se incluirán automáticamente los {necesidades.length} productos con déficit bajo el stock mínimo.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCrearPlanDesdeAlertasSubmit} className="space-y-4 py-2">
            <div className="space-y-1">
              <Label htmlFor="nuevoPlanCodigo" className="text-xs">Código de Plan (Opcional)</Label>
              <Input
                id="nuevoPlanCodigo"
                placeholder="Ej. PLAN-MTS-2026-06"
                value={nuevoPlanCodigo}
                onChange={e => setNuevoPlanCodigo(e.target.value)}
                className="h-9 text-sm"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="nuevoPlanSede" className="text-xs">Sede</Label>
              <Select value={nuevoPlanSedeId} onValueChange={setNuevoPlanSedeId}>
                <SelectTrigger id="nuevoPlanSede" className="h-9 text-sm">
                  <SelectValue placeholder="Seleccionar sede" />
                </SelectTrigger>
                <SelectContent>
                  {sedes.map(s => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="nuevoPlanInicio" className="text-xs">Fecha de Inicio</Label>
                <Input
                  id="nuevoPlanInicio"
                  type="date"
                  required
                  value={nuevoPlanFechaInicio}
                  onChange={e => setNuevoPlanFechaInicio(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="nuevoPlanFin" className="text-xs">Fecha de Fin</Label>
                <Input
                  id="nuevoPlanFin"
                  type="date"
                  required
                  value={nuevoPlanFechaFin}
                  onChange={e => setNuevoPlanFechaFin(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
            </div>

            <DialogFooter className="pt-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCrearPlanModalOpen(false)}
                disabled={isCreatingPlan}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={isCreatingPlan}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {isCreatingPlan ? 'Creando Plan...' : 'Crear y Aprobar Plan'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
