import React, { useState } from 'react';
import { Pencil, Trash2, Workflow } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../ui/alert-dialog';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { procesosApi } from '../../lib/api/procesosApi';
import { formatApiError } from '../../lib/errorUtils';
import type { ProcesoProduccion } from '../../lib/types';

const VACIO = { name: '', description: '' };

function mostrarError(error: unknown) {
  const formatted = formatApiError(error);
  toast.error(formatted.message, { description: formatted.note });
}

/**
 * Catálogo de procesos de producción (tejido, teñido, acabado…) que se eligen al
 * registrar una operación MES. Global: lo mantiene el Administrador de Sistemas.
 * Un proceso ya usado por operaciones no se puede eliminar (el servidor responde 409).
 */
export function ManageProcesos() {
  const { datos, cargando, error, recargar } = useCargaRemota(() => procesosApi.listar(), 'procesos');
  const procesos = datos ?? [];
  const [editando, setEditando] = useState<ProcesoProduccion | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [form, setForm] = useState(VACIO);
  const [guardando, setGuardando] = useState(false);
  const [eliminando, setEliminando] = useState<ProcesoProduccion | null>(null);

  const abrir = (proceso: ProcesoProduccion | null) => {
    setEditando(proceso);
    setForm(proceso ? { name: proceso.name, description: proceso.description ?? '' } : VACIO);
    setFormAbierto(true);
  };

  const guardar = async () => {
    const datosProceso = { name: form.name.trim(), description: form.description.trim() };
    if (!datosProceso.name) {
      toast.error('El nombre del proceso es requerido.');
      return;
    }
    setGuardando(true);
    try {
      if (editando) await procesosApi.actualizar(editando.id, datosProceso);
      else await procesosApi.crear(datosProceso);
      toast.success(editando ? 'Proceso actualizado.' : 'Proceso creado.');
      setFormAbierto(false);
      recargar();
    } catch (e) {
      mostrarError(e);
    } finally {
      setGuardando(false);
    }
  };

  const confirmarEliminar = async () => {
    if (!eliminando) return;
    try {
      await procesosApi.eliminar(eliminando.id);
      toast.success('Proceso eliminado.');
      recargar();
    } catch (e) {
      mostrarError(e);
    } finally {
      setEliminando(null);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Procesos de Producción</CardTitle>
          <CardDescription>Catálogo de procesos que se registran en cada operación de producción.</CardDescription>
        </div>
        <Button onClick={() => abrir(null)}><Workflow className="w-4 h-4 mr-2" /> Nuevo proceso</Button>
      </CardHeader>
      <CardContent>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Descripción</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {procesos.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{p.name}</TableCell>
                <TableCell className="text-muted-foreground">{p.description || '—'}</TableCell>
                <TableCell className="text-right space-x-2 whitespace-nowrap">
                  <Button size="sm" variant="outline" aria-label={`Editar ${p.name}`} onClick={() => abrir(p)}>
                    <Pencil className="w-4 h-4" />
                  </Button>
                  <Button size="sm" variant="destructive" aria-label={`Eliminar ${p.name}`} onClick={() => setEliminando(p)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {!cargando && procesos.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">No hay procesos en el catálogo.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>

      <Dialog open={formAbierto} onOpenChange={setFormAbierto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editando ? 'Editar proceso' : 'Nuevo proceso'}</DialogTitle>
            <DialogDescription>El nombre debe ser único en el catálogo.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="proceso-nombre">Nombre</Label>
              <Input id="proceso-nombre" value={form.name} maxLength={100}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="proceso-descripcion">Descripción</Label>
              <Textarea id="proceso-descripcion" value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormAbierto(false)}>Cancelar</Button>
            <Button onClick={guardar} disabled={guardando}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={eliminando !== null} onOpenChange={(abierto) => { if (!abierto) setEliminando(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar proceso</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará «{eliminando?.name}» del catálogo. Si ya se usó en operaciones, no se podrá eliminar.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmarEliminar}>Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
