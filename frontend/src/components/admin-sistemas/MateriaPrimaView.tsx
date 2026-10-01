import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { SearchableSelect } from '../ui/searchable-select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ControlesPaginacion } from '../ui/controles-paginacion';
import { usePaginacionIncremental } from '../../hooks/usePaginacionIncremental';
import { inventarioApi } from '../../lib/api/inventarioApi';
import type { Proveedor } from '../../lib/types';
import type { FiltrosMateriaPrima, MateriaPrimaLote } from '../../types/inventario';

interface MateriaPrimaViewProps {
  proveedores: Proveedor[];
}

const kg = (valor: string | number) => Number(valor).toFixed(3);

/**
 * Lotes de materia prima recibidos (F0-001) en las bodegas que el usuario opera:
 * cuánto se recibió, cuánto queda disponible para producción, costo y certificado.
 */
export function MateriaPrimaView({ proveedores }: MateriaPrimaViewProps) {
  const [proveedor, setProveedor] = useState('');
  const [soloDisponibles, setSoloDisponibles] = useState(false);

  const filtros = useMemo<FiltrosMateriaPrima>(() => ({
    ...(proveedor ? { proveedor: Number(proveedor) } : {}),
    ...(soloDisponibles ? { disponibles: true } : {}),
  }), [proveedor, soloDisponibles]);
  const filtrosRef = useRef(filtros);
  filtrosRef.current = filtros;

  const obtenerBloque = useCallback(
    (bloque: number, tamano: number) => inventarioApi.listarMateriaPrima(bloque, tamano, filtrosRef.current),
    [],
  );
  const { currentPage, setCurrentPage, totalPages, paginatedItems, count, cargando } =
    usePaginacionIncremental<MateriaPrimaLote>({ obtenerBloque, resetKey: JSON.stringify(filtros) });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lotes de Materia Prima</CardTitle>
        <CardDescription>
          Lotes recibidos de los proveedores: lo recibido, lo disponible para producción, su costo y certificado.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="space-y-2 sm:w-72">
            <Label htmlFor="mp-proveedor">Proveedor</Label>
            <SearchableSelect
              id="mp-proveedor"
              items={proveedores.map(p => ({ value: p.id.toString(), label: p.nombre }))}
              value={proveedor}
              onValueChange={setProveedor}
              placeholder="Todos los proveedores"
              searchPlaceholder="Buscar proveedor..."
              emptyLabel="No se encontraron proveedores"
            />
          </div>
          <div className="flex items-center gap-2 pb-2">
            <Checkbox id="mp-disponibles" checked={soloDisponibles}
              onCheckedChange={(v) => setSoloDisponibles(v === true)} />
            <Label htmlFor="mp-disponibles">Solo disponibles</Label>
          </div>
          {(proveedor || soloDisponibles) && (
            <Button variant="ghost" onClick={() => { setProveedor(''); setSoloDisponibles(false); }}>
              Limpiar filtros
            </Button>
          )}
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
              <TableRow>
                <TableHead>Recepción</TableHead>
                <TableHead>Lote proveedor</TableHead>
                <TableHead>Proveedor</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead>Bodega</TableHead>
                <TableHead className="text-right">Recibido (kg)</TableHead>
                <TableHead className="text-right">Disponible (kg)</TableHead>
                <TableHead className="text-right">Costo unit.</TableHead>
                <TableHead>Certificado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedItems.map((mp) => (
                <TableRow key={mp.id}>
                  <TableCell className="whitespace-nowrap">{mp.fecha_recepcion}</TableCell>
                  <TableCell className="font-medium">{mp.lote_proveedor}</TableCell>
                  <TableCell>{mp.proveedor_nombre}</TableCell>
                  <TableCell>{mp.producto_descripcion}</TableCell>
                  <TableCell>{mp.bodega_nombre ?? '—'}</TableCell>
                  <TableCell className="text-right tabular-nums">{kg(mp.cantidad_kg)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {mp.completamente_consumida
                      ? <Badge variant="secondary">Consumido</Badge>
                      : kg(mp.cantidad_disponible)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{mp.costo_unitario}</TableCell>
                  <TableCell>
                    {mp.certificado_calidad
                      ? <a href={mp.certificado_calidad} target="_blank" rel="noreferrer"
                          className="text-primary underline-offset-4 hover:underline">Ver certificado</a>
                      : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                </TableRow>
              ))}
              {count === 0 && !cargando && (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-muted-foreground">
                    No hay lotes de materia prima.
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
      </CardContent>
    </Card>
  );
}
