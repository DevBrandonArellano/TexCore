import React, { useCallback, useEffect, useState } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { GitCompare, PlusCircle, Split } from 'lucide-react';
import apiClient from '../../lib/axios';
import type { DiffVersionesFormula, SnapshotDetalle, SnapshotFase, VersionFormulaResumen } from '../../lib/types';
import { CrearVersionDialog, DerivarFormulaDialog, DerivarFormulaDatos } from './DialogosFormula';

interface FormulaRef {
  id: number;
  codigo: string;
  nombre_color: string;
}

interface VersionesFormulaPanelProps {
  formula: FormulaRef;
  onCrearVersion: (id: number, observaciones: string) => Promise<boolean>;
  onMarcarOficial: (id: number, numero: number) => Promise<boolean>;
  onDerivar: (id: number, datos: DerivarFormulaDatos & { version_origen: number }) => Promise<boolean>;
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

/** Historial de versiones de una fórmula, con comparador, «guardar versión» (ensayo),
 * «marcar oficial» y «derivar» por fila (spec 2026-09-24 §7, D7-D9). Contenido plano
 * pensado para vivir dentro de una pestaña (D10), no un panel lateral. */
export function VersionesFormulaPanel({ formula, onCrearVersion, onMarcarOficial, onDerivar }: VersionesFormulaPanelProps) {
  const [versiones, setVersiones] = useState<VersionFormulaResumen[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [numeroA, setNumeroA] = useState<string>('');
  const [numeroB, setNumeroB] = useState<string>('');
  const [diff, setDiff] = useState<DiffVersionesFormula | null>(null);
  const [comparando, setComparando] = useState(false);
  const [mostrarCrearVersion, setMostrarCrearVersion] = useState(false);
  const [derivarDesde, setDerivarDesde] = useState<number | null>(null);
  const [marcandoOficial, setMarcandoOficial] = useState<number | null>(null);

  const cargarVersiones = useCallback(() => {
    setCargando(true);
    setError(null);
    setDiff(null);
    return apiClient.get<VersionFormulaResumen[]>(`/formula-colors/${formula.id}/versiones/`)
      .then(({ data }) => {
        setVersiones(data);
        // Por defecto se compara la penúltima con la última (la lista viene descendente)
        setNumeroB(data[0] ? String(data[0].numero) : '');
        setNumeroA(data[1] ? String(data[1].numero) : '');
      })
      .catch(() => setError('No se pudo cargar el historial de versiones.'))
      .finally(() => setCargando(false));
  }, [formula.id]);

  useEffect(() => {
    let vigente = true;
    cargarVersiones().then(() => { if (!vigente) return; });
    return () => { vigente = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formula.id]);

  const comparar = async () => {
    if (!numeroA || !numeroB) return;
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

  const guardarVersion = async (id: number, observaciones: string) => {
    const ok = await onCrearVersion(id, observaciones);
    if (ok) await cargarVersiones();
    return ok;
  };

  const marcarOficial = async (numero: number) => {
    setMarcandoOficial(numero);
    try {
      const ok = await onMarcarOficial(formula.id, numero);
      if (ok) await cargarVersiones();
    } finally {
      setMarcandoOficial(null);
    }
  };

  const derivar = async (id: number, datos: DerivarFormulaDatos & { version_origen: number }) => {
    return onDerivar(id, datos);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button type="button" size="sm" onClick={() => setMostrarCrearVersion(true)}>
          <PlusCircle className="w-4 h-4 mr-1.5" /> Guardar versión actual (ensayo)
        </Button>
      </div>

      {cargando && <p className="text-sm text-muted-foreground">Cargando historial...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!cargando && !error && versiones.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Esta fórmula aún no tiene versiones: guarda un ensayo para crear la primera.
        </p>
      )}

      <ol className="space-y-2">
        {versiones.map((v) => (
          <li key={v.id} className="border rounded-md p-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold">v{v.numero}</span>
                {v.es_oficial && (
                  <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 hover:bg-emerald-100">Oficial</Badge>
                )}
              </div>
              <div className="flex gap-1">
                {!v.es_oficial && (
                  <Button
                    type="button" size="sm" variant="outline"
                    onClick={() => marcarOficial(v.numero)}
                    disabled={marcandoOficial === v.numero}
                  >
                    {marcandoOficial === v.numero ? 'Marcando...' : 'Marcar oficial'}
                  </Button>
                )}
                <Button
                  type="button" size="sm" variant="ghost" aria-label={`Derivar desde v${v.numero}`}
                  onClick={() => setDerivarDesde(v.numero)}
                >
                  <Split className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <p className="mt-1">{v.observaciones || v.motivo}</p>
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

      <CrearVersionDialog
        formula={mostrarCrearVersion ? formula : null}
        onOpenChange={(open) => !open && setMostrarCrearVersion(false)}
        onConfirm={guardarVersion}
      />
      <DerivarFormulaDialog
        origen={derivarDesde !== null ? { ...formula, numeroVersion: derivarDesde } : null}
        onOpenChange={(open) => !open && setDerivarDesde(null)}
        onConfirm={derivar}
      />
    </div>
  );
}
