import React, { useState } from 'react';
import { formulasApi } from '../../lib/api/formulasApi';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { toArray } from '../../lib/collections';
import type { FormulaColor, VersionFormulaResumen } from '../../lib/types';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { ImprimirDosificacionDialog } from './DialogosFormula';
import { DerivadasFormula } from './DerivadasFormula';

const MENSAJE_VERSIONES = 'No se pudo cargar el historial de versiones.';
const SELECT_CLASES = 'flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm';

interface OpcionMaterial {
  valor: string;
  etiqueta: string;
}

/** Colores distintos del catálogo, en orden alfabético. */
function coloresDe(formulas: FormulaColor[]): string[] {
  return Array.from(new Set(formulas.map((f) => f.nombre_color))).sort((a, b) => a.localeCompare(b, 'es'));
}

/** Materiales en los que existe el color elegido, sin repetir. */
function materialesDe(formulas: FormulaColor[], color: string): OpcionMaterial[] {
  const vistos = new Map<string, OpcionMaterial>();
  formulas
    .filter((f) => f.nombre_color === color)
    .forEach((f) => vistos.set(f.tipo_sustrato, {
      valor: f.tipo_sustrato,
      etiqueta: f.tipo_sustrato_display ?? f.tipo_sustrato,
    }));
  return Array.from(vistos.values());
}

/**
 * Imprime la hoja de dosificación de una fórmula: se elige el color, luego el tipo de
 * material y la fórmula de ese par. Se imprime la versión estándar o cualquiera de las
 * demás versiones, y se consultan los matices (fórmulas derivadas).
 */
export function ImprimirFormulasPanel() {
  const catalogo = useCargaRemota(() => formulasApi.listar(), 'catalogo');
  const formulas = toArray<FormulaColor>(catalogo.datos);

  const [color, setColor] = useState('');
  const [material, setMaterial] = useState('');
  const [formulaElegida, setFormulaElegida] = useState<number | null>(null);
  const [impresion, setImpresion] = useState<{ formula: FormulaColor; numero: number | null } | null>(null);

  // Un par color + material tiene una sola fórmula; si hubiera varias, se elige entre ellas.
  const delPar = formulas.filter((f) => f.nombre_color === color && f.tipo_sustrato === material);
  const formula = delPar.length === 1 ? delPar[0] : delPar.find((f) => f.id === formulaElegida) ?? null;

  const idFormula = formula?.id ?? null;
  const versiones = useCargaRemota(
    () => (idFormula === null ? Promise.resolve([] as VersionFormulaResumen[]) : formulasApi.versiones(idFormula)),
    idFormula,
    { habilitado: idFormula !== null, mensajeDeError: () => MENSAJE_VERSIONES },
  );
  const otrasVersiones = toArray<VersionFormulaResumen>(versiones.datos).filter((v) => !v.es_oficial);

  if (catalogo.cargando) return <p className="text-sm text-muted-foreground">Cargando fórmulas…</p>;
  if (catalogo.error) return <p role="alert" className="text-sm text-destructive">{catalogo.error}</p>;
  if (formulas.length === 0) return <p className="text-sm text-muted-foreground">No hay fórmulas para imprimir.</p>;

  const elegirColor = (valor: string) => {
    setColor(valor);
    setMaterial('');
    setFormulaElegida(null);
  };
  const elegirMaterial = (valor: string) => {
    setMaterial(valor);
    setFormulaElegida(null);
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="space-y-1">
          <Label htmlFor="imprimir-color">Color</Label>
          <select id="imprimir-color" className={SELECT_CLASES} value={color}
            onChange={(e) => elegirColor(e.target.value)}>
            <option value="">Seleccione un color</option>
            {coloresDe(formulas).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="imprimir-material">Tipo de material</Label>
          <select id="imprimir-material" className={SELECT_CLASES} value={material} disabled={!color}
            onChange={(e) => elegirMaterial(e.target.value)}>
            <option value="">Seleccione un material</option>
            {materialesDe(formulas, color).map((m) => <option key={m.valor} value={m.valor}>{m.etiqueta}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="imprimir-formula">Fórmula</Label>
          <select id="imprimir-formula" className={SELECT_CLASES} value={formula?.id ?? ''}
            disabled={!material} onChange={(e) => setFormulaElegida(Number(e.target.value))}>
            <option value="">Seleccione una fórmula</option>
            {delPar.map((f) => <option key={f.id} value={f.id}>{f.codigo}</option>)}
          </select>
        </div>
      </div>

      {formula && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Versión estándar</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {formula.version_oficial ? (
                <>
                  <p className="font-medium">v{formula.version_oficial} (oficial)</p>
                  <Button type="button" aria-label="Imprimir versión estándar"
                    onClick={() => setImpresion({ formula, numero: formula.version_oficial ?? null })}>
                    Imprimir
                  </Button>
                </>
              ) : (
                <>
                  <p className="font-medium">Sin versión estándar</p>
                  <p className="text-sm text-muted-foreground">
                    Aún no hay una versión oficial: se imprime la receta en edición como BORRADOR.
                  </p>
                  <Button type="button" variant="outline" onClick={() => setImpresion({ formula, numero: null })}>
                    Imprimir receta en edición
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Otras versiones</CardTitle>
            </CardHeader>
            <CardContent>
              {versiones.cargando && <p className="text-sm text-muted-foreground">Cargando versiones…</p>}
              {!versiones.cargando && versiones.error && (
                <p role="alert" className="text-sm text-destructive">{versiones.error}</p>
              )}
              {!versiones.cargando && !versiones.error && otrasVersiones.length === 0 && (
                <p className="text-sm text-muted-foreground">Esta fórmula aún no tiene ensayos guardados.</p>
              )}
              {!versiones.cargando && !versiones.error && otrasVersiones.length > 0 && (
                <ul aria-label="Otras versiones" className="divide-y">
                  {otrasVersiones.map((v) => (
                    <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                      <div className="min-w-0 space-y-0.5">
                        <span className="font-medium">v{v.numero}</span>{' '}
                        <span className="text-sm">{v.motivo}</span>
                        {v.observaciones && <p className="text-xs text-muted-foreground">{v.observaciones}</p>}
                        <p className="text-xs text-muted-foreground">
                          {new Date(v.fecha).toLocaleDateString('es-EC')}
                        </p>
                      </div>
                      <Button type="button" size="sm" variant="outline" aria-label={`Imprimir versión ${v.numero}`}
                        onClick={() => setImpresion({ formula, numero: v.numero })}>
                        Imprimir
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Matices (fórmulas derivadas)</CardTitle>
            </CardHeader>
            <CardContent>
              <DerivadasFormula formulaId={formula.id} />
            </CardContent>
          </Card>
        </div>
      )}

      <ImprimirDosificacionDialog
        formula={impresion?.formula ?? null}
        numeroVersion={impresion?.numero ?? null}
        onOpenChange={(abierto) => {
          if (!abierto) setImpresion(null);
        }}
      />
    </div>
  );
}
