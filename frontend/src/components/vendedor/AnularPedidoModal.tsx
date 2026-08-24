import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Ban } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import type { PedidoVenta } from '../../lib/types';

interface AnularPedidoModalProps {
  pedido: PedidoVenta | null;
  onClose: () => void;
  onSuccess: () => void;
}

function AnularPedidoModalImpl({ pedido, onClose, onSuccess }: AnularPedidoModalProps) {
  const [motivo, setMotivo] = useState('');
  const [saving, setSaving] = useState(false);

  React.useEffect(() => { if (pedido) setMotivo(''); }, [pedido]);

  const esValido = motivo.trim().length >= 10;

  const handleAnular = async () => {
    if (!pedido || !esValido) return;
    setSaving(true);
    try {
      await apiClient.post(`/pedidos-venta/${pedido.id}/anular/`, { motivo_anulacion: motivo.trim() });
      toast.success('Pedido anulado correctamente');
      onSuccess();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.error ?? 'Error al anular el pedido';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!pedido} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <Ban className="w-5 h-5" />
            Anular Pedido #{pedido?.id}
          </DialogTitle>
          <DialogDescription>
            Esta acción marca el pedido como anulado. Solo aplica a pedidos en estado <strong>Pendiente</strong>.
            El saldo del cliente se ajustará automáticamente.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
            <strong>Cliente:</strong> {pedido?.cliente_nombre}<br />
            <strong>Guía:</strong> {pedido?.guia_remision || '—'}
          </div>
          <div className="space-y-1">
            <Label>
              Motivo de anulación <span className="text-destructive">*</span>
            </Label>
            <Textarea
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Describe el motivo de la anulación..."
              rows={3}
            />
            <p className={`text-xs ${esValido ? 'text-muted-foreground' : 'text-destructive'}`}>
              {motivo.trim().length}/10 caracteres mínimos
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button variant="destructive" onClick={handleAnular} disabled={!esValido || saving}>
            {saving ? 'Anulando...' : 'Confirmar anulación'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const AnularPedidoModal = React.memo(AnularPedidoModalImpl);
