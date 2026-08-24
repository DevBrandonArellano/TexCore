import React from 'react';
import { TabsContent } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ChevronLeft, ChevronRight, Palette, Factory } from 'lucide-react';
import type { Sede, Producto, OrdenProduccion, FormulaColor, LoteProduccion } from '../../lib/types';

interface ProduccionTabProps {
  selectedSede: Sede | undefined;
  sedeOrdenes: OrdenProduccion[];
  paginatedSedeOrdenes: OrdenProduccion[];
  productos: Producto[];
  currentPage: number;
  setCurrentPage: (page: number) => void;
  totalPages: number;
  formulas: FormulaColor[];
  lotesProduccion: LoteProduccion[];
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
  lotesProduccion,
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
            <div className="space-y-2">
              {(Array.isArray(lotesProduccion) ? lotesProduccion : []).map(lote => (
                <div key={lote.id} className="p-2 rounded-lg bg-accent">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{lote.codigo_lote}</span>
                    <Badge variant="outline">{lote.peso_neto_producido} Kg</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {lote.maquina} - Turno {lote.turno}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </TabsContent>
  );
}

export const ProduccionTab = React.memo(ProduccionTabImpl);
