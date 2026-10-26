import React, { useState } from 'react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';

interface RechazarLoteDialogProps {
  codigoLote: string | null;
  onConfirmar: (motivo: string) => Promise<boolean>;
  onClose: () => void;
}

/** Pide el motivo obligatorio del rechazo; se cierra solo si el rechazo tuvo éxito. */
export function RechazarLoteDialog({ codigoLote, onConfirmar, onClose }: RechazarLoteDialogProps) {
  const [motivo, setMotivo] = useState('');
  const [enviando, setEnviando] = useState(false);

  const cerrar = () => {
    setMotivo('');
    onClose();
  };

  const confirmar = async () => {
    setEnviando(true);
    const rechazado = await onConfirmar(motivo);
    setEnviando(false);
    if (rechazado) cerrar();
  };

  return (
    <Dialog open={codigoLote !== null} onOpenChange={(abierto) => !abierto && cerrar()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rechazar lote {codigoLote}</DialogTitle>
          <DialogDescription>Se revertirán los movimientos de inventario del lote.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="motivo-rechazo">Motivo del rechazo</Label>
          <Textarea id="motivo-rechazo" value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={cerrar} disabled={enviando}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={confirmar} disabled={enviando || !motivo.trim()}>
            Rechazar lote
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
