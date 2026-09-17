import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Factory, Play, CheckCircle2, Clock, AlertTriangle, Loader2 } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { getApiErrorMessage } from '../../lib/apiError';
import type { PedidoVenta, DetallePedido } from '../../lib/types';

interface SeguimientoPedidoMTOModalProps {
  pedido: PedidoVenta | null;
  isOpen: boolean;
  onClose: () => void;
  onOrderUpdated?: () => void;
}

export function SeguimientoPedidoMTOModal({
  pedido,
  isOpen,
  onClose,
  onOrderUpdated,
}: SeguimientoPedidoMTOModalProps) {
  const [generandoDetalleId, setGenerandoDetalleId] = useState<number | null>(null);
  const [prioridades, setPrioridades] = useState<Record<number, string>>({});

  if (!pedido) return null;

  const handlePrioridadChange = (detalleId: number, val: string) => {
    setPrioridades((prev) => ({ ...prev, [detalleId]: val }));
  };

  const handleGenerarOrdenMTO = async (detalle: DetallePedido) => {
    if (!pedido) return;
    const prioridad = prioridades[detalle.id] || 'alta';

    try {
      setGenerandoDetalleId(detalle.id);
      const res = await apiClient.post(`/pedidos-venta/${pedido.id}/generar-orden-mto/`, {
        detalle_pedido_id: detalle.id,
        prioridad,
        peso_solicitado: detalle.peso,
      });

      toast.success(
        `Orden de producción MTO ${res.data?.codigo || ''} generada exitosamente.`
      );
      if (onOrderUpdated) {
        onOrderUpdated();
      }
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Error al generar la orden de producción MTO'));
    } finally {
      setGenerandoDetalleId(null);
    }
  };

  const getEstadoBadge = (estado?: string) => {
    switch (estado) {
      case 'fabricado':
        return (
          <Badge className="bg-green-100 text-green-800 border-green-200 gap-1">
            <CheckCircle2 className="w-3 h-3" /> Fabricado
          </Badge>
        );
      case 'en_proceso':
        return (
          <Badge className="bg-blue-100 text-blue-800 border-blue-200 gap-1">
            <Clock className="w-3 h-3" /> En Proceso
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-amber-800 border-amber-300 bg-amber-50 gap-1">
            <AlertTriangle className="w-3 h-3" /> Pendiente Fabricación
          </Badge>
        );
    }
  };

  const detalles = pedido.detalles || [];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Factory className="w-6 h-6 text-indigo-600" />
            <DialogTitle className="text-xl">
              Seguimiento de Fabricación MTO — Pedido #{pedido.numero_pedido || pedido.id}
            </DialogTitle>
          </div>
          <DialogDescription>
            Trazabilidad y generación de órdenes de producción bajo pedido para cada ítem solicitado.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-muted/40 p-3 rounded-lg text-sm">
            <div>
              <span className="text-xs text-muted-foreground block">Cliente</span>
              <span className="font-semibold">{pedido.cliente_nombre || 'N/D'}</span>
            </div>
            <div>
              <span className="text-xs text-muted-foreground block">Fecha Pedido</span>
              <span>{new Date(pedido.fecha_pedido).toLocaleDateString()}</span>
            </div>
            <div>
              <span className="text-xs text-muted-foreground block">Estado Comercial</span>
              <Badge variant="outline">{pedido.estado}</Badge>
            </div>
            <div>
              <span className="text-xs text-muted-foreground block">Guía Remisión</span>
              <span>{pedido.guia_remision || 'Sin asignar'}</span>
            </div>
          </div>

          <div className="rounded-md border overflow-hidden">
            <Table>
              <TableHeader className="bg-slate-50">
                <TableRow>
                  <TableHead>Producto</TableHead>
                  <TableHead className="text-right">Solicitado</TableHead>
                  <TableHead className="text-right">Fabricado</TableHead>
                  <TableHead className="text-center">Avance</TableHead>
                  <TableHead className="text-center">Estado</TableHead>
                  <TableHead className="text-right">Acción MTO</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detalles.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                      No hay ítems registrados en este pedido.
                    </TableCell>
                  </TableRow>
                ) : (
                  detalles.map((det) => {
                    const solicitado = Number(det.peso) || 0;
                    const fabricado = Number(det.cantidad_fabricada) || 0;
                    const pct = solicitado > 0 ? Math.min(100, (fabricado / solicitado) * 100) : 0;
                    const isGenerando = generandoDetalleId === det.id;
                    const estado = det.estado_fabricacion || 'pendiente';
                    const puedeGenerarOP = estado !== 'fabricado' && !pedido.anulado;

                    return (
                      <TableRow key={det.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{det.producto_nombre || `Producto #${det.producto}`}</span>
                            <span className="text-xs text-muted-foreground">
                              ${Number(det.precio_unitario).toFixed(2)} / unidad
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">
                          {solicitado.toFixed(2)} kg
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium text-blue-700">
                          {fabricado.toFixed(2)} kg
                        </TableCell>
                        <TableCell className="w-36">
                          <div className="flex flex-col items-center gap-1">
                            <span className="text-xs font-semibold">{pct.toFixed(0)}%</span>
                            <Progress value={pct} className="h-2 w-full" />
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          {getEstadoBadge(estado)}
                        </TableCell>
                        <TableCell className="text-right">
                          {puedeGenerarOP ? (
                            <div className="flex items-center justify-end gap-2">
                              <Select
                                value={prioridades[det.id] || 'alta'}
                                onValueChange={(v) => handlePrioridadChange(det.id, v)}
                                disabled={isGenerando}
                              >
                                <SelectTrigger className="w-24 h-8 text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="baja">Baja</SelectItem>
                                  <SelectItem value="normal">Normal</SelectItem>
                                  <SelectItem value="alta">Alta</SelectItem>
                                </SelectContent>
                              </Select>
                              <Button
                                size="sm"
                                className="h-8 gap-1 bg-indigo-600 hover:bg-indigo-700 text-white"
                                onClick={() => handleGenerarOrdenMTO(det)}
                                disabled={isGenerando}
                              >
                                {isGenerando ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                  <Play className="w-3.5 h-3.5" />
                                )}
                                <span className="text-xs">Crear OP</span>
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              {pedido.anulado ? 'Pedido anulado' : 'Completado'}
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
