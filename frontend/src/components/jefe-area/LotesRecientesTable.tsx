import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ChevronLeft, ChevronRight, XCircle } from 'lucide-react';
import type { LoteProduccion } from '../../lib/types';
import { usePagination } from '../../hooks/usePagination';

const ITEMS_PER_PAGE = 20;

interface LotesRecientesTableProps {
  lotes: LoteProduccion[];
  onRechazarLote: (loteId: number) => void;
}

function LotesRecientesTableImpl({ lotes, onRechazarLote }: LotesRecientesTableProps) {
  // Reset a página 1 cuando cambia el tamaño de la lista (ej. tras un refresh),
  // con clamp defensivo por si currentPage queda temporalmente fuera de rango.
  const [rawPage, setRawPage] = useState(1);
  useEffect(() => { setRawPage(1); }, [lotes.length]);
  const totalPagesRaw = Math.max(1, Math.ceil(lotes.length / ITEMS_PER_PAGE));
  const safePage = Math.min(Math.max(1, rawPage), totalPagesRaw);

  const { currentPage, setCurrentPage, totalPages, paginatedItems: paginatedLotes } = usePagination(lotes, ITEMS_PER_PAGE, {
    page: safePage,
    onPageChange: setRawPage,
  });

  return (
    <Card className="flex flex-col flex-shrink-0 mb-6">
      <CardHeader className="flex-shrink-0">
        <CardTitle>Gestión de Lotes Recientes</CardTitle>
        <CardDescription>Visualiza y gestiona la producción reciente.</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
              <TableRow>
                <TableHead>Lote</TableHead>
                <TableHead>Máquina</TableHead>
                <TableHead>Operario</TableHead>
                <TableHead>Peso (Kg)</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedLotes.map((lote) => (
                <TableRow key={lote.id}>
                  <TableCell className="font-medium">{lote.codigo_lote}</TableCell>
                  <TableCell>{lote.maquina_nombre || 'N/A'}</TableCell>
                  <TableCell>{lote.operario_nombre || 'N/A'}</TableCell>
                  <TableCell>{lote.peso_neto_producido} Kg</TableCell>
                  <TableCell>
                    <Button variant="ghost" className="text-destructive h-8 px-2" onClick={() => onRechazarLote(lote.id)}>
                      <XCircle className="mr-2 h-4 w-4" /> Rechazar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {lotes.length > 0 && (
          <div className="flex items-center justify-between mt-4 px-4 pb-4">
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

export const LotesRecientesTable = React.memo(LotesRecientesTableImpl);
