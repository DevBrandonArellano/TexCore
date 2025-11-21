import { Package, History } from "lucide-react";
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Movimiento } from './OperarioDashboard';

interface InventoryHistoryProps {
  movements: Movimiento[];
}

export function InventoryHistory({ movements }: InventoryHistoryProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('es-MX', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <History className="w-5 h-5" />
          <CardTitle>Historial de Movimientos</CardTitle>
        </div>
        <CardDescription>
          Consulta tus registros de inventario más recientes.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {movements.length === 0 ? (
          <div className="text-center py-12">
            <Package className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No hay movimientos registrados</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Producto</TableHead>
                  <TableHead>Origen</TableHead>
                  <TableHead>Destino</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {movements.map((movement) => (
                  <TableRow key={movement.id}>
                    <TableCell className="whitespace-nowrap">
                      {formatDate(movement.fecha)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{movement.tipo_movimiento}</Badge>
                    </TableCell>
                    <TableCell>{movement.producto}</TableCell>
                    <TableCell>{movement.bodega_origen || 'N/A'}</TableCell>
                    <TableCell>{movement.bodega_destino || 'N/A'}</TableCell>
                    <TableCell className="text-right font-medium">{movement.cantidad}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
