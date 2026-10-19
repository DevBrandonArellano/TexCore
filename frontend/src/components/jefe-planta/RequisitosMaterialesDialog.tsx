import React, { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Skeleton } from '../ui/skeleton';
import apiClient from '../../lib/axios';
import { getApiErrorMessage } from '../../lib/apiError';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import type { OrdenProduccion, RequisitoMaterial, RequisitosOrden } from '../../lib/types';

/** Cantidad en formato de Ecuador, sin ceros de relleno: '60.000' → '60', '0.600' → '0,6'. */
const cantidad = (valor: number | string) => Number(valor).toLocaleString('es-EC', { maximumFractionDigits: 3 });

const peso = (valor: number | string | null) => (valor === null ? 'Sin peso requerido' : `${cantidad(valor)} kg`);

interface RequisitosMaterialesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orden: OrdenProduccion | null;
}

/**
 * TEX-28: materiales que necesita la orden para completarse, con el mismo cálculo que el
 * MRP. Muestra el stock libre en la bodega de la orden y señala lo que falta (CA-2); los
 * químicos descargados al crearla aparecen como ya descontados.
 */
function RequisitosMaterialesDialogImpl({ open, onOpenChange, orden }: RequisitosMaterialesDialogProps) {
  const { datos: requisitos, cargando, error } = useCargaRemota<RequisitosOrden>(
    async () => (await apiClient.get(`/ordenes-produccion/${orden?.id}/requisitos_materiales/`)).data,
    orden?.id ?? null,
    {
      habilitado: open && !!orden,
      mensajeDeError: (err) => getApiErrorMessage(err, 'Error al cargar los requisitos de materiales.'),
    },
  );

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Requisitos de Materiales para OP: {orden?.codigo}</DialogTitle>
          <DialogDescription>
            Lo que falta del producto de entrada y los químicos de la fórmula, con el stock libre en la bodega
            de la orden.
          </DialogDescription>
        </DialogHeader>
        {cargando ? (
          <div className="space-y-4 py-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : requisitos ? (
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-4">
              <Card className="bg-slate-50 border-none">
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">Peso requerido</div>
                  <div className="text-2xl font-bold">{peso(requisitos.peso_total_op)}</div>
                </CardContent>
              </Card>
              <Card className="bg-slate-50 border-none">
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">Pendiente de producir</div>
                  <div className="text-2xl font-bold">{peso(requisitos.peso_pendiente)}</div>
                </CardContent>
              </Card>
            </div>

            {requisitos.advertencias.length > 0 && (
              <ul className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 space-y-1">
                {requisitos.advertencias.map((a, i) => (
                  <li key={i} className="flex gap-1"><AlertTriangle className="w-3.5 h-3.5 shrink-0" />{a}</li>
                ))}
              </ul>
            )}

            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader className="bg-slate-50">
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead className="text-right">Requerido</TableHead>
                    <TableHead className="text-right">Disponible</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requisitos.requisitos.map((req) => (
                    <TableRow key={req.producto_id}>
                      <TableCell>
                        <div className="font-medium">{req.producto_nombre}</div>
                        <div className="text-xs text-muted-foreground">{req.producto_codigo}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={req.es_base ? 'default' : 'secondary'}>
                          {req.es_base ? 'Producto de entrada' : 'Químico'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {cantidad(req.cantidad_requerida)} {req.unidad}
                      </TableCell>
                      <TableCell className="text-right font-mono">{cantidad(req.stock_disponible)}</TableCell>
                      <TableCell><EstadoRequisito requisito={req} /></TableCell>
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

function EstadoRequisito({ requisito }: { requisito: RequisitoMaterial }) {
  if (requisito.ya_descontado) return <Badge variant="outline">Ya descontado</Badge>;
  if (Number(requisito.faltante) > 0) {
    return <Badge variant="destructive">Falta {cantidad(requisito.faltante)} {requisito.unidad}</Badge>;
  }
  return <Badge variant="outline" className="border-green-600 text-green-700">Suficiente</Badge>;
}

export const RequisitosMaterialesDialog = React.memo(RequisitosMaterialesDialogImpl);
