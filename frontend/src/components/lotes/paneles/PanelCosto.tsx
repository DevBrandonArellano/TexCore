import React from 'react';
import { lotesApi } from '../../../lib/api/lotesApi';
import { useCargaRemota } from '../../../hooks/useCargaRemota';
import { Table, TableBody, TableCell, TableRow } from '../../ui/table';
import { EstadoCarga } from './EstadoCarga';
import type { LoteReferencia } from './tipos';

/** Pestaña «Costo»: desglose F0-002 (materia prima, químicos, operario y máquina) y margen. */
export function PanelCosto({ lote }: { lote: LoteReferencia }) {
  const { datos, cargando, error } = useCargaRemota(() => lotesApi.costo(lote.id), lote.id);

  const filas: [string, string | null | undefined][] = datos ? [
    ['Materia prima', datos.costo_materia_prima],
    ['Químicos', datos.costo_quimicos],
    ['Operario', datos.costo_operario],
    ['Máquina', datos.costo_maquina],
    ['Otros', datos.otros_costos],
  ] : [];

  return (
    <EstadoCarga cargando={cargando} error={error}>
      {datos && (
        <div className="space-y-3">
          <Table>
            <TableBody>
              {filas.map(([concepto, valor]) => (
                <TableRow key={concepto}>
                  <TableCell>{concepto}</TableCell>
                  <TableCell className="text-right font-mono">{valor ?? '—'}</TableCell>
                </TableRow>
              ))}
              <TableRow className="font-semibold">
                <TableCell>Total</TableCell>
                <TableCell className="text-right font-mono">{datos.total_costo}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
          {datos.margen_bruto_pct != null && (
            <p className="text-sm">
              Margen bruto: <strong className="font-mono">{datos.margen_bruto ?? '—'}</strong>{' '}
              (<span className="font-mono">{datos.margen_bruto_pct} %</span>) sobre un precio esperado de{' '}
              <span className="font-mono">{datos.precio_venta_esperado ?? '—'}</span>.
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Calculado el {new Date(datos.recalculado_en ?? datos.calculado_en).toLocaleString('es-EC')}.
          </p>
        </div>
      )}
    </EstadoCarga>
  );
}
