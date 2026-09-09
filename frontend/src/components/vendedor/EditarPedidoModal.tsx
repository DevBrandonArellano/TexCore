import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Pencil } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import type { PedidoVenta } from '../../lib/types';

interface EditarPedidoModalProps {
  pedido: PedidoVenta | null;
  onClose: () => void;
  onSuccess: () => void;
}

function EditarPedidoModalImpl({ pedido, onClose, onSuccess }: EditarPedidoModalProps) {
  const [guiaRemision, setGuiaRemision] = useState('');
  const [fechaDespacho, setFechaDespacho] = useState('');
  const [valorRetencion, setValorRetencion] = useState('');
  const [estaPagado, setEstaPagado] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [saving, setSaving] = useState(false);

  React.useEffect(() => {
    if (!pedido) return;
    setGuiaRemision(pedido.guia_remision ?? '');
    setFechaDespacho(pedido.fecha_despacho ?? '');
    setValorRetencion(pedido.valor_retencion?.toString() ?? '0');
    setEstaPagado(pedido.esta_pagado);
    setMotivo('');
  }, [pedido]);

  const huboAlgunCambio = pedido && (
    guiaRemision !== (pedido.guia_remision ?? '') ||
    fechaDespacho !== (pedido.fecha_despacho ?? '') ||
    valorRetencion !== (pedido.valor_retencion?.toString() ?? '0') ||
    estaPagado !== pedido.esta_pagado
  );
  const esValido = !!huboAlgunCambio && motivo.trim().length >= 10;

  const handleGuardar = async () => {
    if (!pedido || !esValido) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { motivo: motivo.trim() };
      if (guiaRemision !== pedido.guia_remision) payload.guia_remision = guiaRemision;
      if (fechaDespacho !== (pedido.fecha_despacho ?? '')) payload.fecha_despacho = fechaDespacho || null;
      if (valorRetencion !== (pedido.valor_retencion?.toString() ?? '0')) payload.valor_retencion = parseFloat(valorRetencion) || 0;
      if (estaPagado !== pedido.esta_pagado) payload.esta_pagado = estaPagado;

      await apiClient.patch(`/pedidos-venta/${pedido.id}/modificar/`, payload);
      toast.success('Pedido actualizado correctamente');
      onSuccess();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.error ?? 'Error al modificar el pedido';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!pedido} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Pencil className="w-5 h-5" />
            Editar Pedido #{pedido?.id}
          </DialogTitle>
          <DialogDescription>
            Solo pedidos en estado <strong>Pendiente</strong>. Los cambios quedan registrados con auditoría.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label>Guía / Referencia</Label>
              <Input value={guiaRemision} onChange={(e) => setGuiaRemision(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Fecha Despacho</Label>
              <Input type="date" value={fechaDespacho} onChange={(e) => setFechaDespacho(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label>Valor Retención ($)</Label>
              <Input type="number" min="0" step="0.001" value={valorRetencion} onChange={(e) => setValorRetencion(e.target.value)} />
            </div>
            <div className="flex items-center gap-3 pt-5">
              <input
                type="checkbox"
                id="esta_pagado"
                checked={estaPagado}
                onChange={(e) => setEstaPagado(e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="esta_pagado">Marcar como pagado</Label>
            </div>
          </div>
          <div className="space-y-1">
            <Label>
              Motivo de modificación <span className="text-destructive">*</span>
            </Label>
            <Textarea
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Describe el motivo de la modificación..."
              rows={3}
            />
            <p className={`text-xs ${esValido ? 'text-muted-foreground' : 'text-destructive'}`}>
              {motivo.trim().length}/10 caracteres mínimos
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button onClick={handleGuardar} disabled={!esValido || saving}>
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const EditarPedidoModal = React.memo(EditarPedidoModalImpl);
