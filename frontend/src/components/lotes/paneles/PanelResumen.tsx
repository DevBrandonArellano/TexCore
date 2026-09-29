import React from 'react';
import { lotesApi } from '../../../lib/api/lotesApi';
import { useCargaRemota } from '../../../hooks/useCargaRemota';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../ui/table';
import { EstadoCarga } from './EstadoCarga';
import type { LoteReferencia } from './tipos';

const formatoFecha = (iso: string) => (iso ? new Date(iso).toLocaleString('es-EC') : '—');

function Dato({ etiqueta, valor }: { etiqueta: string; valor: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="font-medium">{valor ?? '—'}</dd>
    </div>
  );
}

/** Pestaña «Resumen»: producción del lote y químicos consumidos por su orden. */
export function PanelResumen({ lote }: { lote: LoteReferencia }) {
  const { datos, cargando, error } = useCargaRemota(() => lotesApi.ficha(lote.id), lote.id);

  return (
    <EstadoCarga cargando={cargando} error={error}>
      {datos && (
        <div className="space-y-5">
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <Dato etiqueta="Producto" valor={datos.producto} />
            <Dato etiqueta="Peso neto" valor={`${datos.peso_neto} kg`} />
            <Dato etiqueta="Merma" valor={`${datos.peso_merma} kg${datos.tipo_merma ? ` (${datos.tipo_merma})` : ''}`} />
            <Dato etiqueta="Calidad" valor={datos.calidad} />
            <Dato etiqueta="Operario" valor={datos.operario} />
            <Dato etiqueta="Máquina" valor={datos.maquina} />
            <Dato etiqueta="Orden de producción" valor={datos.orden_produccion.codigo} />
            <Dato etiqueta="Fórmula de color" valor={datos.orden_produccion.formula_color} />
            <Dato etiqueta="Inicio" valor={formatoFecha(datos.fechas.inicio)} />
            <Dato etiqueta="Fin" valor={formatoFecha(datos.fechas.final)} />
          </dl>
          <div>
            <h4 className="text-sm font-semibold mb-2">Químicos consumidos por la orden</h4>
            {datos.quimicos_consumidos.length === 0 ? (
              <p className="text-sm text-muted-foreground">La orden no registra descargas de químicos.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Químico</TableHead>
                    <TableHead>Fase</TableHead>
                    <TableHead className="text-right">Cantidad (kg)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {datos.quimicos_consumidos.map((q, i) => (
                    <TableRow key={`${q.quimico}-${q.fase}-${i}`}>
                      <TableCell>{q.quimico}</TableCell>
                      <TableCell>{q.fase}</TableCell>
                      <TableCell className="text-right font-mono">{q.cantidad_total_op_kg}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      )}
    </EstadoCarga>
  );
}
