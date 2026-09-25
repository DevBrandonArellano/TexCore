import React, { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from '../ui/sheet';
import { Separator } from '../ui/separator';
import { Progress } from '../ui/progress';
import { Pencil, Trash2, ClipboardList, PlusCircle, Play, CheckCircle2, Droplets } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { OrdenProduccion, Sede, Area, Bodega, FormulaColor } from '../../lib/types';
import { TrazabilidadProducto } from '../produccion/TrazabilidadProducto';
import { getOrdenVencimientoStatus, estadoBadge, prioridadBadge } from './ordenUtils';

interface OrdenDetalleSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orden: OrdenProduccion | null;
  onEdit: (orden: OrdenProduccion) => void;
  onDelete: (id: number) => void;
  onStatusChange: (id: number, newStatus: 'en_proceso' | 'finalizada') => void;
  onOpenLotDialog: (orden: OrdenProduccion) => void;
  onOpenRequisitosDialog: (orden: OrdenProduccion) => void;
  sedes: Sede[];
  areas: Area[];
  bodegas: Bodega[];
  formulas: FormulaColor[];
  onDataRefresh?: () => void;
}

const DetailRow = ({ label, value }: { label: string; value?: string | null }) => (
  <div className="flex flex-col gap-0.5">
    <span className="text-xs text-muted-foreground">{label}</span>
    <span className="text-sm font-medium">{value || <span className="text-muted-foreground italic">—</span>}</span>
  </div>
);

function OrdenDetalleSheetImpl({
  open,
  onOpenChange,
  orden,
  onEdit,
  onDelete,
  onStatusChange,
  onOpenLotDialog,
  onOpenRequisitosDialog,
  sedes,
  areas,
  bodegas,
  formulas,
  onDataRefresh,
}: OrdenDetalleSheetProps) {
  const [litrosBano, setLitrosBano] = useState('');
  const [guardandoLitros, setGuardandoLitros] = useState(false);

  useEffect(() => {
    setLitrosBano(orden?.litros_bano != null ? String(orden.litros_bano) : '');
  }, [orden?.id, orden?.litros_bano]);

  if (!orden) return null;

  const { isOverdue, isToday } = getOrdenVencimientoStatus(orden);
  const pesoProd = Number(orden.peso_producido || 0);
  const pesoReq = Number(orden.peso_neto_requerido || 0);
  const porcentaje = pesoReq > 0 ? Math.min(100, Math.round((pesoProd / pesoReq) * 100)) : 0;

  const handleGuardarLitros = async () => {
    const valor = parseFloat(litrosBano);
    if (isNaN(valor) || valor <= 0) {
      toast.error('Ingresa un número de litros mayor a cero.');
      return;
    }
    let justificacion: string | undefined;
    if (orden.inventario_descontado) {
      justificacion = window.prompt(
        'Esta orden ya tiene químicos descontados. Indica una justificación para ajustar los litros de baño:'
      ) || '';
      if (!justificacion.trim()) {
        toast.error('La justificación es obligatoria para modificar una orden con químicos descontados.');
        return;
      }
    }
    try {
      setGuardandoLitros(true);
      await apiClient.patch(`/ordenes-produccion/${orden.id}/`, {
        litros_bano: valor,
        ...(justificacion ? { justificacion } : {}),
      });
      toast.success('Litros de baño actualizados.');
      onDataRefresh?.();
    } catch (error: any) {
      const detalle = error?.response?.data;
      toast.error(detalle ? JSON.stringify(detalle) : 'Error al guardar los litros de baño.');
    } finally {
      setGuardandoLitros(false);
    }
  };

  // Resolver nombres desde catálogos (la API solo devuelve IDs para estos campos)
  const ordenAny = orden as any;
  const productoNombre = ordenAny.producto_entrada_detail?.descripcion || orden.producto_nombre;
  const formulaNombre = formulas.find(f => f.id === orden.formula_color)?.nombre_color;
  const sedeNombre = sedes.find(s => s.id === orden.sede)?.nombre;
  const areaNombre = areas.find(a => a.id === orden.area)?.nombre;
  const bodegaEntradaNombre = bodegas.find(b => b.id === ordenAny.bodega_entrada)?.nombre;
  const bodegaQuimicosNombre = bodegas.find(b => b.id === orden.bodega_quimicos)?.nombre;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto flex flex-col gap-0 p-0">
        <SheetHeader className="p-6 pb-4 border-b">
          <div className="flex items-center gap-2 flex-wrap">
            <SheetTitle className="font-mono text-lg">{orden.codigo}</SheetTitle>
            {estadoBadge(orden.estado)}
            {prioridadBadge(orden.prioridad)}
            {isOverdue && <Badge variant="destructive" className="text-xs">Vencida</Badge>}
            {isToday && !isOverdue && <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-xs">Vence hoy</Badge>}
          </div>
          <SheetDescription>Detalle completo de la orden de producción</SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* General */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Información General</h3>
            <div className="grid grid-cols-2 gap-3">
              <DetailRow label="Producto" value={productoNombre} />
              <DetailRow label="Fórmula Color" value={formulaNombre} />
              <DetailRow label="Sede" value={sedeNombre} />
              <DetailRow label="Área Responsable" value={areaNombre} />
            </div>
          </div>

          <Separator />

          {orden.pedido_venta && (
            <div className="bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900 rounded-lg p-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-purple-900 dark:text-purple-300 uppercase tracking-wide">
                  Fabricación Bajo Pedido (MTO)
                </span>
                <Badge className="bg-purple-200 text-purple-900 border-purple-300 text-xs">
                  Pedido #{orden.pedido_venta}
                </Badge>
              </div>
              <p className="text-xs text-purple-800 dark:text-purple-400">
                Esta orden está vinculada directamente al pedido comercial #{orden.pedido_venta}
                {orden.detalle_pedido ? ` (ítem #${orden.detalle_pedido})` : ''}.
                Los lotes producidos quedarán reservados exclusivamente para este cliente.
              </p>
            </div>
          )}

          {/* Progreso */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Progreso de Producción</h3>
            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">{pesoProd} / {pesoReq} Kg</span>
                <span className="font-semibold">{porcentaje}%</span>
              </div>
              <Progress value={porcentaje} className="h-2" />
            </div>
            {orden.inventario_descontado && (
              <Badge className="bg-green-100 text-green-800 border-green-200 w-fit">✓ Químicos descontados</Badge>
            )}
          </div>

          <Separator />

          {/* Baño de tintura (spec 2026-09-24 D3): litros es el dato canónico, la
              relación de baño (litros / peso) se deriva y se muestra de solo lectura. */}
          {orden.formula_color && (
            <>
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                  <Droplets className="w-3.5 h-3.5" /> Baño de Tintura
                </h3>
                <div className="flex items-end gap-2">
                  <div className="flex-1 space-y-1">
                    <Label htmlFor="litros-bano" className="text-xs text-muted-foreground">Litros de Baño</Label>
                    <Input
                      id="litros-bano"
                      type="number"
                      step="0.01"
                      className="h-9"
                      value={litrosBano}
                      onChange={(e) => setLitrosBano(e.target.value)}
                      placeholder="Ej: 860"
                    />
                  </div>
                  <Button size="sm" onClick={handleGuardarLitros} disabled={guardandoLitros}>
                    {guardandoLitros ? 'Guardando...' : 'Guardar'}
                  </Button>
                </div>
                <DetailRow
                  label="Relación de Baño"
                  value={orden.relacion_bano ? `1:${Number(orden.relacion_bano).toFixed(2)}` : 'Aún no calculada'}
                />
              </div>
              <Separator />
            </>
          )}

          {/* Fechas */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Fechas</h3>
            <div className="grid grid-cols-2 gap-3">
              <DetailRow label="Inicio Planificado" value={orden.fecha_inicio_planificada || undefined} />
              <div className="flex flex-col gap-0.5">
                <span className="text-xs text-muted-foreground">Fin Planificado</span>
                <span className={`text-sm font-medium ${isOverdue ? 'text-red-600' : isToday ? 'text-amber-600' : ''}`}>
                  {orden.fecha_fin_planificada || <span className="text-muted-foreground italic">—</span>}
                </span>
              </div>
              <DetailRow label="Fecha de Creación" value={orden.fecha_creacion ? orden.fecha_creacion.split('T')[0] : undefined} />
            </div>
          </div>

          <Separator />

          {/* Almacén */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Almacén</h3>
            <div className="grid grid-cols-2 gap-3">
              <DetailRow label="Bodega Entrada" value={bodegaEntradaNombre} />
              <DetailRow label="Bodega Químicos" value={bodegaQuimicosNombre} />
            </div>
          </div>

          {(orden.observaciones || orden.justificacion) && (
            <>
              <Separator />
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Notas</h3>
                {orden.observaciones && (
                  <div className="rounded-md bg-muted px-3 py-2 text-sm">{orden.observaciones}</div>
                )}
                {orden.justificacion && (
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs text-muted-foreground">Justificación</span>
                    <div className="rounded-md bg-muted px-3 py-2 text-sm">{orden.justificacion}</div>
                  </div>
                )}
              </div>
            </>
          )}

          <Separator />

          {/* Trazabilidad de transformaciones (supervisión — solo lectura) */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Flujo de Transformaciones</h3>
            <TrazabilidadProducto ordenId={orden.id} />
          </div>
        </div>

        <SheetFooter className="border-t p-4 flex flex-col gap-2">
          {/* Cambio de estado */}
          {orden.estado === 'pendiente' && (
            <Button
              className="w-full"
              variant="outline"
              onClick={() => onStatusChange(orden.id, 'en_proceso')}
            >
              <Play className="w-4 h-4 mr-2" /> Iniciar Proceso
            </Button>
          )}
          {orden.estado === 'en_proceso' && (
            <Button
              className="w-full"
              variant="outline"
              onClick={() => onStatusChange(orden.id, 'finalizada')}
            >
              <CheckCircle2 className="w-4 h-4 mr-2" /> Marcar como Finalizada
            </Button>
          )}

          {/* Acciones secundarias */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onOpenRequisitosDialog(orden)}
            >
              <ClipboardList className="w-4 h-4 mr-2" /> Requisitos
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              disabled={orden.estado === 'finalizada'}
              onClick={() => onOpenLotDialog(orden)}
            >
              <PlusCircle className="w-4 h-4 mr-2" /> Lote
            </Button>
          </div>

          {/* Editar / Eliminar */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onEdit(orden)}
            >
              <Pencil className="w-4 h-4 mr-2" /> Editar
            </Button>
            <Button
              variant="destructive"
              className="flex-1"
              onClick={() => onDelete(orden.id)}
            >
              <Trash2 className="w-4 h-4 mr-2" /> Eliminar
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

export const OrdenDetalleSheet = React.memo(OrdenDetalleSheetImpl);
