import React, { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { usePagination } from '../../hooks/usePagination';
import { ITEMS_PER_PAGE, type StockItem } from './inventoryUtils';

interface StockViewProps {
  stock: StockItem[];
  loading: boolean;
}

function StockViewImpl({ stock, loading }: StockViewProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const filteredStock = useMemo(() => {
    return stock.filter(item =>
      (item.producto || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.bodega || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.lote && item.lote.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  }, [stock, searchTerm]);

  const { totalPages, paginatedItems: paginatedStock, setCurrentPage } = usePagination(filteredStock, ITEMS_PER_PAGE, {
    page: currentPage,
    onPageChange: (p) => setSearchParams(prev => { prev.set('page', String(p)); return prev; }),
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
              prev.set('page', '1');
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
                <TableHead className="text-right">Cantidad</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}><TableCell colSpan={4}><Skeleton className="h-5 w-full" /></TableCell></TableRow>
                ))
              ) : paginatedStock.length > 0 ? (
                paginatedStock.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.producto}</TableCell>
                    <TableCell>{item.bodega}</TableCell>
                    <TableCell>{item.lote || '-'}</TableCell>
                    <TableCell className="text-right">{item.cantidad}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow><TableCell colSpan={4} className="text-center">No hay stock para mostrar.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        <div className="flex items-center justify-between mt-4 flex-shrink-0">
          <span className="text-sm text-muted-foreground">Página {currentPage} de {totalPages}</span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1 || loading}><ChevronLeft className="w-4 h-4 mr-1" />Anterior</Button>
            <span className="flex items-center gap-1 text-sm">
              <span className="text-muted-foreground">Ir a</span>
              <Input
                type="number"
                min={1}
                max={totalPages}
                defaultValue={currentPage}
                key={currentPage}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const v = parseInt((e.target as HTMLInputElement).value, 10);
                    if (!isNaN(v) && v >= 1 && v <= totalPages) {
                      setCurrentPage(v);
                    }
                  }
                }}
                onBlur={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (!isNaN(v) && v >= 1 && v <= totalPages) {
                    setCurrentPage(v);
                  }
                }}
                className="w-14 h-8 text-center py-0 px-1"
              />
            </span>
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages || loading}>Siguiente<ChevronRight className="w-4 h-4 ml-1" /></Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export const StockView = React.memo(StockViewImpl);
