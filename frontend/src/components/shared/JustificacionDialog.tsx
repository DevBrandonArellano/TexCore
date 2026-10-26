import React, { useState } from 'react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';

interface JustificacionDialogProps {
  open: boolean;
  titulo: string;
  descripcion: string;
  textoConfirmar: string;
  /** Longitud mínima de la justificación, sin contar espacios de los extremos. */
  minLength?: number;
  /** Recibe la justificación recortada; devuelve `true` si la acción tuvo éxito. */
  onConfirmar: (justificacion: string) => Promise<boolean>;
  onClose: () => void;
}

/**
 * Pide la justificación obligatoria de una acción crítica (ISO 9001: causa trazable;
 * el backend la guarda en el AuditLog). Se cierra solo si la acción tuvo éxito.
 */
export function JustificacionDialog({
  open, titulo, descripcion, textoConfirmar, minLength = 10, onConfirmar, onClose,
}: JustificacionDialogProps) {
  const [justificacion, setJustificacion] = useState('');
  const [enviando, setEnviando] = useState(false);
  const recortada = justificacion.trim();
  const valida = recortada.length >= minLength;

  const cerrar = () => {
    setJustificacion('');
    onClose();
  };

  const confirmar = async () => {
    setEnviando(true);
    const ok = await onConfirmar(recortada);
    setEnviando(false);
    if (ok) cerrar();
  };

  return (
    <Dialog open={open} onOpenChange={(abierto) => !abierto && cerrar()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>{descripcion}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="justificacion-accion">Justificación</Label>
          <Textarea
            id="justificacion-accion"
            value={justificacion}
            onChange={(e) => setJustificacion(e.target.value)}
            rows={3}
          />
          <p className="text-xs text-muted-foreground">Mínimo {minLength} caracteres.</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={cerrar} disabled={enviando}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={confirmar} disabled={enviando || !valida}>
            {textoConfirmar}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
