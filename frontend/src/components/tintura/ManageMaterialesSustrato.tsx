import React, { useState } from 'react';
import { Layers, Pencil, Power, PowerOff } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { materialesSustratoApi } from '../../lib/api/materialesSustratoApi';
import { getApiErrorMessage } from '../../lib/apiError';
import type { MaterialSustrato } from '../../lib/types';

const NOMBRE_MIN = 2;
const NOMBRE_MAX = 60;
const FALTA_JUSTIFICACION = 'Indique la justificación del cambio: queda en la auditoría.';

interface CampoJustificacionProps {
  id: string;
  valor: string;
  onChange: (valor: string) => void;
}

function CampoJustificacion({ id, valor, onChange }: CampoJustificacionProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>Justificación</Label>
      <Textarea id={id} value={valor} placeholder="Por qué se hace el cambio (queda en la auditoría)"
        onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

interface ManageMaterialesSustratoProps {
  /** Se llama tras cada cambio guardado, para refrescar las fórmulas que muestran el material. */
  onCatalogoCambiado?: () => void;
}

/**
 * Catálogo de materiales (tipos de sustrato) de la sede: algodón, poliéster, lino…
 * Cada color tiene una fórmula por material. No se eliminan desde aquí: un material
 * usado por fórmulas se desactiva y deja de ofrecerse en las fórmulas nuevas.
 * Renombrar, activar o desactivar pide una justificación, que queda en la auditoría.
 */
export function ManageMaterialesSustrato({ onCatalogoCambiado }: ManageMaterialesSustratoProps = {}) {
  const { datos, cargando, error, recargar } = useCargaRemota(
    () => materialesSustratoApi.listar(), 'materiales-sustrato',
  );
  const materiales = datos ?? [];
  const [editando, setEditando] = useState<MaterialSustrato | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [nombre, setNombre] = useState('');
  const [justificacion, setJustificacion] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [cambiandoEstado, setCambiandoEstado] = useState<MaterialSustrato | null>(null);

  const abrir = (material: MaterialSustrato | null) => {
    setEditando(material);
    setNombre(material?.nombre ?? '');
    setJustificacion('');
    setFormAbierto(true);
  };

  const pedirCambioDeEstado = (material: MaterialSustrato) => {
    setJustificacion('');
    setCambiandoEstado(material);
  };

  const trasGuardar = (mensaje: string) => {
    toast.success(mensaje);
    recargar();
    onCatalogoCambiado?.();
  };

  const guardar = async () => {
    const limpio = nombre.trim();
    if (limpio.length < NOMBRE_MIN) {
      toast.error(`El nombre debe tener al menos ${NOMBRE_MIN} caracteres.`);
      return;
    }
    const motivo = justificacion.trim();
    if (editando && !motivo) {
      toast.error(FALTA_JUSTIFICACION);
      return;
    }
    setGuardando(true);
    try {
      if (editando) await materialesSustratoApi.actualizar(editando.id, { nombre: limpio, _justificacion_auditoria: motivo });
      else await materialesSustratoApi.crear({ nombre: limpio });
      setFormAbierto(false);
      trasGuardar(editando ? 'Material actualizado.' : 'Material creado.');
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'No se pudo guardar el material.'));
    } finally {
      setGuardando(false);
    }
  };

  const confirmarCambioDeEstado = async () => {
    if (!cambiandoEstado) return;
    const motivo = justificacion.trim();
    if (!motivo) {
      toast.error(FALTA_JUSTIFICACION);
      return;
    }
    const material = cambiandoEstado;
    setGuardando(true);
    try {
      await materialesSustratoApi.actualizar(material.id, { activo: !material.activo, _justificacion_auditoria: motivo });
      setCambiandoEstado(null);
      trasGuardar(material.activo ? 'Material desactivado.' : 'Material activado.');
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'No se pudo cambiar el estado del material.'));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div>
          <CardTitle>Materiales</CardTitle>
          <CardDescription>
            Tipos de sustrato con los que trabaja la tintorería. Cada color tiene una fórmula por
            material. Un material inactivo deja de ofrecerse en las fórmulas nuevas.
          </CardDescription>
        </div>
        <Button onClick={() => abrir(null)}><Layers className="w-4 h-4 mr-2" /> Nuevo material</Button>
      </CardHeader>
      <CardContent>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {materiales.map((m) => (
              <TableRow key={m.id} className={m.activo ? '' : 'text-muted-foreground'}>
                <TableCell className="font-medium">{m.nombre}</TableCell>
                <TableCell>
                  <Badge variant={m.activo ? 'secondary' : 'outline'}>{m.activo ? 'Activo' : 'Inactivo'}</Badge>
                </TableCell>
                <TableCell className="text-right space-x-2 whitespace-nowrap">
                  <Button size="sm" variant="outline" aria-label={`Editar ${m.nombre}`} onClick={() => abrir(m)}>
                    <Pencil className="w-4 h-4" />
                  </Button>
                  <Button size="sm" variant="outline" aria-label={`${m.activo ? 'Desactivar' : 'Activar'} ${m.nombre}`}
                    onClick={() => pedirCambioDeEstado(m)}>
                    {m.activo ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {!cargando && materiales.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  No hay materiales en la sede.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>

      <Dialog open={formAbierto} onOpenChange={setFormAbierto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editando ? 'Editar material' : 'Nuevo material'}</DialogTitle>
            <DialogDescription>
              {editando
                ? 'Cambiar el nombre no afecta a las fórmulas que ya usan este material.'
                : 'El nombre debe ser único en la sede.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="material-nombre">Nombre</Label>
            <Input id="material-nombre" value={nombre} maxLength={NOMBRE_MAX} placeholder="Ej: Lino"
              onChange={(e) => setNombre(e.target.value)} />
          </div>
          {editando && <CampoJustificacion id="material-justificacion" valor={justificacion} onChange={setJustificacion} />}
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormAbierto(false)}>Cancelar</Button>
            <Button onClick={guardar} disabled={guardando}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={cambiandoEstado !== null} onOpenChange={(abierto) => { if (!abierto) setCambiandoEstado(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {cambiandoEstado?.activo ? 'Desactivar' : 'Activar'} «{cambiandoEstado?.nombre}»
            </DialogTitle>
            <DialogDescription>
              {cambiandoEstado?.activo
                ? 'Dejará de ofrecerse en las fórmulas nuevas; las que ya lo usan lo conservan.'
                : 'Volverá a ofrecerse en las fórmulas nuevas.'}
            </DialogDescription>
          </DialogHeader>
          <CampoJustificacion id="estado-justificacion" valor={justificacion} onChange={setJustificacion} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCambiandoEstado(null)}>Cancelar</Button>
            <Button onClick={confirmarCambioDeEstado} disabled={guardando}>Confirmar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
