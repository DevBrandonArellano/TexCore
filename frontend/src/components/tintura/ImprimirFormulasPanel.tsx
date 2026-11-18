import React, { useState } from 'react';
import { formulasApi } from '../../lib/api/formulasApi';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { toArray } from '../../lib/collections';
import type { FormulaColor, VersionFormulaResumen } from '../../lib/types';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ImprimirDosificacionDialog } from './DialogosFormula';
import { DerivadasFormula } from './DerivadasFormula';

const MENSAJE_VERSIONES = 'No se pudo cargar el historial de versiones.';
const SELECT_CLASES = 'flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm';

interface OpcionMaterial {
  valor: string;
  etiqueta: string;
}

interface FilaColor {
  color: string;
  materiales: string[];
  codigos: string[];
  totalFormulas: number;
}

/** Texto sin tildes ni mayúsculas, para buscar «limon» y encontrar «Limón». */
const normalizar = (texto: string) => texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

/** Una fila por color del catálogo, en orden alfabético, con sus materiales y códigos. */
function filasDeColores(formulas: FormulaColor[]): FilaColor[] {
  const porColor = new Map<string, FilaColor>();
  formulas.forEach((f) => {
    const fila = porColor.get(f.nombre_color) ?? { color: f.nombre_color, materiales: [], codigos: [], totalFormulas: 0 };
    const material = f.tipo_sustrato_display ?? f.tipo_sustrato;
    if (!fila.materiales.includes(material)) fila.materiales.push(material);
    fila.codigos.push(f.codigo);
    fila.totalFormulas += 1;
    porColor.set(f.nombre_color, fila);
  });
  return Array.from(porColor.values()).sort((a, b) => a.color.localeCompare(b.color, 'es'));
}

/** Coincide por nombre del color o por código de cualquiera de sus fórmulas. */
function coincide(fila: FilaColor, busqueda: string): boolean {
  const texto = normalizar(busqueda);
  if (!texto) return true;
  return normalizar(fila.color).includes(texto) || fila.codigos.some((c) => normalizar(c).includes(texto));
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
 * Imprime la hoja de dosificación de una fórmula: se busca y se elige el color en la
 * tabla, luego el tipo de material y la fórmula de ese par. Se imprime la versión estándar o cualquiera de las
 * demás versiones, y se consultan los matices (fórmulas derivadas).
 */
export function ImprimirFormulasPanel() {
  const catalogo = useCargaRemota(() => formulasApi.listar(), 'catalogo');
  const formulas = toArray<FormulaColor>(catalogo.datos);

  const [busqueda, setBusqueda] = useState('');
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

  const filas = filasDeColores(formulas).filter((f) => coincide(f, busqueda));

  const elegirColor = (valor: string) => {
    setColor(valor);
    // Con un solo material no hay nada que elegir: se preselecciona.
    const materiales = materialesDe(formulas, valor);
    setMaterial(materiales.length === 1 ? materiales[0].valor : '');
    setFormulaElegida(null);
  };
  const elegirMaterial = (valor: string) => {
    setMaterial(valor);
    setFormulaElegida(null);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="space-y-3">
          <CardTitle className="text-base">Colores</CardTitle>
          <div className="max-w-sm space-y-1">
            <Label htmlFor="imprimir-buscar">Buscar color</Label>
            <Input id="imprimir-buscar" value={busqueda} placeholder="Nombre del color o código de fórmula"
              onChange={(e) => setBusqueda(e.target.value)} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="max-h-80 overflow-y-auto">
            <Table aria-label="Colores">
              <TableHeader>
                <TableRow>
                  <TableHead>Color</TableHead>
                  <TableHead>Materiales</TableHead>
                  <TableHead className="text-right">Fórmulas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filas.map((f) => (
                  <TableRow key={f.color} aria-selected={f.color === color} onClick={() => elegirColor(f.color)}
                    className={`cursor-pointer ${f.color === color ? 'bg-muted' : ''}`}>
                    <TableCell>
                      <button type="button" className="text-left font-medium hover:underline"
                        onClick={(e) => { e.stopPropagation(); elegirColor(f.color); }}>
                        {f.color}
                      </button>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{f.materiales.join(', ')}</TableCell>
                    <TableCell className="text-right">{f.totalFormulas}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {filas.length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              {`Ningún color coincide con «${busqueda.trim()}».`}
            </p>
          )}
        </CardContent>
      </Card>

      {color && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">{color}</h3>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="imprimir-material">Tipo de material</Label>
              <select id="imprimir-material" className={SELECT_CLASES} value={material}
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
        </div>
      )}

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
