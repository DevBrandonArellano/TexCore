import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { procesosTintoreriaApi } from '../../lib/api/procesosTintoreriaApi';
import { ordenesApi } from '../../lib/api/ordenesApi';
import { getApiErrorMessage } from '../../lib/apiError';

interface ProcesosMaquinaDialogProps {
  maquina: { id: number; nombre: string } | null;
  onClose: () => void;
}

/**
 * El Jefe de Área define qué procesos de tintorería (descrude, lavado reductivo…)
 * ejecuta una máquina de su área. Solo se ofrecen los procesos activos de la sede;
 * guardar reemplaza el conjunto completo en una sola operación.
 */
export function ProcesosMaquinaDialog({ maquina, onClose }: ProcesosMaquinaDialogProps) {
  const abierto = maquina !== null;
  const { data: catalogo = [], isLoading: cargandoCatalogo } = useQuery({
    queryKey: ['procesos-tintoreria', 'activos'],
    queryFn: () => procesosTintoreriaApi.listar({ soloActivos: true }),
    enabled: abierto,
  });
  const { data: asignados, isLoading: cargandoAsignados } = useQuery({
    queryKey: ['maquina-procesos', maquina?.id],
    queryFn: () => ordenesApi.procesosDeMaquina(maquina!.id),
    enabled: abierto,
  });
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set());
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    setSeleccion(new Set((asignados ?? []).map((p) => p.id)));
  }, [asignados]);

  const alternar = (id: number) => setSeleccion((prev) => {
    const siguiente = new Set(prev);
    if (siguiente.has(id)) siguiente.delete(id);
    else siguiente.add(id);
    return siguiente;
  });

  const guardar = async () => {
    if (!maquina) return;
    setGuardando(true);
    try {
      // Solo ids del catálogo activo: uno dado de baja se retira al guardar.
      const ids = catalogo.filter((p) => seleccion.has(p.id)).map((p) => p.id);
      await procesosTintoreriaApi.asignarAMaquina(maquina.id, ids);
      toast.success(`Procesos de ${maquina.nombre} actualizados.`);
      onClose();
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'No se pudieron guardar los procesos de la máquina.'));
    } finally {
      setGuardando(false);
    }
  };

  const cargando = cargandoCatalogo || cargandoAsignados;

  return (
    <Dialog open={abierto} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Procesos de {maquina?.nombre}</DialogTitle>
          <DialogDescription>
            Marca los procesos de tintorería que ejecuta esta máquina. Los procesos inactivos no se ofrecen.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-72 overflow-y-auto space-y-2 py-2">
          {cargando && <p className="text-sm text-muted-foreground">Cargando procesos…</p>}
          {!cargando && catalogo.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No hay procesos activos en la sede. El Tintorero los crea en su pestaña «Procesos».
            </p>
          )}
          {!cargando && catalogo.map((p) => (
            <div key={p.id} className="flex items-center gap-2">
              <Checkbox id={`proceso-${p.id}`} checked={seleccion.has(p.id)} onCheckedChange={() => alternar(p.id)} />
              <Label htmlFor={`proceso-${p.id}`} className="font-normal cursor-pointer">
                <span className="font-mono">{p.codigo}</span> · {p.nombre}
              </Label>
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={guardando}>Cancelar</Button>
          <Button onClick={guardar} disabled={guardando || cargando}>Guardar procesos</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
