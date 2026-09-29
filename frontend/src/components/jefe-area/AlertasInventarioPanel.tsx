import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { AlertTriangle } from 'lucide-react';
import type { Producto } from '../../lib/types';
import { usePagination } from '../../hooks/usePagination';
import { ControlesPaginacion } from '../ui/controles-paginacion';

const ITEMS_PER_PAGE = 20;

interface AlertasInventarioPanelProps {
  alertas: Producto[];
}

function AlertasInventarioPanelImpl({ alertas }: AlertasInventarioPanelProps) {
  // Resetea a página 1 cuando cambia el tamaño de la lista (ej. tras un
  // refresh); el hook clampa internamente si currentPage queda fuera de rango.
  const { currentPage, setCurrentPage, totalPages, paginatedItems: paginatedAlertas } = usePagination(alertas, ITEMS_PER_PAGE, {
    resetKey: alertas.length,
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
          <ControlesPaginacion
            currentPage={currentPage}
            totalPages={totalPages}
            setCurrentPage={setCurrentPage}
            className="mt-4"
          />
        )}
      </CardContent>
    </Card>
  );
}

export const AlertasInventarioPanel = React.memo(AlertasInventarioPanelImpl);
