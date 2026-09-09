import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { ListChecks, ClipboardList, CheckCircle2 as CheckCircle, Layout } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { Maquina, User, OrdenProduccion } from '../../lib/types';

interface OrdenesAsignacionPanelProps {
  ordenes: OrdenProduccion[];
  maquinas: Maquina[];
  operarios: User[];
  onDataRefresh: () => void;
}

function OrdenesAsignacionPanelImpl({ ordenes, maquinas, operarios, onDataRefresh }: OrdenesAsignacionPanelProps) {
  const [assignments, setAssignments] = useState<Record<number, { maquinaId: string, operarioId: string }>>({});

  const handleAsignarOrden = async (ordenId: number, maquinaId: string, operarioId: string) => {
    if (!maquinaId || !operarioId) {
      toast.error("Debes seleccionar una máquina y un operario.");
      return;
    }

    try {
      await apiClient.patch(`/ordenes-produccion/${ordenId}/`, {
        maquina_asignada: parseInt(maquinaId),
        operario_asignado: parseInt(operarioId),
        estado: 'en_proceso'
      });
      toast.success("Orden asignada e iniciada correctamente.");
      onDataRefresh();
    } catch (error) {
      console.error("Error asignando orden", error);
      toast.error("Error al asignar la orden.");
    }
  };

  const pendientes = ordenes.filter(o => o.estado === 'pendiente');

  return (
    <Card className="flex flex-col flex-1 min-h-0">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-blue-500" />
            <div>
              <CardTitle>Órdenes de Producción de tu Área</CardTitle>
              <CardDescription>Asigna máquinas y personal a las órdenes creadas por el Jefe de Planta.</CardDescription>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto min-h-0">
        {pendientes.length > 0 ? (
          <div className="space-y-4">
            {pendientes.map((orden) => (
              <div key={orden.id} className="flex flex-col md:flex-row items-start md:items-center gap-4 p-4 border rounded-lg bg-slate-50/50">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="font-mono text-[10px] text-blue-600 border-blue-200 bg-blue-50">{orden.codigo}</Badge>
                    <span className="font-bold text-slate-800">{orden.producto_nombre}</span>
                    {orden.observaciones && (
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700 border-amber-200 text-[10px]">
                        <ClipboardList className="w-3 h-3 mr-1" /> Nota
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <p>Requerido: <span className="font-semibold text-slate-700">{orden.peso_neto_requerido} Kg</span> | Fórmula: <span className="text-slate-700">{orden.formula_color_nombre}</span></p>
                    {orden.observaciones && <p className="italic text-amber-600 text-[11px] leading-tight">"{orden.observaciones}"</p>}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                  <div className="w-40">
                    <Select onValueChange={(val) => setAssignments(prev => ({
                      ...prev,
                      [orden.id]: { ...prev[orden.id], maquinaId: val }
                    }))}>
                      <SelectTrigger className="h-9 bg-white">
                        <SelectValue placeholder="Máquina" />
                      </SelectTrigger>
                      <SelectContent>
                        {maquinas.map(m => (
                          <SelectItem key={m.id} value={m.id.toString()}>{m.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-40">
                    <Select onValueChange={(val) => setAssignments(prev => ({
                      ...prev,
                      [orden.id]: { ...prev[orden.id], operarioId: val }
                    }))}>
                      <SelectTrigger className="h-9 bg-white">
                        <SelectValue placeholder="Operario" />
                      </SelectTrigger>
                      <SelectContent>
                        {operarios.map(u => (
                          <SelectItem key={u.id} value={u.id.toString()}>{u.username}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    size="sm"
                    onClick={() => handleAsignarOrden(
                      orden.id,
                      assignments[orden.id]?.maquinaId || '',
                      assignments[orden.id]?.operarioId || ''
                    )}
                    disabled={!maquinas.length || !operarios.length}
                  >
                    <CheckCircle className="mr-2 h-4 w-4" /> Asignar
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-lg border border-dashed">
            <Layout className="h-8 w-8 text-muted-foreground mb-2 opacity-50" />
            <p className="text-sm text-muted-foreground">No hay órdenes pendientes de asignación en tu área.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const OrdenesAsignacionPanel = React.memo(OrdenesAsignacionPanelImpl);
