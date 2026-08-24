import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Skeleton } from '../ui/skeleton';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { createLogger } from '../../lib/logger';
import { getApiErrorMessage } from '../../lib/apiError';
import type { OrdenProduccion } from '../../lib/types';

const logger = createLogger('ManageOrdenesProduccion');

interface RequisitosMaterialesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orden: OrdenProduccion | null;
}

function RequisitosMaterialesDialogImpl({ open, onOpenChange, orden }: RequisitosMaterialesDialogProps) {
  const [loading, setLoading] = useState(false);
  const [requisitos, setRequisitos] = useState<any>(null);

  useEffect(() => {
    if (open && orden) {
      const fetchRequisitos = async () => {
        setLoading(true);
        try {
          const response = await apiClient.get(`/ordenes-produccion/${orden.id}/requisitos_materiales/`);
          setRequisitos(response.data);
        } catch (error) {
          logger.warning('Fallo al cargar requisitos de materiales', {
            operacion: 'fetchRequisitosDialog', orden_id: orden.id,
          });
          toast.error(getApiErrorMessage(error, "Error al cargar los requisitos de materiales."));
        } finally {
          setLoading(false);
        }
      };
      fetchRequisitos();
    }
  }, [open, orden]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Requisitos de Materiales para OP: {orden?.codigo}</DialogTitle>
          <DialogDescription>
            Cálculo detallado de insumos basados en la fórmula y peso requerido.
          </DialogDescription>
        </DialogHeader>
        {loading ? (
          <div className="space-y-4 py-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : requisitos ? (
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-4">
              <Card className="bg-slate-50 border-none">
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">Peso Requerido</div>
                  <div className="text-2xl font-bold">{requisitos.peso_total_op} Kg</div>
                </CardContent>
              </Card>
              <Card className="bg-slate-50 border-none">
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">Total Insumos</div>
                  <div className="text-2xl font-bold">{requisitos.requisitos.length}</div>
                </CardContent>
              </Card>
            </div>

            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader className="bg-slate-50">
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead className="text-right">Cantidad</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requisitos.requisitos.map((req: any, i: number) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{req.producto_nombre}</TableCell>
                      <TableCell>
                        <Badge variant={req.es_base ? "default" : "secondary"}>
                          {req.tipo === 'quimico' ? '🧪 Químico' : '🧶 Materia Prima'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {req.cantidad_requerida} {req.unidad}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const RequisitosMaterialesDialog = React.memo(RequisitosMaterialesDialogImpl);
