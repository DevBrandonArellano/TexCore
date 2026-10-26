import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import type { InsumoDosificado } from '../../lib/types';

/** Insumos calculados por el servidor (dosificación de una fórmula o de una orden). */
export function TablaInsumosDosificacion({ insumos }: { insumos: InsumoDosificado[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Insumo</TableHead>
          <TableHead>Dosis</TableHead>
          <TableHead className="text-right">Cantidad (kg)</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {insumos.map((i) => (
          <TableRow key={`${i.orden_adicion}-${i.producto_id}`}>
            <TableCell>{i.producto_descripcion}</TableCell>
            <TableCell>{i.tipo_calculo === 'gr_l' ? `${i.concentracion_gr_l} g/L` : `${i.porcentaje} %`}</TableCell>
            <TableCell className="text-right tabular-nums">{i.cantidad_kg}</TableCell>
          </TableRow>
        ))}
        {insumos.length === 0 && (
          <TableRow>
            <TableCell colSpan={3} className="text-center text-muted-foreground">
              La fórmula no tiene insumos.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
