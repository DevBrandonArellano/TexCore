import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';

/** Mínimo exigido por el backend (VersionFormula.motivo, AprobarFormulaSerializer). */
export const MOTIVO_MIN = 10;

interface FormulaRef {
  id: number;
  codigo: string;
  nombre_color: string;
}

interface AprobarFormulaDialogProps {
  formula: FormulaRef | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: (id: number, motivo: string) => Promise<boolean>;
}

/** Aprobar crea la versión oficial nº 1 de la fórmula (regla 2): exige un motivo. */
export function AprobarFormulaDialog({ formula, onOpenChange, onConfirm }: AprobarFormulaDialogProps) {
  const [motivo, setMotivo] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { setMotivo(''); }, [formula]);

  const motivoValido = motivo.trim().length >= MOTIVO_MIN;

  const confirmar = async () => {
    if (!formula || !motivoValido) return;
    setEnviando(true);
    try {
      if (await onConfirm(formula.id, motivo.trim())) onOpenChange(false);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Dialog open={!!formula} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Aprobar fórmula</DialogTitle>
          <DialogDescription>
            {formula && `${formula.codigo} — ${formula.nombre_color}. `}
            Se creará la versión oficial con la receta actual; las órdenes que se lancen usarán esa versión.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="motivo-aprobacion">Motivo de la aprobación</Label>
          <Textarea
            id="motivo-aprobacion"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Ej: Aprobada tras prueba de laboratorio"
          />
          {motivo.length > 0 && !motivoValido && (
            <span className="text-xs text-red-500">El motivo debe tener al menos {MOTIVO_MIN} caracteres.</span>
          )}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="button" onClick={confirmar} disabled={!motivoValido || enviando}>
            {enviando ? 'Aprobando...' : 'Aprobar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface CrearVarianteDialogProps {
  formula: FormulaRef | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: (id: number, datos: { codigo: string; nombre_color: string }) => Promise<boolean>;
}

/** «Duplicar» crea una variante: una fórmula nueva, en pruebas, con código y color propios. */
export function CrearVarianteDialog({ formula, onOpenChange, onConfirm }: CrearVarianteDialogProps) {
  const [codigo, setCodigo] = useState('');
  const [nombreColor, setNombreColor] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { setCodigo(''); setNombreColor(''); }, [formula]);

  const valido = codigo.trim() !== '' && nombreColor.trim() !== '';

  const confirmar = async () => {
    if (!formula || !valido) return;
    setEnviando(true);
    try {
      const ok = await onConfirm(formula.id, { codigo: codigo.trim(), nombre_color: nombreColor.trim().toUpperCase() });
      if (ok) onOpenChange(false);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Dialog open={!!formula} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Crear variante</DialogTitle>
          <DialogDescription>
            {formula && `Copia la receta de ${formula.codigo} en una fórmula nueva, en pruebas y sin versiones.`}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <div className="space-y-1">
            <Label htmlFor="variante-codigo">Código</Label>
            <Input id="variante-codigo" value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="Ej: FQ-1002-B" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="variante-nombre">Nombre del color</Label>
            <Input id="variante-nombre" value={nombreColor} onChange={(e) => setNombreColor(e.target.value)} className="uppercase" />
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="button" onClick={confirmar} disabled={!valido || enviando}>
            {enviando ? 'Creando...' : 'Crear variante'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
