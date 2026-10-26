import React, { useState } from 'react';
import { Pencil, Power, PowerOff, Workflow } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { procesosTintoreriaApi } from '../../lib/api/procesosTintoreriaApi';
import { getApiErrorMessage } from '../../lib/apiError';
import type { ProcesoTintoreria, TipoProcesoTintoreria } from '../../lib/types';

const TIPOS: { value: TipoProcesoTintoreria; label: string }[] = [
  { value: 'pre_tratamiento', label: 'Pre-Tratamiento' },
  { value: 'colorante', label: 'Colorante' },
  { value: 'auxiliar', label: 'Auxiliar' },
  { value: 'lavado', label: 'Lavado' },
  { value: 'acabado', label: 'Acabado' },
];

interface FormProceso {
  codigo: string;
  nombre: string;
  tipo: TipoProcesoTintoreria;
  descripcion: string;
}

const VACIO: FormProceso = { codigo: '', nombre: '', tipo: 'pre_tratamiento', descripcion: '' };

/**
 * Catálogo de procesos de tintorería de la sede (DESCRUDE, LAVADO REDUCTIVO…) que se
 * eligen en cada fase de una receta y que el Jefe de Área asigna a sus máquinas.
 * No se eliminan: un proceso usado por recetas está protegido; se desactiva.
 * El código no se edita porque las recetas lo citan (ISO 9001).
 */
interface ManageProcesosTintoreriaProps {
  /** Se llama tras cada cambio guardado, para refrescar los procesos que usan las recetas. */
  onCatalogoCambiado?: () => void;
}

export function ManageProcesosTintoreria({ onCatalogoCambiado }: ManageProcesosTintoreriaProps = {}) {
  const { datos, cargando, error, recargar } = useCargaRemota(
    () => procesosTintoreriaApi.listar(), 'procesos-tintoreria',
  );
  const procesos = datos ?? [];
  const [editando, setEditando] = useState<ProcesoTintoreria | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [form, setForm] = useState<FormProceso>(VACIO);
  const [guardando, setGuardando] = useState(false);

  const abrir = (proceso: ProcesoTintoreria | null) => {
    setEditando(proceso);
    setForm(proceso
      ? { codigo: proceso.codigo, nombre: proceso.nombre, tipo: proceso.tipo, descripcion: proceso.descripcion ?? '' }
      : VACIO);
    setFormAbierto(true);
  };

  const guardar = async () => {
    const nombre = form.nombre.trim();
    const codigo = form.codigo.trim().toUpperCase();
    if (!nombre || (!editando && !codigo)) {
      toast.error('El código y el nombre son requeridos.');
      return;
    }
    const cambios = { nombre, tipo: form.tipo, descripcion: form.descripcion.trim() };
    setGuardando(true);
    try {
      if (editando) await procesosTintoreriaApi.actualizar(editando.id, cambios);
      else await procesosTintoreriaApi.crear({ codigo, ...cambios });
      toast.success(editando ? 'Proceso actualizado.' : 'Proceso creado.');
      setFormAbierto(false);
      recargar();
      onCatalogoCambiado?.();
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'No se pudo guardar el proceso.'));
    } finally {
      setGuardando(false);
    }
  };

  const cambiarEstado = async (proceso: ProcesoTintoreria) => {
    try {
      await procesosTintoreriaApi.actualizar(proceso.id, { activo: !proceso.activo });
      toast.success(proceso.activo ? 'Proceso desactivado.' : 'Proceso activado.');
      recargar();
      onCatalogoCambiado?.();
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'No se pudo cambiar el estado del proceso.'));
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Procesos de Tintorería</CardTitle>
          <CardDescription>
            Procesos que se usan en las fases de las recetas y que ejecutan las máquinas. Un proceso
            inactivo deja de ofrecerse en recetas nuevas y en las máquinas.
          </CardDescription>
        </div>
        <Button onClick={() => abrir(null)}><Workflow className="w-4 h-4 mr-2" /> Nuevo proceso</Button>
      </CardHeader>
      <CardContent>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Código</TableHead>
              <TableHead>Nombre</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {procesos.map((p) => (
              <TableRow key={p.id} className={p.activo ? '' : 'text-muted-foreground'}>
                <TableCell className="font-mono font-medium">{p.codigo}</TableCell>
                <TableCell>{p.nombre}</TableCell>
                <TableCell>{p.tipo_display ?? p.tipo}</TableCell>
                <TableCell>
                  <Badge variant={p.activo ? 'secondary' : 'outline'}>{p.activo ? 'Activo' : 'Inactivo'}</Badge>
                </TableCell>
                <TableCell className="text-right space-x-2 whitespace-nowrap">
                  <Button size="sm" variant="outline" aria-label={`Editar ${p.codigo}`} onClick={() => abrir(p)}>
                    <Pencil className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    aria-label={`${p.activo ? 'Desactivar' : 'Activar'} ${p.codigo}`}
                    onClick={() => cambiarEstado(p)}
                  >
                    {p.activo ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {!cargando && procesos.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No hay procesos de tintorería en la sede.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>

      <Dialog open={formAbierto} onOpenChange={setFormAbierto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editando ? 'Editar proceso' : 'Nuevo proceso'}</DialogTitle>
            <DialogDescription>
              {editando ? 'El código no se modifica: las recetas lo citan.' : 'El código debe ser único en la sede.'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="proceso-codigo">Código</Label>
              <Input id="proceso-codigo" value={form.codigo} maxLength={50} disabled={editando !== null}
                onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="proceso-nombre">Nombre</Label>
              <Input id="proceso-nombre" value={form.nombre} maxLength={100}
                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="proceso-tipo">Tipo</Label>
              <Select value={form.tipo} onValueChange={(v) => setForm((f) => ({ ...f, tipo: v as TipoProcesoTintoreria }))}>
                <SelectTrigger id="proceso-tipo" aria-label="Tipo"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIPOS.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="proceso-descripcion">Descripción</Label>
              <Textarea id="proceso-descripcion" value={form.descripcion}
                onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormAbierto(false)}>Cancelar</Button>
            <Button onClick={guardar} disabled={guardando}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
