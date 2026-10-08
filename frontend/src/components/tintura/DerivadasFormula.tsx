import React from 'react';
import { FlaskConical } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { formulasApi } from '../../lib/api/formulasApi';
import type { FormulaColor } from '../../lib/types';
import { useCargaRemota } from '../../hooks/useCargaRemota';

const ESTADO_FORMULA: Record<FormulaColor['estado'], string> = {
  en_pruebas: 'En pruebas',
  aprobada: 'Aprobada',
};

/** Fórmulas nacidas de esta (derivar desde una versión): código, versión de origen y motivo. */
export function DerivadasFormula({ formulaId }: { formulaId: number }) {
  const carga = useCargaRemota(() => formulasApi.derivadas(formulaId), formulaId);
  const derivadas = carga.datos ?? [];
  const { cargando } = carga;
  const error = carga.error !== null;

  if (cargando) return <p className="text-sm text-muted-foreground">Cargando fórmulas derivadas...</p>;
  if (error) return <p className="text-sm text-destructive">No se pudieron cargar las fórmulas derivadas.</p>;
  if (derivadas.length === 0) {
    return <p className="text-sm text-muted-foreground">Ninguna fórmula se ha derivado de esta.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Código</TableHead>
          <TableHead>Color</TableHead>
          <TableHead>Desde</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>Motivo</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {derivadas.map((f) => (
          <TableRow key={f.id}>
            <TableCell className="font-mono">{f.codigo}</TableCell>
            <TableCell className="uppercase">
              <span className="inline-flex items-center gap-1">
                {f.nombre_color}
                {f.es_laboratorio && <FlaskConical className="w-3 h-3 text-muted-foreground" aria-label="Laboratorio" />}
              </span>
            </TableCell>
            <TableCell className="font-mono">{f.version_origen_numero ? `v${f.version_origen_numero}` : '—'}</TableCell>
            <TableCell><Badge variant="outline">{ESTADO_FORMULA[f.estado] ?? f.estado}</Badge></TableCell>
            <TableCell>{f.motivo_derivacion || '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
