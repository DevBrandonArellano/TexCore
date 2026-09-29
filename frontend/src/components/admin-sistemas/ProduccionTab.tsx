import React from 'react';
import { TabsContent } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Palette, Factory } from 'lucide-react';
import type { Sede, Producto, OrdenProduccion, FormulaColor } from '../../lib/types';
import { TablaLotesPaginada } from '../lotes/TablaLotesPaginada';
import { ControlesPaginacion } from '../ui/controles-paginacion';

interface ProduccionTabProps {
  selectedSede: Sede | undefined;
  sedeOrdenes: OrdenProduccion[];
  paginatedSedeOrdenes: OrdenProduccion[];
  productos: Producto[];
  currentPage: number;
  setCurrentPage: (page: number) => void;
  totalPages: number;
  formulas: FormulaColor[];
}

function ProduccionTabImpl({
  selectedSede,
  sedeOrdenes,
  paginatedSedeOrdenes,
  productos,
  currentPage,
  setCurrentPage,
  totalPages,
  formulas,
}: ProduccionTabProps) {
  return (
    <TabsContent value="production" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Órdenes de Producción</CardTitle>
          <CardDescription>Órdenes activas en {selectedSede?.nombre}</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead>Peso Req.</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sedeOrdenes.length > 0 ? (
                paginatedSedeOrdenes.map(orden => {
                  const producto = productos.find(p => p.id === orden.producto);
                  return (
                    <TableRow key={orden.id}>
                      <TableCell>{orden.codigo}</TableCell>
                      <TableCell>{producto?.descripcion || 'N/A'}</TableCell>
                      <TableCell>{orden.peso_neto_requerido} Kg</TableCell>
                      <TableCell>
                        <Badge variant={
                          orden.estado === 'finalizada' ? 'default' :
                            orden.estado === 'en_proceso' ? 'secondary' : 'outline'
                        }>
                          {orden.estado}
                        </Badge>
                      </TableCell>
                      <TableCell>{new Date(orden.fecha_creacion).toLocaleDateString()}</TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    No hay órdenes de producción
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          {sedeOrdenes.length > 0 && (
            <ControlesPaginacion
              currentPage={currentPage}
              totalPages={totalPages}
              setCurrentPage={setCurrentPage}
              className="mt-4"
            />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="w-5 h-5" />
              Fórmulas de Color
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {formulas.map(formula => (
                <div key={formula.id} className="flex items-center justify-between p-2 rounded-lg bg-accent">
                  <div>
                    <p className="font-medium">{formula.nombre_color}</p>
                    <p className="text-xs text-muted-foreground">{formula.codigo}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Factory className="w-5 h-5" />
              Lotes Producidos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TablaLotesPaginada filtros={selectedSede ? { sede_id: selectedSede.id } : {}} />
          </CardContent>
        </Card>
      </div>
    </TabsContent>
  );
}

export const ProduccionTab = React.memo(ProduccionTabImpl);
