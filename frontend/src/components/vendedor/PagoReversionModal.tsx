import React from 'react';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { RotateCcw } from 'lucide-react';
import { format } from 'date-fns';
import type { PagoCliente } from '../../lib/types';

interface PagoReversionModalProps {
  pago: PagoCliente | null;
  justificacion: string;
  loading: boolean;
  onJustificacionChange: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}

function PagoReversionModalImpl({
  pago,
  justificacion,
  loading,
  onJustificacionChange,
  onClose,
  onConfirm,
}: PagoReversionModalProps) {
  const esValido = justificacion.trim().length >= 5;

  return (
    <Dialog open={!!pago} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <RotateCcw className="w-5 h-5" />
            Revertir Pago
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2 text-sm">
          {pago && (
            <>
              <div className="rounded-md bg-amber-50 border border-amber-200 p-3">
                <p className="text-xs text-amber-800 mb-2">
                  ⚠️ Esta acción restaurará la deuda del cliente al monto anterior.
                </p>
                <p><strong>Monto a revertir:</strong> ${parseFloat(pago.monto.toString()).toFixed(2)}</p>
                <p><strong>Fecha del pago:</strong> {format(new Date(pago.fecha), 'dd/MM/yyyy HH:mm')}</p>
                <p><strong>Método:</strong> {pago.metodo_pago}</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="justificacion" className="text-xs font-semibold">
                  Justificación obligatoria
                </Label>
                <Textarea
                  id="justificacion"
                  placeholder="Explica por qué se revierte este pago (mínimo 5 caracteres)"
                  value={justificacion}
                  onChange={(e) => onJustificacionChange(e.target.value)}
                  disabled={loading}
                  className="text-xs resize-none"
                  rows={3}
                />
                {justificacion.trim() && justificacion.trim().length < 5 && (
                  <p className="text-xs text-red-600">Mínimo 5 caracteres</p>
                )}
              </div>
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={!esValido || loading}
          >
            {loading ? 'Revirtiendo...' : 'Confirmar Reversión'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const PagoReversionModal = React.memo(PagoReversionModalImpl);
