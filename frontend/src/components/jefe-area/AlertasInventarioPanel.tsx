import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Producto } from '../../lib/types';
import { usePagination } from '../../hooks/usePagination';

const ITEMS_PER_PAGE = 20;

interface AlertasInventarioPanelProps {
  alertas: Producto[];
}

function AlertasInventarioPanelImpl({ alertas }: AlertasInventarioPanelProps) {
  // Reset a página 1 cuando cambia el tamaño de la lista (ej. tras un refresh),
  // con clamp defensivo por si currentPage queda temporalmente fuera de rango.
  const [rawPage, setRawPage] = useState(1);
  useEffect(() => { setRawPage(1); }, [alertas.length]);
  const totalPagesRaw = Math.max(1, Math.ceil(alertas.length / ITEMS_PER_PAGE));
  const safePage = Math.min(Math.max(1, rawPage), totalPagesRaw);

  const { currentPage, setCurrentPage, totalPages, paginatedItems: paginatedAlertas } = usePagination(alertas, ITEMS_PER_PAGE, {
    page: safePage,
    onPageChange: setRawPage,
  });

  return (
    <Card className="col-span-3 flex flex-col h-[400px]">
      <CardHeader className="flex-shrink-0">
        <CardTitle>Alertas de Inventario</CardTitle>
        <CardDescription>Productos químicos e hilos bajo mínimo.</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto min-h-0">
        <div className="space-y-2">
          {paginatedAlertas.map((prod) => (
            <Alert key={prod.id} variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Stock Bajo: {prod.codigo}</AlertTitle>
              <AlertDescription>
                {prod.descripcion} (Min: {prod.stock_minimo} {prod.unidad_medida})
              </AlertDescription>
            </Alert>
          ))}
          {alertas.length === 0 && <Alert><AlertTitle>Todo en orden</AlertTitle><AlertDescription>No hay alertas de stock bajo.</AlertDescription></Alert>}
        </div>
        {alertas.length > 0 && (
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-muted-foreground">
              Página {currentPage} de {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Anterior
              </Button>
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
                      if (!isNaN(v) && v >= 1 && v <= totalPages) setCurrentPage(v);
                    }
                  }}
                  onBlur={(e) => {
                    const v = parseInt(e.target.value, 10);
                    if (!isNaN(v) && v >= 1 && v <= totalPages) setCurrentPage(v);
                  }}
                  className="w-14 h-8 text-center py-0 px-1"
                />
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
              >
                Siguiente
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const AlertasInventarioPanel = React.memo(AlertasInventarioPanelImpl);
