import React, { useEffect, useState } from 'react';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../ui/sheet';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { GitCompare } from 'lucide-react';
import apiClient from '../../lib/axios';
import type { DiffVersionesFormula, SnapshotDetalle, SnapshotFase, VersionFormulaResumen } from '../../lib/types';

interface VersionesFormulaSheetProps {
  formula: { id: number; codigo: string; nombre_color: string } | null;
  onOpenChange: (open: boolean) => void;
}

const formatoFecha = (iso: string) => new Date(iso).toLocaleString('es-EC', { dateStyle: 'medium', timeStyle: 'short' });

const valorTexto = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v));

function CambiosCampos({ cambios }: { cambios: Record<string, { a: unknown; b: unknown }> }) {
  return (
    <ul className="space-y-0.5">
      {Object.entries(cambios).map(([campo, { a, b }]) => (
        <li key={campo} className="text-xs font-mono">
          <span className="text-muted-foreground">{campo}:</span>{' '}
          <span className="line-through text-red-600">{valorTexto(a)}</span> →{' '}
          <span className="text-emerald-700 font-semibold">{valorTexto(b)}</span>
        </li>
      ))}
    </ul>
  );
}

const nombreDetalle = (d: SnapshotDetalle) => d.producto_descripcion || d.producto_codigo || `Producto ${d.producto_id}`;
const nombreFase = (f: SnapshotFase) => `Fase ${f.orden}: ${f.proceso_nombre || f.proceso_codigo}`;

function DiffVista({ diff }: { diff: DiffVersionesFormula }) {
  const { formula, fases } = diff.cambios;
  const sinCambios = Object.keys(formula).length === 0 && fases.agregadas.length === 0
    && fases.eliminadas.length === 0 && fases.modificadas.length === 0;
  if (sinCambios) {
    return <p className="text-sm text-muted-foreground">Las versiones v{diff.a} y v{diff.b} son idénticas.</p>;
  }
  return (
    <div className="space-y-3 text-sm">
      {Object.keys(formula).length > 0 && (
        <div>
          <h4 className="font-semibold mb-1">Datos de la fórmula</h4>
          <CambiosCampos cambios={formula} />
        </div>
      )}
      {fases.agregadas.map((f) => (
        <div key={`add-${f.orden}`} className="text-emerald-700">+ {nombreFase(f)} (agregada)</div>
      ))}
      {fases.eliminadas.map((f) => (
        <div key={`del-${f.orden}`} className="text-red-600">− {nombreFase(f)} (eliminada)</div>
      ))}
      {fases.modificadas.map((f) => (
        <div key={`mod-${f.orden}`} className="border rounded-md p-2 space-y-1">
          <h4 className="font-semibold">Fase {f.orden} ({f.proceso_codigo})</h4>
          <CambiosCampos cambios={f.cambios} />
          {f.detalles.agregados.map((d) => (
            <div key={`da-${d.producto_id}`} className="text-xs text-emerald-700">+ {nombreDetalle(d)}</div>
          ))}
          {f.detalles.eliminados.map((d) => (
            <div key={`de-${d.producto_id}`} className="text-xs text-red-600">− {nombreDetalle(d)}</div>
          ))}
          {f.detalles.modificados.map((d) => (
            <div key={`dm-${d.producto_id}`} className="text-xs">
              <span className="font-medium">{d.producto_codigo || `Producto ${d.producto_id}`}</span>
              <CambiosCampos cambios={d.cambios} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/** Panel lateral con el historial de versiones de una fórmula y la comparación entre dos
 *  de ellas (spec 2026-09-24 §7). Carga sus propios datos al abrirse. */
export function VersionesFormulaSheet({ formula, onOpenChange }: VersionesFormulaSheetProps) {
  const [versiones, setVersiones] = useState<VersionFormulaResumen[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [numeroA, setNumeroA] = useState<string>('');
  const [numeroB, setNumeroB] = useState<string>('');
  const [diff, setDiff] = useState<DiffVersionesFormula | null>(null);
  const [comparando, setComparando] = useState(false);

  useEffect(() => {
    if (!formula) return;
    let vigente = true;
    setCargando(true);
    setError(null);
    setDiff(null);
    apiClient.get<VersionFormulaResumen[]>(`/formula-colors/${formula.id}/versiones/`)
      .then(({ data }) => {
        if (!vigente) return;
        setVersiones(data);
        // Por defecto se compara la penúltima con la última (la lista viene descendente)
        setNumeroB(data[0] ? String(data[0].numero) : '');
        setNumeroA(data[1] ? String(data[1].numero) : '');
      })
      .catch(() => vigente && setError('No se pudo cargar el historial de versiones.'))
      .finally(() => vigente && setCargando(false));
    return () => { vigente = false; };
  }, [formula]);

  const comparar = async () => {
    if (!formula || !numeroA || !numeroB) return;
    setComparando(true);
    setError(null);
    try {
      const { data } = await apiClient.get<DiffVersionesFormula>(
        `/formula-colors/${formula.id}/versiones/${numeroA}/diff/${numeroB}/`);
      setDiff(data);
    } catch {
      setError('No se pudo comparar las versiones.');
    } finally {
      setComparando(false);
    }
  };

  return (
    <Sheet open={!!formula} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Historial de versiones</SheetTitle>
          <SheetDescription>{formula ? `${formula.codigo} — ${formula.nombre_color}` : ''}</SheetDescription>
        </SheetHeader>

        <div className="px-4 pb-4 space-y-4">
          {cargando && <p className="text-sm text-muted-foreground">Cargando historial...</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {!cargando && !error && versiones.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Esta fórmula aún no tiene versiones: se crea la primera al aprobarla.
            </p>
          )}

          <ol className="space-y-2">
            {versiones.map((v) => (
              <li key={v.id} className="border rounded-md p-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-bold">v{v.numero}</span>
                  {v.es_oficial && (
                    <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 hover:bg-emerald-100">Oficial</Badge>
                  )}
                </div>
                <p className="mt-1">{v.motivo}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {formatoFecha(v.fecha)}{v.creada_por_nombre ? ` · ${v.creada_por_nombre}` : ''}
                </p>
              </li>
            ))}
          </ol>

          {versiones.length >= 2 && (
            <div className="border-t pt-4 space-y-3">
              <h3 className="font-semibold flex items-center gap-2"><GitCompare className="w-4 h-4" /> Comparar versiones</h3>
              <div className="grid grid-cols-2 gap-3">
                {([['Desde', numeroA, setNumeroA], ['Hasta', numeroB, setNumeroB]] as const).map(([etiqueta, valor, setValor]) => (
                  <div key={etiqueta} className="space-y-1">
                    <Label>{etiqueta}</Label>
                    <Select value={valor} onValueChange={(v) => { setValor(v); setDiff(null); }}>
                      <SelectTrigger aria-label={`Versión ${etiqueta.toLowerCase()}`}><SelectValue placeholder="Versión" /></SelectTrigger>
                      <SelectContent>
                        {versiones.map((v) => (
                          <SelectItem key={v.id} value={String(v.numero)}>v{v.numero}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>
              <Button type="button" size="sm" onClick={comparar} disabled={comparando || !numeroA || !numeroB || numeroA === numeroB}>
                {comparando ? 'Comparando...' : 'Comparar'}
              </Button>
              {diff && <DiffVista diff={diff} />}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
