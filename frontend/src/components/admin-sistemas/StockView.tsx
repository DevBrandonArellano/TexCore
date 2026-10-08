import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Skeleton } from '../ui/skeleton';
import { Badge } from '../ui/badge';
import { usePaginacionIncremental } from '../../hooks/usePaginacionIncremental';
import { inventarioApi } from '../../lib/api/inventarioApi';
import { ITEMS_PER_PAGE, type StockItem } from './inventoryUtils';
import { ControlesPaginacion } from '../ui/controles-paginacion';

/** Espera tras la última tecla antes de buscar en el servidor. */
const ESPERA_BUSQUEDA_MS = 300;

interface StockViewProps {
  sedeId?: string;
}

/**
 * Stock con existencias, paginado y filtrado en el servidor: con años de operación el
 * listado completo eran decenas de miles de filas (prueba de carga 2026-10-06).
 */
function StockViewImpl({ sedeId }: StockViewProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const [busqueda, setBusqueda] = useState(searchTerm);

  useEffect(() => {
    const id = setTimeout(() => setBusqueda(searchTerm), ESPERA_BUSQUEDA_MS);
    return () => clearTimeout(id);
  }, [searchTerm]);

  const obtenerBloque = useCallback(
    (bloque: number, tamano: number) => inventarioApi.listarStock(bloque, tamano, { sede_id: sedeId, search: busqueda }),
    [sedeId, busqueda],
  );
  const { currentPage, setCurrentPage, totalPages, paginatedItems: paginatedStock, count, cargando, error } =
    usePaginacionIncremental<StockItem>({
      obtenerBloque,
      tamanoPagina: ITEMS_PER_PAGE,
      resetKey: `${sedeId ?? ''}|${busqueda}`,
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stock Actual</CardTitle>
        <CardDescription>Inventario disponible en todas las bodegas.</CardDescription>
        <Input
          placeholder="Buscar por producto, bodega o lote..."
          value={searchTerm}
          onChange={(e) => {
            const val = e.target.value;
            setSearchParams(prev => {
              if (val) prev.set('search', val);
              else prev.delete('search');
              return prev;
            }, { replace: true });
          }}
          className="w-full mt-4"
        />
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col pt-0">
        <div className="flex-1 overflow-auto rounded-md border relative">
          <Table className="min-w-max">
            <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
              <TableRow>
                <TableHead>Producto</TableHead>
                <TableHead>Bodega</TableHead>
                <TableHead>Lote</TableHead>
                <TableHead className="text-right">Físico Total</TableHead>
                <TableHead className="text-right">Comprometido (MTO)</TableHead>
                <TableHead className="text-right font-semibold">Disponible</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cargando ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}><TableCell colSpan={6}><Skeleton className="h-5 w-full" /></TableCell></TableRow>
                ))
              ) : paginatedStock.length > 0 ? (
                paginatedStock.map((item) => {
                  const comprometido = parseFloat(String(item.stock_comprometido || '0'));
                  const disponible = item.stock_disponible != null
                    ? item.stock_disponible
                    : (parseFloat(item.cantidad || '0') - comprometido).toFixed(3);

                  return (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.producto}</TableCell>
                      <TableCell>{item.bodega}</TableCell>
                      <TableCell>{item.lote || '-'}</TableCell>
                      <TableCell className="text-right">{item.cantidad}</TableCell>
                      <TableCell className="text-right">
                        {comprometido > 0 ? (
                          <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-300 font-mono">
                            {comprometido.toFixed(3)}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-xs">0.000</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-semibold text-emerald-700">
                        {disponible}
                      </TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className={error ? 'text-center text-destructive' : 'text-center'}>
                    {error ?? 'No hay stock para mostrar.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        <ControlesPaginacion
          currentPage={currentPage}
          totalPages={totalPages}
          setCurrentPage={setCurrentPage}
          total={count}
          cargando={cargando}
          className="mt-4 flex-shrink-0"
        />
      </CardContent>
    </Card>
  );
}

export const StockView = React.memo(StockViewImpl);
