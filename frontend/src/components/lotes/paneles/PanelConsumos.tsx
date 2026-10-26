import React from 'react';
import { lotesApi } from '../../../lib/api/lotesApi';
import { useCargaRemota } from '../../../hooks/useCargaRemota';
import { Badge } from '../../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../ui/table';
import { EstadoCarga } from './EstadoCarga';
import type { LoteReferencia } from './tipos';

/** Pestaña «Consumos»: lotes de origen consumidos en la mezcla de este lote. */
export function PanelConsumos({ lote }: { lote: LoteReferencia }) {
  const { datos, cargando, error } = useCargaRemota(() => lotesApi.consumos(lote.id), lote.id);

  return (
    <EstadoCarga
      cargando={cargando}
      error={error}
      vacio={!!datos && datos.length === 0}
      mensajeVacio="El lote no consumió otros lotes en su mezcla."
    >
      {datos && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Lote de origen</TableHead>
              <TableHead className="text-right">Cantidad consumida (kg)</TableHead>
              <TableHead>Lote nuevo</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {datos.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-mono">{c.lote_origen_codigo ?? c.lote_origen}</TableCell>
                <TableCell className="text-right font-mono">{c.cantidad_consumida}</TableCell>
                <TableCell>{c.genera_nuevo_lote ? <Badge variant="outline">Sí</Badge> : 'No'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </EstadoCarga>
  );
}
