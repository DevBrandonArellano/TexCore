import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Label } from '../ui/label';
import apiClient from '../../lib/axios';
import type { Maquina, User } from '../../lib/types';

interface MaquinaDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  maquina: Partial<Maquina> | null;
  operarios: User[];
  areaId: number | undefined;
  onSave: () => void;
}

function MaquinaDialogImpl({
  open,
  onOpenChange,
  maquina,
  operarios,
  areaId,
  onSave
}: MaquinaDialogProps) {
  const [formData, setFormData] = useState({
    nombre: '',
    capacidad_maxima: '',
    eficiencia_ideal: '0.85',
    estado: 'operativa',
    operarios: [] as number[]
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (maquina) {
      setFormData({
        nombre: maquina.nombre || '',
        capacidad_maxima: maquina.capacidad_maxima?.toString() || '',
        eficiencia_ideal: maquina.eficiencia_ideal?.toString() || '0.85',
        estado: maquina.estado || 'operativa',
        operarios: maquina.operarios || []
      });
    } else {
      setFormData({
        nombre: '',
        capacidad_maxima: '',
        eficiencia_ideal: '0.85',
        estado: 'operativa',
        operarios: []
      });
    }
  }, [maquina, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const data = {
        ...formData,
        area: areaId,
        capacidad_maxima: parseFloat(formData.capacidad_maxima),
        eficiencia_ideal: parseFloat(formData.eficiencia_ideal),
      };

      if (maquina?.id) {
        await apiClient.put(`/maquinas/${maquina.id}/`, data);
        toast.success("Máquina actualizada correctamente.");
      } else {
        await apiClient.post('/maquinas/', data);
        toast.success("Máquina creada correctamente.");
      }
      onSave();
      onOpenChange(false);
    } catch (error) {
      toast.error("Error al guardar la máquina.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleOperario = (id: number) => {
    setFormData(prev => ({
      ...prev,
      operarios: prev.operarios.includes(id)
        ? prev.operarios.filter(oid => oid !== id)
        : [...prev.operarios, id]
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{maquina?.id ? 'Editar Máquina' : 'Nueva Máquina'}</DialogTitle>
          <DialogDescription>Configura los detalles técnicos y el personal a cargo.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre de la Máquina</Label>
            <Input id="nombre" value={formData.nombre} onChange={e => setFormData({ ...formData, nombre: e.target.value })} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="capacidad">Capacidad (Kg/Turno)</Label>
              <Input id="capacidad" type="number" step="0.01" value={formData.capacidad_maxima} onChange={e => setFormData({ ...formData, capacidad_maxima: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="estado">Estado Inicial</Label>
              <Select value={formData.estado} onValueChange={v => setFormData({ ...formData, estado: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="operativa">Operativa</SelectItem>
                  <SelectItem value="mantenimiento">Mantenimiento</SelectItem>
                  <SelectItem value="inactiva">Inactiva</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Operarios Asignados (Control)</Label>
            <ScrollArea className="h-32 border rounded-md p-2 bg-slate-50">
              <div className="space-y-2">
                {operarios.map(u => (
                  <div key={u.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`u-${u.id}`}
                      checked={formData.operarios.includes(u.id)}
                      onCheckedChange={() => toggleOperario(u.id)}
                    />
                    <Label htmlFor={`u-${u.id}`} className="text-sm font-normal cursor-pointer">
                      {u.username}
                    </Label>
                  </div>
                ))}
                {operarios.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">No hay operarios en esta área.</p>}
              </div>
            </ScrollArea>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Guardando...' : 'Guardar'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export const MaquinaDialog = React.memo(MaquinaDialogImpl);
