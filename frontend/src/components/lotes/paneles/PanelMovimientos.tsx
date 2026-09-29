import React from 'react';
import { lotesApi } from '../../../lib/api/lotesApi';
import { useCargaRemota } from '../../../hooks/useCargaRemota';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../ui/table';
import { EstadoCarga } from './EstadoCarga';
import type { LoteReferencia } from './tipos';

/** Pestaña «Movimientos»: kárdex del lote (acotado por el backend a las bodegas visibles). */
export function PanelMovimientos({ lote }: { lote: LoteReferencia }) {
  const { datos, cargando, error } = useCargaRemota(() => lotesApi.movimientos(lote.codigo_lote), lote.codigo_lote);

  return (
    <EstadoCarga
      cargando={cargando}
      error={error}
      vacio={!!datos && datos.historial.length === 0}
      mensajeVacio="El lote no tiene movimientos de inventario en sus bodegas."
    >
      {datos && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Origen</TableHead>
              <TableHead>Destino</TableHead>
              <TableHead className="text-right">Cantidad (kg)</TableHead>
              <TableHead>Documento</TableHead>
              <TableHead>Usuario</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {datos.historial.map((m) => (
              <TableRow key={m.id}>
                <TableCell className="whitespace-nowrap">{new Date(m.fecha).toLocaleString('es-EC')}</TableCell>
                <TableCell>{m.tipo_movimiento}</TableCell>
                <TableCell>{m.bodega_origen}</TableCell>
                <TableCell>{m.bodega_destino}</TableCell>
                <TableCell className="text-right font-mono">{m.cantidad}</TableCell>
                <TableCell>{m.documento_ref || '—'}</TableCell>
                <TableCell>{m.usuario}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </EstadoCarga>
  );
}
