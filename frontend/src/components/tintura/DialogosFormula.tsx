import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import type { TipoSustrato } from '../../lib/types';

/** Mínimo exigido por el backend para observaciones/motivo (VersionFormula.motivo). */
export const OBSERVACIONES_MIN = 10;

interface FormulaRef {
  id: number;
  codigo: string;
  nombre_color: string;
}

interface CrearVersionDialogProps {
  formula: FormulaRef | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: (id: number, observaciones: string) => Promise<boolean>;
}

/** Congela la receta viva como una versión nueva, NO oficial (regla 1, D7): un ensayo.
 * Distinto de «marcar oficial», que se hace después sobre una versión ya creada. */
export function CrearVersionDialog({ formula, onOpenChange, onConfirm }: CrearVersionDialogProps) {
  const [observaciones, setObservaciones] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { setObservaciones(''); }, [formula]);

  const valido = observaciones.trim().length >= OBSERVACIONES_MIN;

  const confirmar = async () => {
    if (!formula || !valido) return;
    setEnviando(true);
    try {
      if (await onConfirm(formula.id, observaciones.trim())) onOpenChange(false);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Dialog open={!!formula} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Guardar versión (ensayo)</DialogTitle>
          <DialogDescription>
            {formula && `${formula.codigo} — ${formula.nombre_color}. `}
            Congela la receta actual como un ensayo nuevo. No se marca oficial automáticamente.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="observaciones-ensayo">Observaciones del ensayo</Label>
          <Textarea
            id="observaciones-ensayo"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            placeholder="Ej: sale muy rojizo, falta igualación"
          />
          {observaciones.length > 0 && !valido && (
            <span className="text-xs text-red-500">Debe tener al menos {OBSERVACIONES_MIN} caracteres.</span>
          )}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="button" onClick={confirmar} disabled={!valido || enviando}>
            {enviando ? 'Guardando...' : 'Guardar versión'}
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
            {formula && `Copia la receta viva de ${formula.codigo} en una fórmula nueva, en pruebas y sin versiones.`}
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

const SUSTRATOS: TipoSustrato[] = ['algodon', 'poliester', 'nylon', 'mixto', 'otro'];

export interface DerivarFormulaDatos {
  codigo: string;
  nombre_color: string;
  tipo_sustrato?: TipoSustrato;
  motivo_derivacion?: string;
  es_laboratorio?: boolean;
}

interface DerivarFormulaDialogProps {
  /** Fórmula origen y número de la versión concreta (oficial o ensayo) de la que se deriva. */
  origen: (FormulaRef & { numeroVersion: number }) | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: (id: number, datos: DerivarFormulaDatos & { version_origen: number }) => Promise<boolean>;
}

/** Crea una fórmula nueva a partir del snapshot de una versión concreta de otra
 * (oficial o ensayo, a elección del tintorero — D8-D9). */
export function DerivarFormulaDialog({ origen, onOpenChange, onConfirm }: DerivarFormulaDialogProps) {
  const [codigo, setCodigo] = useState('');
  const [nombreColor, setNombreColor] = useState('');
  const [tipoSustrato, setTipoSustrato] = useState<TipoSustrato | ''>('');
  const [motivo, setMotivo] = useState('');
  const [esLaboratorio, setEsLaboratorio] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    setCodigo(''); setNombreColor(''); setTipoSustrato(''); setMotivo(''); setEsLaboratorio(false);
  }, [origen]);

  const valido = codigo.trim() !== '' && nombreColor.trim() !== '';

  const confirmar = async () => {
    if (!origen || !valido) return;
    setEnviando(true);
    try {
      const ok = await onConfirm(origen.id, {
        codigo: codigo.trim(),
        nombre_color: nombreColor.trim().toUpperCase(),
        tipo_sustrato: tipoSustrato || undefined,
        motivo_derivacion: motivo.trim() || undefined,
        es_laboratorio: esLaboratorio,
        version_origen: origen.numeroVersion,
      });
      if (ok) onOpenChange(false);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Dialog open={!!origen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Derivar fórmula</DialogTitle>
          <DialogDescription>
            {origen && `Copia la v${origen.numeroVersion} de ${origen.codigo} en una fórmula nueva, con su propio ciclo de versionado.`}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <div className="space-y-1">
            <Label htmlFor="derivar-codigo">Código</Label>
            <Input id="derivar-codigo" value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="Ej: FQ-2000" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="derivar-nombre">Nombre del color</Label>
            <Input id="derivar-nombre" value={nombreColor} onChange={(e) => setNombreColor(e.target.value)} className="uppercase" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="derivar-sustrato">Sustrato (opcional; por defecto el del origen)</Label>
            <Select value={tipoSustrato} onValueChange={(v) => setTipoSustrato(v as TipoSustrato)}>
              <SelectTrigger id="derivar-sustrato"><SelectValue placeholder="Igual que el origen" /></SelectTrigger>
              <SelectContent>
                {SUSTRATOS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="derivar-motivo">Motivo de la derivación (opcional)</Label>
            <Textarea id="derivar-motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)}
                     placeholder="Ej: cambio de sustrato a nylon" />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={esLaboratorio} onChange={(e) => setEsLaboratorio(e.target.checked)} />
            Fórmula de laboratorio (no se muestra en el listado por defecto)
          </label>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="button" onClick={confirmar} disabled={!valido || enviando}>
            {enviando ? 'Derivando...' : 'Derivar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
