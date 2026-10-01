import React, { useState } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ordenesApi } from '../../lib/api/ordenesApi';
import { formatApiError } from '../../lib/errorUtils';
import type { TransformacionProducto } from '../../types/produccion';

const ESTADO: Record<string, { etiqueta: string; variante: 'secondary' | 'destructive' | 'outline' }> = {
  completada: { etiqueta: 'Completada', variante: 'secondary' },
  rechazada: { etiqueta: 'Rechazada', variante: 'destructive' },
};

/**
 * Todos los registros de transformación de la orden, incluidos los rechazados
 * (intentos fallidos que la trazabilidad no muestra). Se cargan a pedido.
 */
export function RegistrosTransformacion({ ordenId }: { ordenId: number }) {
  const [registros, setRegistros] = useState<TransformacionProducto[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = async () => {
    setCargando(true);
    setError(null);
    try {
      setRegistros(await ordenesApi.transformaciones(ordenId));
    } catch (e) {
      setError(formatApiError(e).message);
    } finally {
      setCargando(false);
    }
  };

  if (registros === null) {
    return (
      <div className="space-y-1">
        <Button variant="ghost" size="sm" onClick={cargar} disabled={cargando}>
          {cargando ? 'Cargando registros…' : 'Ver todos los registros'}
        </Button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  if (registros.length === 0) {
    return <p className="text-sm text-muted-foreground">La orden no tiene registros de transformación.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>#</TableHead>
          <TableHead>Máquina</TableHead>
          <TableHead>Operario</TableHead>
          <TableHead className="text-right">Entrada (kg)</TableHead>
          <TableHead className="text-right">Salida (kg)</TableHead>
          <TableHead className="text-right">Merma (kg)</TableHead>
          <TableHead>Estado</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {registros.map((r) => {
          const estado = ESTADO[r.estado] ?? { etiqueta: r.estado, variante: 'outline' as const };
          return (
            <TableRow key={r.id}>
              <TableCell>{r.numero_secuencia}</TableCell>
              <TableCell>{r.maquina_nombre ?? '—'}</TableCell>
              <TableCell>{r.operario_nombre ?? '—'}</TableCell>
              <TableCell className="text-right font-mono">{r.peso_entrada}</TableCell>
              <TableCell className="text-right font-mono">{r.peso_salida}</TableCell>
              <TableCell className="text-right font-mono">{r.merma}</TableCell>
              <TableCell><Badge variant={estado.variante}>{estado.etiqueta}</Badge></TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
