import React from 'react';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from './button';
import { Input } from './input';
import { cn } from './utils';

interface ControlesPaginacionProps {
  currentPage: number;
  totalPages: number;
  setCurrentPage: (pagina: number) => void;
  /** Total de registros del servidor; si se omite no se muestra. */
  total?: number;
  /** Qué cuenta `total` (registros, movimientos…). */
  etiquetaTotal?: string;
  /** Muestra el indicador y bloquea la navegación mientras llega la página. */
  cargando?: boolean;
  /** Espaciado del contenedor según la pantalla (por defecto, el de una tabla dentro de una Card). */
  className?: string;
}

/** Anterior / «Ir a» / Siguiente. Navega siempre con números: sirve a `usePagination`,
 * `usePaginacionIncremental` y a los setters de estado de página simples. */
export function ControlesPaginacion({
  currentPage,
  totalPages,
  setCurrentPage,
  total,
  etiquetaTotal = 'registros',
  cargando = false,
  className = 'px-4 pb-4 mt-4',
}: ControlesPaginacionProps) {
  const irA = (valor: string) => {
    const destino = parseInt(valor, 10);
    if (!isNaN(destino) && destino >= 1 && destino <= totalPages) setCurrentPage(destino);
  };

  return (
    <nav aria-label="Paginación" className={cn('flex flex-wrap items-center justify-between gap-2', className)}>
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        Página {currentPage} de {totalPages}
        {total !== undefined && <span>· {total} {etiquetaTotal}</span>}
        {cargando && <Loader2 className="h-4 w-4 animate-spin" aria-label="Cargando" />}
      </span>
      <div className="flex items-center gap-2">
        <Button size="sm" variant="outline" onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1 || cargando}>
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
            aria-label="Ir a la página"
            onKeyDown={(e) => {
              if (e.key === 'Enter') irA((e.target as HTMLInputElement).value);
            }}
            onBlur={(e) => irA(e.target.value)}
            className="w-14 h-8 text-center py-0 px-1"
          />
        </span>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setCurrentPage(currentPage + 1)}
          disabled={currentPage === totalPages || cargando}
        >
          Siguiente
          <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>
    </nav>
  );
}
