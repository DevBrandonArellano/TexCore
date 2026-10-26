import React from 'react';
import { lotesApi } from '../../../lib/api/lotesApi';
import { useCargaRemota } from '../../../hooks/useCargaRemota';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../ui/table';
import { EstadoCarga } from './EstadoCarga';
import type { LoteReferencia } from './tipos';

const moneda = (valor: number) => valor.toLocaleString('es-EC', { style: 'currency', currency: 'USD' });

/** Pestaña «Materias primas y costos»: lotes de proveedor consumidos y su costo. */
export function PanelMateriasPrimas({ lote }: { lote: LoteReferencia }) {
  const { datos, cargando, error } = useCargaRemota(() => lotesApi.materiasPrimas(lote.id), lote.id);

  return (
    <EstadoCarga
      cargando={cargando}
      error={error}
      vacio={!!datos && datos.componentes.length === 0}
      mensajeVacio="El lote no registra consumo de materias primas recepcionadas."
    >
      {datos && (
        <div className="space-y-3">
          <p className="text-sm">
            Costo total de materias primas:{' '}
            <strong className="font-mono">{moneda(datos.costo_total_materias_primas)}</strong>
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Lote proveedor</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead>Proveedor</TableHead>
                <TableHead className="text-right">Kg</TableHead>
                <TableHead className="text-right">Costo unit.</TableHead>
                <TableHead className="text-right">Costo</TableHead>
                <TableHead>Documento</TableHead>
                <TableHead>Certificado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datos.componentes.map((c) => (
                <TableRow key={`${c.materia_prima_lote}-${c.numero_documento}`}>
                  <TableCell className="font-mono">{c.materia_prima_lote}</TableCell>
                  <TableCell>{c.producto}</TableCell>
                  <TableCell>{c.proveedor}</TableCell>
                  <TableCell className="text-right font-mono">{c.cantidad_kg}</TableCell>
                  <TableCell className="text-right font-mono">{moneda(c.costo_unitario)}</TableCell>
                  <TableCell className="text-right font-mono">{moneda(c.costo_total)}</TableCell>
                  <TableCell>{c.numero_documento}</TableCell>
                  <TableCell>
                    {c.certificado ? (
                      <a href={c.certificado} target="_blank" rel="noopener noreferrer" className="text-primary underline">
                        Ver
                      </a>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </EstadoCarga>
  );
}
