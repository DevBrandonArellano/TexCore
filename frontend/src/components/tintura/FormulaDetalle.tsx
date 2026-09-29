import React, { useEffect, useState } from 'react';
import { ArrowLeft, ChevronRight, FlaskConical, Pencil } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card, CardContent } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import apiClient from '../../lib/axios';
import type { FormulaColor, OrdenProduccion, ProcesoTintoreria } from '../../lib/types';
import { VersionesFormulaPanel } from './VersionesFormulaPanel';
import { DerivarFormulaDatos } from './DialogosFormula';

interface FormulaDetalleProps {
  formula: FormulaColor;
  procesos: ProcesoTintoreria[];
  onVolver: () => void;
  onEditar: (formula: FormulaColor) => void;
  onCrearVersion: (id: number, observaciones: string) => Promise<boolean>;
  onMarcarOficial: (id: number, numero: number) => Promise<boolean>;
  onDerivar: (id: number, datos: DerivarFormulaDatos & { version_origen: number }) => Promise<boolean>;
}

function OrdenesDeFormula({ formulaId }: { formulaId: number }) {
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    apiClient.get(`/ordenes-produccion/historial/?formula_color=${formulaId}`)
      .then(({ data }) => {
        if (!vigente) return;
        setOrdenes(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => vigente && setOrdenes([]))
      .finally(() => vigente && setCargando(false));
    return () => { vigente = false; };
  }, [formulaId]);

  if (cargando) return <p className="text-sm text-muted-foreground">Cargando órdenes...</p>;
  if (ordenes.length === 0) {
    return <p className="text-sm text-muted-foreground">Ninguna orden de producción usó esta fórmula todavía.</p>;
  }

  return (
    <div className="rounded-lg border overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Código</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead className="text-right">Peso (kg)</TableHead>
            <TableHead className="text-right">Litros baño</TableHead>
            <TableHead>Versión usada</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {ordenes.map((o) => (
            <TableRow key={o.id}>
              <TableCell className="font-mono text-xs font-bold">{o.codigo}</TableCell>
              <TableCell><Badge variant="outline">{o.estado}</Badge></TableCell>
              <TableCell className="text-right font-mono">{o.peso_neto_requerido ?? '—'}</TableCell>
              <TableCell className="text-right font-mono">{o.litros_bano ?? '—'}</TableCell>
              <TableCell className="font-mono text-xs">{o.version_formula ? `v${o.version_formula}` : '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Detalle de una fórmula con las tres pestañas del spec 2026-09-24 D10:
 * Receta · Versiones · Órdenes. Reemplaza el panel lateral de historial (D10:
 * el contenido de versiones/diff se reutiliza tal cual dentro de la pestaña). */
export function FormulaDetalle({
  formula, procesos, onVolver, onEditar, onCrearVersion, onMarcarOficial, onDerivar,
}: FormulaDetalleProps) {
  const nombreProceso = (id?: number) => procesos.find((p) => p.id === id)?.nombre ?? 'Sin proceso';

  return (
    <div className="flex flex-col min-h-screen">
      <div className="mb-4 flex items-center justify-between text-sm text-muted-foreground flex-shrink-0">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onVolver}><ArrowLeft className="w-4 h-4 mr-2" /> Volver</Button>
          <ChevronRight className="w-4 h-4" />
          <span className="font-medium text-foreground font-mono">{formula.codigo}</span>
          <span className="font-medium text-foreground uppercase">{formula.nombre_color}</span>
          {formula.version_oficial ? (
            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">Oficial v{formula.version_oficial}</Badge>
          ) : (
            <Badge variant="secondary">Sin oficial</Badge>
          )}
          {formula.es_laboratorio && (
            <Badge variant="outline" className="gap-1"><FlaskConical className="w-3 h-3" /> Laboratorio</Badge>
          )}
        </div>
        <Button size="sm" onClick={() => onEditar(formula)}>
          <Pencil className="w-4 h-4 mr-2" /> Editar receta
        </Button>
      </div>

      {formula.formula_origen && (
        <p className="text-xs text-muted-foreground mb-4">
          Derivada de <span className="font-mono">{formula.formula_origen_codigo}</span>
          {formula.version_origen_numero ? ` (v${formula.version_origen_numero})` : ''}.
          {formula.motivo_derivacion ? ` ${formula.motivo_derivacion}` : ''}
        </p>
      )}

      <Tabs defaultValue="receta" className="flex-1 flex flex-col">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="receta">Receta</TabsTrigger>
          <TabsTrigger value="versiones">Versiones</TabsTrigger>
          <TabsTrigger value="ordenes">Órdenes</TabsTrigger>
        </TabsList>

        <TabsContent value="receta" className="flex-1 space-y-3 pt-4">
          {(formula.fases || []).map((fase) => (
            <Card key={fase.id}>
              <CardContent className="pt-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-sm">
                    Fase {fase.orden}: {fase.proceso_nombre || nombreProceso(fase.proceso)}
                  </h4>
                  <span className="text-xs text-muted-foreground">
                    {fase.temperatura ?? '—'}°C / {fase.tiempo ?? '—'}'
                  </span>
                </div>
                <div className="space-y-1">
                  {fase.detalles.map((d) => (
                    <div key={d.id} className="flex justify-between text-xs bg-muted/30 rounded px-2 py-1">
                      <span>{d.producto_descripcion || `Producto ${d.producto}`}</span>
                      <span className="font-mono">
                        {d.tipo_calculo === 'gr_l' ? `${d.concentracion_gr_l ?? 0} g/L` : `${d.porcentaje ?? 0}%`}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
          {(!formula.fases || formula.fases.length === 0) && (
            <p className="text-sm text-muted-foreground">Esta fórmula todavía no tiene fases.</p>
          )}
        </TabsContent>

        <TabsContent value="versiones" className="flex-1 pt-4">
          <VersionesFormulaPanel
            formula={formula}
            onCrearVersion={onCrearVersion}
            onMarcarOficial={onMarcarOficial}
            onDerivar={onDerivar}
          />
        </TabsContent>

        <TabsContent value="ordenes" className="flex-1 pt-4">
          <OrdenesDeFormula formulaId={formula.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
