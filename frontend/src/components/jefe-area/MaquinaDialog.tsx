import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Label } from '../ui/label';
import apiClient from '../../lib/axios';
import { getApiErrorMessage } from '../../lib/apiError';
import type { Maquina, User } from '../../lib/types';
import type { ProductoDetail, BodegaDetail } from '../../types/produccion';

/**
 * Datos de la máquina que el formulario precarga. Admite el `Maquina` del panel
 * (decimales como number) y el `MaquinaConMerma` de Gestión de Máquinas (decimales
 * como string): ambos vienen de `/maquinas/`.
 */
export interface MaquinaEditable {
  id: number;
  nombre: string;
  estado: Maquina['estado'];
  capacidad_maxima: number | string;
  eficiencia_ideal: number | string;
  operarios?: number[];
  producto_merma?: number | null;
  bodega_merma?: number | null;
}

interface MaquinaDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  maquina: MaquinaEditable | null;
  operarios: User[];
  areaId: number | undefined;
  onSaved: () => void;
}

const SIN_VALOR = '__none__';

const formVacio = () => ({
  nombre: '',
  capacidad_maxima: '',
  eficiencia_ideal: '0.85',
  estado: 'operativa' as Maquina['estado'],
  operarios: [] as number[],
  producto_merma: '',
  bodega_merma: '',
});

/** Capacidad > 0 y eficiencia en [0, 1]: lo que el negocio admite para una máquina. */
function esValido(form: ReturnType<typeof formVacio>): boolean {
  const capacidad = Number(form.capacidad_maxima);
  const eficiencia = Number(form.eficiencia_ideal);
  return form.nombre.trim() !== ''
    && form.capacidad_maxima !== '' && capacidad > 0
    && form.eficiencia_ideal !== '' && eficiencia >= 0 && eficiencia <= 1;
}

/**
 * Formulario único de máquina (crear y editar) del Jefe de Área: datos técnicos,
 * operarios a cargo y merma vendible. Lo abren la tarjeta de la máquina y Gestión
 * de Máquinas. Al editar usa PATCH y solo envía la merma si la máquina la trajo,
 * para no borrar una configuración que el formulario no llegó a mostrar.
 */
function MaquinaDialogImpl({
  open,
  onOpenChange,
  maquina,
  operarios,
  areaId,
  onSaved,
}: MaquinaDialogProps) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState(formVacio);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: productosMerma = [] } = useQuery<ProductoDetail[]>({
    queryKey: ['productos-merma'],
    queryFn: () =>
      apiClient.get('/productos/?tipo=tela,subproducto').then((r) => r.data.results ?? r.data),
    enabled: open,
  });

  const { data: bodegas = [] } = useQuery<BodegaDetail[]>({
    queryKey: ['bodegas'],
    queryFn: () => apiClient.get('/bodegas/').then((r) => r.data.results ?? r.data),
    enabled: open,
  });

  // Al abrir o cambiar de máquina se reinicia el formulario durante el render.
  const [vistos, setVistos] = useState<{ maquina: typeof maquina; open: boolean } | null>(null);
  if (vistos === null || vistos.maquina !== maquina || vistos.open !== open) {
    setVistos({ maquina, open });
    setFormData(
      maquina
        ? {
            nombre: maquina.nombre,
            capacidad_maxima: String(maquina.capacidad_maxima ?? ''),
            eficiencia_ideal: String(maquina.eficiencia_ideal ?? '0.85'),
            estado: maquina.estado,
            operarios: maquina.operarios ?? [],
            producto_merma: maquina.producto_merma?.toString() ?? '',
            bodega_merma: maquina.bodega_merma?.toString() ?? '',
          }
        : formVacio(),
    );
  }

  const conMerma = !maquina || 'producto_merma' in maquina;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!esValido(formData)) return;
    setIsSubmitting(true);
    try {
      const data = {
        nombre: formData.nombre.trim(),
        estado: formData.estado,
        capacidad_maxima: formData.capacidad_maxima,
        eficiencia_ideal: formData.eficiencia_ideal,
        operarios: formData.operarios,
        ...(conMerma ? {
          producto_merma: formData.producto_merma ? Number(formData.producto_merma) : null,
          bodega_merma: formData.bodega_merma ? Number(formData.bodega_merma) : null,
        } : {}),
        ...(areaId ? { area: areaId } : {}),
      };

      if (maquina) {
        await apiClient.patch(`/maquinas/${maquina.id}/`, data);
        toast.success('Máquina actualizada');
      } else {
        await apiClient.post('/maquinas/', data);
        toast.success('Máquina creada');
      }
      qc.invalidateQueries({ queryKey: ['maquinas'] });
      onSaved();
      onOpenChange(false);
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Error al guardar la máquina.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleOperario = (id: number) => {
    setFormData(prev => ({
      ...prev,
      operarios: prev.operarios.includes(id)
        ? prev.operarios.filter(oid => oid !== id)
        : [...prev.operarios, id],
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{maquina ? 'Editar Máquina' : 'Nueva Máquina'}</DialogTitle>
          <DialogDescription>Configura los datos técnicos, el personal a cargo y la merma vendible.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="maquina-nombre">Nombre de la Máquina</Label>
            <Input
              id="maquina-nombre"
              value={formData.nombre}
              onChange={e => setFormData({ ...formData, nombre: e.target.value })}
              placeholder="Ej: Máquina de Hilado 01"
              required
            />
          </div>

          <div className="space-y-2">
            <Label>Estado</Label>
            <Select value={formData.estado} onValueChange={v => setFormData({ ...formData, estado: v as Maquina['estado'] })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="operativa">Operativa</SelectItem>
                <SelectItem value="mantenimiento">Mantenimiento</SelectItem>
                <SelectItem value="inactiva">Inactiva</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="maquina-capacidad">Capacidad máx. (kg/turno)</Label>
              <Input
                id="maquina-capacidad"
                type="number"
                min="0"
                step="0.01"
                value={formData.capacidad_maxima}
                onChange={e => setFormData({ ...formData, capacidad_maxima: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maquina-eficiencia">Eficiencia ideal (0–1)</Label>
              <Input
                id="maquina-eficiencia"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={formData.eficiencia_ideal}
                onChange={e => setFormData({ ...formData, eficiencia_ideal: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Operarios Asignados</Label>
            <ScrollArea className="h-32 border rounded-md p-2 bg-slate-50">
              <div className="space-y-2">
                {operarios.map(u => (
                  <div key={u.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`maquina-operario-${u.id}`}
                      checked={formData.operarios.includes(u.id)}
                      onCheckedChange={() => toggleOperario(u.id)}
                    />
                    <Label htmlFor={`maquina-operario-${u.id}`} className="text-sm font-normal cursor-pointer">
                      {u.username}
                    </Label>
                  </div>
                ))}
                {operarios.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">No hay operarios en esta área.</p>}
              </div>
            </ScrollArea>
          </div>

          {conMerma && (
            <div className="border-t pt-4 space-y-3">
              <p className="text-sm font-medium text-muted-foreground">Configuración de Merma Vendible</p>

              <div className="space-y-2">
                <Label>Producto de Merma</Label>
                <Select
                  value={formData.producto_merma || SIN_VALOR}
                  onValueChange={v => setFormData({ ...formData, producto_merma: v === SIN_VALOR ? '' : v })}
                >
                  <SelectTrigger><SelectValue placeholder="Sin merma vendible" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={SIN_VALOR}>Sin merma vendible</SelectItem>
                    {productosMerma.map(p => (
                      <SelectItem key={p.id} value={p.id.toString()}>
                        {p.codigo} — {p.descripcion}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Bodega de Merma</Label>
                <Select
                  value={formData.bodega_merma || SIN_VALOR}
                  onValueChange={v => setFormData({ ...formData, bodega_merma: v === SIN_VALOR ? '' : v })}
                >
                  <SelectTrigger><SelectValue placeholder="Seleccionar bodega" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={SIN_VALOR}>Sin bodega asignada</SelectItem>
                    {bodegas.map(b => (
                      <SelectItem key={b.id} value={b.id.toString()}>
                        {b.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button type="submit" disabled={!esValido(formData) || isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Guardar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export const MaquinaDialog = React.memo(MaquinaDialogImpl);
