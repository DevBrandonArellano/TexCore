import React, { useEffect, useRef, useState } from 'react';
import { Eye } from 'lucide-react';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ControlesPaginacion } from '../ui/controles-paginacion';
import { lotesApi } from '../../lib/api/lotesApi';
import { usePaginacionIncremental } from '../../hooks/usePaginacionIncremental';
import type { LoteProduccion } from '../../lib/types';
import type { FiltrosLotes } from '../../types/lotes';
import { FichaLoteDialog } from './FichaLoteDialog';

interface TablaLotesPaginadaProps {
  filtros?: FiltrosLotes;
  /** Acciones propias de la pantalla, junto a «Ver ficha». */
  accionesExtra?: (lote: LoteProduccion) => React.ReactNode;
  /** Al cambiar, se vuelve a pedir la página visible (tras rechazar, reetiquetar…). */
  version?: number;
}

/**
 * Tabla de lotes servida por bloques (usePaginacionIncremental) con «Ver ficha».
 * Cada pantalla agrega sus acciones por composición en lugar de copiar la tabla.
 */
export function TablaLotesPaginada({ filtros = {}, accionesExtra, version = 0 }: TablaLotesPaginadaProps) {
  // Los filtros llegan como objeto nuevo en cada render; su forma serializada
  // decide cuándo reiniciar la paginación (el hook guarda la estrategia vigente).
  const obtenerBloque = (bloque: number, tamano: number) =>
    lotesApi.listar(bloque, tamano, { ordering: '-hora_final', ...filtros });
  const { currentPage, setCurrentPage, totalPages, paginatedItems, count, cargando, recargar } =
    usePaginacionIncremental<LoteProduccion>({ obtenerBloque, resetKey: JSON.stringify(filtros) });
  const [loteFicha, setLoteFicha] = useState<LoteProduccion | null>(null);

  const versionInicial = useRef(version);
  useEffect(() => {
    if (version !== versionInicial.current) recargar();
  }, [version, recargar]);

  return (
    <>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
            <TableRow>
              <TableHead>Lote</TableHead>
              <TableHead>Máquina</TableHead>
              <TableHead>Operario</TableHead>
              <TableHead>Turno</TableHead>
              <TableHead>Peso (Kg)</TableHead>
              <TableHead>Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedItems.map((lote) => (
              <TableRow key={lote.id}>
                <TableCell className="font-medium">{lote.codigo_lote}</TableCell>
                <TableCell>{lote.maquina_nombre || 'N/A'}</TableCell>
                <TableCell>{lote.operario_nombre || 'N/A'}</TableCell>
                <TableCell>{lote.turno}</TableCell>
                <TableCell>{lote.peso_neto_producido} Kg</TableCell>
                <TableCell className="space-x-1 whitespace-nowrap">
                  <Button variant="ghost" className="h-8 px-2" onClick={() => setLoteFicha(lote)}>
                    <Eye className="mr-2 h-4 w-4" /> Ver ficha
                  </Button>
                  {accionesExtra?.(lote)}
                </TableCell>
              </TableRow>
            ))}
            {count === 0 && !cargando && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No hay lotes registrados.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {count > 0 && (
        <ControlesPaginacion
          currentPage={currentPage}
          totalPages={totalPages}
          setCurrentPage={setCurrentPage}
          total={count}
          cargando={cargando}
        />
      )}
      <FichaLoteDialog lote={loteFicha} onClose={() => setLoteFicha(null)} />
    </>
  );
}
