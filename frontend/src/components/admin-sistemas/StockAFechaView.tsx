import React, { useState } from 'react';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { ProductSelect } from '../ui/product-select';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '../ui/table';
import { inventarioApi } from '../../lib/api/inventarioApi';
import { formatApiError } from '../../lib/errorUtils';
import type { Bodega, Producto } from '../../lib/types';
import type { StockAFechaFila } from '../../types/inventario';

interface StockAFechaViewProps {
  productos: Producto[];
  bodegas: Bodega[];
}

const TODAS = 'all';
const hoy = () => new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD en hora local
const kg = (valor: string | number) => Number(valor).toFixed(3);

/**
 * Stock de un producto por bodega a una fecha de corte (cierre de ese día),
 * calculado en el servidor desde los movimientos. Solo bodegas que el usuario ve.
 */
export function StockAFechaView({ productos, bodegas }: StockAFechaViewProps) {
  const [producto, setProducto] = useState('');
  const [fechaCorte, setFechaCorte] = useState(hoy);
  const [bodega, setBodega] = useState(TODAS);
  const [filas, setFilas] = useState<StockAFechaFila[] | null>(null);
  const [consultando, setConsultando] = useState(false);

  const consultar = async () => {
    if (!producto || !fechaCorte) {
      toast.error('Elige un producto y una fecha de corte.');
      return;
    }
    setConsultando(true);
    try {
      setFilas(await inventarioApi.stockAFecha({
        producto_id: Number(producto),
        fecha_corte: fechaCorte,
        ...(bodega !== TODAS ? { bodega_id: Number(bodega) } : {}),
      }));
    } catch (error) {
      const formatted = formatApiError(error);
      toast.error(formatted.message, { description: formatted.note });
    } finally {
      setConsultando(false);
    }
  };

  const total = (filas ?? []).reduce((suma, f) => suma + Number(f.stock_calculado), 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stock a fecha de corte</CardTitle>
        <CardDescription>
          Saldo de un producto en cada bodega al cierre de una fecha pasada (entradas menos salidas).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4 md:items-end">
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="corte-producto">Producto</Label>
            <ProductSelect productos={productos} value={producto} onValueChange={setProducto} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="corte-fecha">Fecha de corte</Label>
            <Input id="corte-fecha" type="date" value={fechaCorte} max={hoy()}
              onChange={e => setFechaCorte(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="corte-bodega">Bodega</Label>
            <Select value={bodega} onValueChange={setBodega}>
              <SelectTrigger id="corte-bodega"><SelectValue placeholder="Todas las bodegas" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={TODAS}>Todas las bodegas</SelectItem>
                {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button onClick={consultar} disabled={consultando}>{consultando ? 'Consultando...' : 'Consultar stock'}</Button>

        {filas && (
          filas.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin stock a esa fecha.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sede</TableHead>
                  <TableHead>Bodega</TableHead>
                  <TableHead className="text-right">Stock</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filas.map(f => (
                  <TableRow key={f.bodega_id}>
                    <TableCell>{f.sede ?? '—'}</TableCell>
                    <TableCell>{f.bodega}</TableCell>
                    <TableCell className="text-right tabular-nums">{kg(f.stock_calculado)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
              {filas.length > 1 && (
                <TableFooter>
                  <TableRow>
                    <TableCell colSpan={2}>Total</TableCell>
                    <TableCell className="text-right tabular-nums">{kg(total)}</TableCell>
                  </TableRow>
                </TableFooter>
              )}
            </Table>
          )
        )}
      </CardContent>
    </Card>
  );
}
