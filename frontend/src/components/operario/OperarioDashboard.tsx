import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { OrdenProduccion, LoteProduccion } from '../../lib/types';
import type { ConsumoInput, OrdenProduccion as OrdenProduccionNew } from '../../types/produccion';
import { Package, Scale, ClipboardList, Timer, History, Pencil, Check, X, TrendingUp, AlertTriangle, Trash2 } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Separator } from '../ui/separator';

export function OperarioDashboard() {
  const { profile } = useAuth();
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrden, setSelectedOrden] = useState<OrdenProduccion | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form State for Lote
  const [pesoNeto, setPesoNeto] = useState('');
  const [bobinas, setBobinas] = useState('1');
  const [pesoMerma, setPesoMerma] = useState('');
  const [tipoMerma, setTipoMerma] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Recent entries state
  const [ultimosLotes, setUltimosLotes] = useState<LoteProduccion[]>([]);
  const [loadingLotes, setLoadingLotes] = useState(false);
  const [editingLoteId, setEditingLoteId] = useState<number | null>(null);
  const [editPesoNeto, setEditPesoNeto] = useState('');
  const [editUnidades, setEditUnidades] = useState('');
  const [editPesoMerma, setEditPesoMerma] = useState('');
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  // Delete confirmation state
  const [deleteConfirmLote, setDeleteConfirmLote] = useState<LoteProduccion | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Consumos de mezcla
  const [consumos, setConsumos] = useState<Array<{
    lote_origen_id: number | null
    cantidad_kg: string
    genera_nuevo_lote: boolean
    label: string
  }>>([]);

  const fetchOrdenes = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get<OrdenProduccion[]>('/ordenes-produccion/');
      const data = Array.isArray(res.data) ? res.data : (res.data as any).results || [];
      const active = data.filter((o: any) => o.estado === 'en_proceso');
      setOrdenes(active);
    } catch (error) {
      console.error('Error al cargar órdenes', error);
      toast.error('No se pudieron cargar tus asignaciones.');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchUltimosLotes = useCallback(async () => {
    if (!profile?.user?.id) return;
    try {
      setLoadingLotes(true);
      const res = await apiClient.get<LoteProduccion[]>('/lotes-produccion/', {
        params: {
          operario: profile.user.id,
          ordering: '-hora_final',
        }
      });
      const data = Array.isArray(res.data) ? res.data : (res.data as any).results || [];
      // Client-side sort as safety net + limit to last 10 entries
      const sorted = data.sort((a: LoteProduccion, b: LoteProduccion) =>
        new Date(b.hora_final).getTime() - new Date(a.hora_final).getTime()
      );
      setUltimosLotes(sorted.slice(0, 10));
    } catch (error) {
      console.error('Error al cargar últimos lotes', error);
    } finally {
      setLoadingLotes(false);
    }
  }, [profile?.user?.id]);

  useEffect(() => {
    fetchOrdenes();
    fetchUltimosLotes();
  }, [fetchOrdenes, fetchUltimosLotes]);

  const handleOpenRegistro = (orden: OrdenProduccion) => {
    setSelectedOrden(orden);
    setPesoNeto('');
    setBobinas('1');
    setPesoMerma('');
    setTipoMerma('');
    // Inicializar consumos si la OP tiene componentes de mezcla
    const ordenAny = orden as any;
    if (ordenAny.componentes_mezcla && ordenAny.componentes_mezcla.length > 0) {
      setConsumos(ordenAny.componentes_mezcla.map((c: any) => ({
        lote_origen_id: null,
        cantidad_kg: c.cantidad_kg,
        genera_nuevo_lote: true,
        label: c.producto_detail?.codigo ?? `Producto ${c.producto}`,
      })));
    } else {
      setConsumos([]);
    }
    setIsDialogOpen(true);
  };

  const handleRegistrarLote = async () => {
    if (!selectedOrden || !pesoNeto) return;

    setIsSubmitting(true);
    try {
      const now = new Date();
      // Simple logic: Start time is now - 1 hour (approx) or just now for logging
      // In a real app, the operator would "Start" then "Stop".
      // Assuming straightforward registration here.

      const payload = {
        codigo_lote: `${selectedOrden.codigo}-L${Math.floor(Math.random() * 1000)}`, // Backend or simple generation
        peso_neto_producido: parseFloat(pesoNeto),
        unidades_empaque: parseInt(bobinas),
        maquina: selectedOrden.maquina_asignada, // Auto-assign to the machine of the order
        operario: profile?.user.id,
        turno: 'Dia', // Default or selector
        hora_inicio: new Date(now.getTime() - 60 * 60 * 1000).toISOString(), // 1 hour ago
        hora_final: now.toISOString(),
        peso_merma: pesoMerma ? parseFloat(pesoMerma) : 0,
        tipo_merma: pesoMerma ? tipoMerma : null,
        ...(consumos.length > 0 && consumos.every(c => c.lote_origen_id !== null) ? {
          consumos: consumos.map(c => ({
            lote_origen_id: c.lote_origen_id!,
            cantidad_kg: c.cantidad_kg,
            genera_nuevo_lote: c.genera_nuevo_lote,
          }))
        } : {}),
      };

      await apiClient.post(`/ordenes-produccion/${selectedOrden.id}/registrar-lote/`, payload);
      toast.success('Lote registrado exitosamente');
      setIsDialogOpen(false);
      fetchOrdenes(); // Refresh to see if status changes
      fetchUltimosLotes(); // Refresh recent entries
    } catch (error: any) {
      console.error(error);
      toast.error('Error al registrar la producción');
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Edit handlers ---
  const handleStartEdit = (lote: LoteProduccion) => {
    setEditingLoteId(lote.id);
    setEditPesoNeto(String(lote.peso_neto_producido));
    setEditUnidades(String(lote.unidades_empaque || 1));
    setEditPesoMerma(String(lote.peso_merma ?? 0));
  };

  const handleCancelEdit = () => {
    setEditingLoteId(null);
    setEditPesoNeto('');
    setEditUnidades('');
    setEditPesoMerma('');
  };

  const handleSaveEdit = async (lote: LoteProduccion) => {
    if (!editPesoNeto || parseFloat(editPesoNeto) <= 0) {
      toast.error('El peso neto debe ser mayor a 0.');
      return;
    }

    setIsSavingEdit(true);
    try {
      await apiClient.patch(`/lotes-produccion/${lote.id}/`, {
        peso_neto_producido: parseFloat(editPesoNeto),
        unidades_empaque: parseInt(editUnidades) || 1,
        peso_merma: parseFloat(editPesoMerma) || 0,
      });
      toast.success('Lote actualizado correctamente');
      setEditingLoteId(null);
      fetchOrdenes();
      fetchUltimosLotes();
    } catch (error: any) {
      console.error(error);
      const detail = error?.response?.data?.detail || error?.response?.data?.peso_neto_producido?.[0] || 'Error al actualizar el lote';
      toast.error(String(detail));
    } finally {
      setIsSavingEdit(false);
    }
  };

  // --- Delete handler (with inventory reversion via rechazar endpoint) ---
  const handleDeleteLote = async () => {
    if (!deleteConfirmLote) return;

    setIsDeleting(true);
    try {
      await apiClient.post(`/lotes-produccion/${deleteConfirmLote.id}/rechazar/`);
      toast.success(`Lote ${deleteConfirmLote.codigo_lote} eliminado y movimientos revertidos.`);
      setDeleteConfirmLote(null);
      fetchOrdenes();
      fetchUltimosLotes();
    } catch (error: any) {
      console.error(error);
      const detail = error?.response?.data?.error || error?.response?.data?.detail || 'Error al eliminar el lote';
      toast.error(String(detail));
    } finally {
      setIsDeleting(false);
    }
  };

  // --- Helpers ---
  const getProgressPercent = (orden: OrdenProduccion): number => {
    const producido = Number(orden.peso_producido ?? 0);
    const requerido = Number(orden.peso_neto_requerido);
    if (requerido <= 0) return 0;
    return Math.min((producido / requerido) * 100, 100);
  };

  const getPendiente = (orden: OrdenProduccion): number => {
    const producido = Number(orden.peso_producido ?? 0);
    const requerido = Number(orden.peso_neto_requerido);
    return Math.max(requerido - producido, 0);
  };

  const formatDate = (dateStr: string): string => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-EC', {
        day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
      });
    } catch { return dateStr; }
  };

  const getOrdenCodigoForLote = (lote: LoteProduccion): string => {
    // Find orden from our loaded list
    const orden = ordenes.find(o => o.id === lote.orden_produccion);
    return orden?.codigo || `OP-${lote.orden_produccion}`;
  };

  if (loading) return <div className="p-6">Cargando asignaciones...</div>;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Panel de Operario</h1>
        <p className="text-muted-foreground">
          Bienvenido, {profile?.user.username}. Aquí están tus órdenes de producción activas.
        </p>
      </div>

      {/* === ORDERS SECTION === */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {ordenes.length > 0 ? (
          ordenes.map((orden) => {
            const progress = getProgressPercent(orden);
            const pendiente = getPendiente(orden);
            const producido = Number(orden.peso_producido ?? 0);
            const isNearComplete = progress >= 90 && progress < 100;
            const isComplete = progress >= 100;

            return (
              <Card key={orden.id} className="border-l-4 border-l-blue-500 shadow-sm hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Package className="h-5 w-5 text-blue-600" />
                        {orden.producto_nombre}
                      </CardTitle>
                      <CardDescription className="font-mono text-xs mt-1">
                        OP: {orden.codigo}
                      </CardDescription>
                    </div>
                    <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                      En Proceso
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex flex-col">
                      <span className="text-muted-foreground text-xs">Fórmula</span>
                      <span className="font-medium truncate" title={orden.formula_color_nombre}>{orden.formula_color_nombre}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-muted-foreground text-xs">Meta</span>
                      <span className="font-medium">{orden.peso_neto_requerido} Kg</span>
                    </div>
                  </div>

                  {/* === PROGRESS SECTION === */}
                  <div className="space-y-2 bg-slate-50 dark:bg-slate-900 rounded-lg p-3 border">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <TrendingUp className="h-3.5 w-3.5" />
                        Avance
                      </span>
                      <span className="font-bold text-sm">
                        {progress.toFixed(1)}%
                      </span>
                    </div>
                    <Progress
                      value={progress}
                      className="h-2.5"
                    />
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="flex flex-col">
                        <span className="text-muted-foreground">Producido</span>
                        <span className="font-semibold text-green-700 dark:text-green-400">{producido.toFixed(2)} Kg</span>
                      </div>
                      <div className="flex flex-col text-right">
                        <span className="text-muted-foreground">Pendiente</span>
                        <span className={`font-semibold ${isComplete ? 'text-green-600' : isNearComplete ? 'text-amber-600' : 'text-red-600'}`}>
                          {pendiente.toFixed(2)} Kg
                        </span>
                      </div>
                    </div>
                    {isNearComplete && !isComplete && (
                      <div className="flex items-center gap-1 text-xs text-amber-700 bg-amber-50 rounded px-2 py-1 border border-amber-200">
                        <AlertTriangle className="h-3 w-3 shrink-0" />
                        ¡Casi completada! Faltan {pendiente.toFixed(2)} Kg
                      </div>
                    )}
                    {isComplete && (
                      <div className="flex items-center gap-1 text-xs text-green-700 bg-green-50 rounded px-2 py-1 border border-green-200">
                        <Check className="h-3 w-3 shrink-0" />
                        Meta alcanzada
                      </div>
                    )}
                  </div>

                  {orden.observaciones && (
                    <div className="bg-amber-50 p-2 rounded text-xs text-amber-800 border border-amber-100 flex gap-2">
                      <ClipboardList className="h-4 w-4 shrink-0" />
                      <span className="italic">"{orden.observaciones}"</span>
                    </div>
                  )}

                  <Button className="w-full mt-2" onClick={() => handleOpenRegistro(orden)}>
                    <Scale className="mr-2 h-4 w-4" /> Registrar Avance
                  </Button>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <div className="col-span-full flex flex-col items-center justify-center p-12 bg-slate-50 border border-dashed rounded-lg text-muted-foreground">
            <Timer className="h-10 w-10 mb-2 opacity-20" />
            <p>No tienes órdenes de producción asignadas en este momento.</p>
            <p className="text-sm">Contacta a tu Jefe de Área si crees que es un error.</p>
          </div>
        )}
      </div>

      {/* === RECENT ENTRIES SECTION === */}
      <Separator />
      <div>
        <div className="flex items-center gap-2 mb-4">
          <History className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-xl font-semibold tracking-tight">Últimos Ingresos</h2>
          <Badge variant="outline" className="ml-auto text-xs">
            {ultimosLotes.length} registros
          </Badge>
        </div>

        {loadingLotes ? (
          <div className="text-muted-foreground text-sm p-4">Cargando últimos ingresos...</div>
        ) : ultimosLotes.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 bg-slate-50 border border-dashed rounded-lg text-muted-foreground">
            <History className="h-8 w-8 mb-2 opacity-20" />
            <p className="text-sm">No hay registros de producción aún.</p>
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[130px]">Lote</TableHead>
                      <TableHead>Orden</TableHead>
                      <TableHead className="text-right">Peso Neto (Kg)</TableHead>
                      <TableHead className="text-right">Unidades</TableHead>
                      <TableHead className="text-right">Merma (Kg)</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead className="text-center w-[120px]">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ultimosLotes.map((lote) => (
                      <TableRow key={lote.id} className={editingLoteId === lote.id ? 'bg-blue-50 dark:bg-blue-950/30' : ''}>
                        <TableCell className="font-mono text-xs">
                          {lote.codigo_lote}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {getOrdenCodigoForLote(lote)}
                        </TableCell>

                        {/* Peso Neto */}
                        <TableCell className="text-right">
                          {editingLoteId === lote.id ? (
                            <Input
                              type="number"
                              step="0.01"
                              value={editPesoNeto}
                              onChange={(e) => setEditPesoNeto(e.target.value)}
                              className="w-24 ml-auto text-right font-mono"
                              autoFocus
                            />
                          ) : (
                            <span className="font-medium font-mono">{Number(lote.peso_neto_producido).toFixed(2)}</span>
                          )}
                        </TableCell>

                        {/* Unidades */}
                        <TableCell className="text-right">
                          {editingLoteId === lote.id ? (
                            <Input
                              type="number"
                              value={editUnidades}
                              onChange={(e) => setEditUnidades(e.target.value)}
                              className="w-20 ml-auto text-right"
                            />
                          ) : (
                            <span>{lote.unidades_empaque || 1}</span>
                          )}
                        </TableCell>

                        {/* Merma */}
                        <TableCell className="text-right">
                          {editingLoteId === lote.id ? (
                            <Input
                              type="number"
                              step="0.01"
                              value={editPesoMerma}
                              onChange={(e) => setEditPesoMerma(e.target.value)}
                              className="w-24 ml-auto text-right font-mono"
                              placeholder="0.00"
                            />
                          ) : (
                            <span className="text-muted-foreground font-mono">
                              {lote.peso_merma ? Number(lote.peso_merma).toFixed(2) : '—'}
                            </span>
                          )}
                        </TableCell>

                        {/* Fecha */}
                        <TableCell className="text-xs text-muted-foreground">
                          {formatDate(lote.hora_final)}
                        </TableCell>

                        {/* Acciones */}
                        <TableCell className="text-center">
                          {editingLoteId === lote.id ? (
                            <div className="flex items-center justify-center gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-green-600 hover:text-green-700 hover:bg-green-50"
                                onClick={() => handleSaveEdit(lote)}
                                disabled={isSavingEdit}
                                title="Guardar"
                              >
                                <Check className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-red-500 hover:text-red-600 hover:bg-red-50"
                                onClick={handleCancelEdit}
                                disabled={isSavingEdit}
                                title="Cancelar"
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center justify-center gap-0.5">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-muted-foreground hover:text-blue-600"
                                onClick={() => handleStartEdit(lote)}
                                title="Editar registro"
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-muted-foreground hover:text-red-600 hover:bg-red-50"
                                onClick={() => setDeleteConfirmLote(lote)}
                                title="Eliminar y revertir"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Dialogo de Registro */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Registrar Producción</DialogTitle>
            <DialogDescription>
              Ingresa los detalles del lote producido para la orden <strong>{selectedOrden?.codigo}</strong>.
              {selectedOrden && (
                <span className="block mt-1 text-xs">
                  Pendiente: <strong className="text-red-600">{getPendiente(selectedOrden).toFixed(2)} Kg</strong> de {selectedOrden.peso_neto_requerido} Kg
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="peso" className="text-right">
                Peso Neto (Kg)
              </Label>
              <Input
                id="peso"
                type="number"
                step="0.01"
                value={pesoNeto}
                onChange={(e) => setPesoNeto(e.target.value)}
                className="col-span-3 font-mono text-lg"
                autoFocus
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="bobinas" className="text-right">
                Unidades
              </Label>
              <Input
                id="bobinas"
                type="number"
                value={bobinas}
                onChange={(e) => setBobinas(e.target.value)}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4 border-t pt-4 mt-2 border-dashed">
              <Label htmlFor="merma" className="text-right text-muted-foreground">
                Desperdicio (Kg)
              </Label>
              <Input
                id="merma"
                type="number"
                step="0.01"
                value={pesoMerma}
                onChange={(e) => setPesoMerma(e.target.value)}
                className="col-span-3"
                placeholder="0.00 (Opcional)"
              />
            </div>
            {parseFloat(pesoMerma) > 0 && (
              <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right text-muted-foreground">
                  Motivo
                </Label>
                <div className="col-span-3">
                  <Select value={tipoMerma} onValueChange={setTipoMerma}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona el motivo" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="maquina">Falla Técnica / Máquina</SelectItem>
                      <SelectItem value="material">Calidad de Hilo / Material</SelectItem>
                      <SelectItem value="setup">Arranque / Setup</SelectItem>
                      <SelectItem value="corte">Corte / Empalme</SelectItem>
                      <SelectItem value="otro">Otro</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
            {consumos.length > 0 && (
              <div className="space-y-3 border rounded-lg p-3 bg-muted/30">
                <p className="text-sm font-semibold">Lotes de Entrada (Mezcla)</p>
                {consumos.map((consumo, idx) => (
                  <div key={idx} className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <Label className="text-xs">{consumo.label} — ID lote origen</Label>
                      <Input
                        type="number"
                        placeholder="ID del lote de origen"
                        value={consumo.lote_origen_id ?? ''}
                        onChange={(e) => {
                          const updated = [...consumos]
                          updated[idx] = { ...updated[idx], lote_origen_id: parseInt(e.target.value) || null }
                          setConsumos(updated)
                        }}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Cantidad (kg)</Label>
                      <Input
                        type="number"
                        step="0.001"
                        value={consumo.cantidad_kg}
                        onChange={(e) => {
                          const updated = [...consumos]
                          updated[idx] = { ...updated[idx], cantidad_kg: e.target.value }
                          setConsumos(updated)
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSubmitting}>Cancelar</Button>
            <Button onClick={handleRegistrarLote} disabled={!pesoNeto || isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Confirmar Registro'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialogo de Confirmación de Eliminación */}
      <AlertDialog open={!!deleteConfirmLote} onOpenChange={(open) => { if (!open) setDeleteConfirmLote(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Eliminar Registro de Producción
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>
                  ¿Estás seguro de eliminar el lote <strong className="font-mono">{deleteConfirmLote?.codigo_lote}</strong>?
                </p>
                <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-md p-3 text-sm space-y-1">
                  <p className="font-medium text-red-800 dark:text-red-400">Esta acción revertirá:</p>
                  <ul className="list-disc list-inside text-red-700 dark:text-red-300 text-xs space-y-0.5">
                    <li>Se removerá <strong>{deleteConfirmLote ? Number(deleteConfirmLote.peso_neto_producido).toFixed(2) : 0} Kg</strong> del stock producido</li>
                    <li>Se devolverá la materia prima al inventario</li>
                    <li>Se revertirán los químicos consumidos</li>
                    <li>El registro del lote será eliminado permanentemente</li>
                  </ul>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteLote}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {isDeleting ? 'Eliminando...' : 'Eliminar y Revertir'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}