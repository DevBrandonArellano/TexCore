import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { createLogger } from '../../lib/logger';
import { getApiErrorMessage } from '../../lib/apiError';
import type { OrdenProduccion, Maquina } from '../../lib/types';
import { toLocalDatetimeInput } from './ordenUtils';

const logger = createLogger('ManageOrdenesProduccion');

interface RegistrarLoteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orden: OrdenProduccion | null;
  maquinas: Maquina[];
  onLotCreated: () => void;
}

function RegistrarLoteDialogImpl({ open, onOpenChange, orden, maquinas, onLotCreated }: RegistrarLoteDialogProps) {
  const [formData, setFormData] = useState({
    codigo_lote: '', peso_neto_producido: '', maquina: '', turno: '',
    hora_inicio: '', hora_final: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (orden) {
      // Default editable: el lote se registra al terminar (fin = ahora) y se
      // asume ~1h de proceso (inicio = ahora − 1h). El operario ajusta la hora
      // real de inicio. La duración (fin − inicio) alimenta el tiempo por lote
      // y el OEE, por eso NO pueden ser idénticas (duración 0 invalidaría el KPI).
      const ahora = new Date();
      const haceUnaHora = new Date(ahora.getTime() - 60 * 60 * 1000);
      setFormData({
        codigo_lote: '',
        peso_neto_producido: '',
        maquina: orden.maquina_asignada?.toString() || '',
        turno: '',
        hora_inicio: toLocalDatetimeInput(haceUnaHora),
        hora_final: toLocalDatetimeInput(ahora),
      });
    }
  }, [orden]);

  if (!orden) return null;

  const handleSubmit = async () => {
    if (!formData.codigo_lote || !formData.peso_neto_producido) {
      toast.error("El código del lote y el peso producido son requeridos.");
      return;
    }
    if (!formData.hora_inicio || !formData.hora_final) {
      toast.error("La hora de inicio y la hora final son requeridas.");
      return;
    }
    const inicio = new Date(formData.hora_inicio);
    const final = new Date(formData.hora_final);
    if (final <= inicio) {
      toast.error("La hora final debe ser posterior a la hora de inicio.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.post(`/ordenes-produccion/${orden.id}/registrar-lote/`, {
        codigo_lote: formData.codigo_lote,
        peso_neto_producido: formData.peso_neto_producido,
        maquina: formData.maquina,
        turno: formData.turno,
        hora_inicio: inicio.toISOString(),
        hora_final: final.toISOString(),
      });
      toast.success("Lote de producción registrado exitosamente.");
      onLotCreated();
      onOpenChange(false);
    } catch (error) {
      logger.warning('Fallo al registrar lote de producción', {
        operacion: 'registrarLote', orden_id: orden.id,
      });
      toast.error(getApiErrorMessage(error, "Ocurrió un error al registrar el lote."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Registrar Lote para OP: {orden.codigo}</DialogTitle>
          <DialogDescription>
            Producto: {orden.producto_nombre}. Complete los detalles del lote producido.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="codigo_lote">Código de Lote</Label>
            <Input id="codigo_lote" value={formData.codigo_lote} onChange={e => setFormData(f => ({ ...f, codigo_lote: e.target.value }))} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="peso_neto_producido">Peso Neto Producido (Kg)</Label>
            <Input id="peso_neto_producido" type="number" value={formData.peso_neto_producido} onChange={e => setFormData(f => ({ ...f, peso_neto_producido: e.target.value }))} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="maquina">Máquina</Label>
            <Select value={formData.maquina} onValueChange={v => setFormData(f => ({ ...f, maquina: v }))}>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona una máquina" />
              </SelectTrigger>
              <SelectContent>
                {maquinas.map(m => (
                  <SelectItem key={m.id} value={m.id.toString()}>{m.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="turno">Turno</Label>
            <Select value={formData.turno} onValueChange={v => setFormData(f => ({ ...f, turno: v }))}>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona un turno" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Mañana">Mañana</SelectItem>
                <SelectItem value="Tarde">Tarde</SelectItem>
                <SelectItem value="Noche">Noche</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="hora_inicio">Hora de Inicio</Label>
              <Input
                id="hora_inicio"
                type="datetime-local"
                value={formData.hora_inicio}
                onChange={e => setFormData(f => ({ ...f, hora_inicio: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="hora_final">Hora Final</Label>
              <Input
                id="hora_final"
                type="datetime-local"
                value={formData.hora_final}
                onChange={e => setFormData(f => ({ ...f, hora_final: e.target.value }))}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "Registrando..." : "Registrar Lote"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const RegistrarLoteDialog = React.memo(RegistrarLoteDialogImpl);
