import React from 'react';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Clock } from 'lucide-react';
import type { PedidoVenta } from '../../lib/types';

interface HistorialPedidoModalProps {
  pedido: PedidoVenta | null;
  onClose: () => void;
}

function HistorialPedidoModalImpl({ pedido, onClose }: HistorialPedidoModalProps) {
  if (!pedido) return null;
  return (
    <Dialog open={!!pedido} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Detalle de anulación — Pedido #{pedido.id}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2 text-sm">
          <div className="rounded-md bg-red-50 border border-red-200 p-3 space-y-2">
            <p><strong>Cliente:</strong> {pedido.cliente_nombre}</p>
            <p><strong>Guía:</strong> {pedido.guia_remision || '—'}</p>
            <p><strong>Anulado por:</strong> {pedido.anulado_por_nombre ?? '—'}</p>
            <p><strong>Fecha:</strong> {pedido.fecha_anulacion ? new Date(pedido.fecha_anulacion).toLocaleString('es-EC') : '—'}</p>
            <p><strong>Motivo:</strong></p>
            <p className="italic text-muted-foreground">{pedido.motivo_anulacion}</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const HistorialPedidoModal = React.memo(HistorialPedidoModalImpl);
