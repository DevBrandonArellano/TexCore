import React, { useState } from 'react';
import apiClient from '../../lib/axios';
import { Maquina, Producto } from '../../lib/types';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { toast } from 'sonner';
import { AxiosError } from 'axios';

/**
 * Diálogo para registrar una transformación máquina a máquina dentro de una OP.
 *
 * El producto de ENTRADA lo deriva el backend (continuidad de cadena): es la
 * salida de la transformación anterior, o la materia prima de la OP si es la
 * primera. Por eso aquí solo se captura la máquina, el producto de salida (nuevo
 * código), los pesos y las observaciones. La merma se calcula sola.
 */
interface RegistrarTransformacionProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ordenId: number;
  maquinas: Maquina[];
  productos: Producto[];
  /** Código del producto que entrará (informativo; lo determina el backend). */
  entradaEsperada?: string | null;
  onSuccess: () => void;
}

const ahoraLocal = () => {
  // YYYY-MM-DDTHH:mm para <input type="datetime-local">
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 16);
};

/**
 * El backend puede devolver `detail` como string o como dict de errores por
 * campo (p.ej. {"peso_salida": "..."} o {"maquina": ["..."]}). Esta función
 * normaliza ambos casos a un mensaje legible.
 */
const extraerError = (detail: unknown): string => {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    const mensajes = Object.values(detail as Record<string, unknown>)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .map((v) => String(v));
    if (mensajes.length) return mensajes.join(' ');
  }
  return 'No se pudo registrar la transformación.';
};

export function RegistrarTransformacion({
  open,
  onOpenChange,
  ordenId,
  maquinas,
  productos,
  entradaEsperada,
  onSuccess,
}: RegistrarTransformacionProps) {
  const vacio = {
    maquina: '',
    producto_salida: '',
    peso_entrada: '',
    peso_salida: '',
    fecha_inicio: ahoraLocal(),
    fecha_fin: ahoraLocal(),
    observaciones: '',
  };
  const [form, setForm] = useState(vacio);
  const [enviando, setEnviando] = useState(false);

  const merma = (() => {
    const e = parseFloat(form.peso_entrada);
    const s = parseFloat(form.peso_salida);
    if (isNaN(e) || isNaN(s)) return null;
    return e - s;
  })();

  const validar = (): string | null => {
    if (!form.maquina) return 'Selecciona la máquina.';
    if (!form.producto_salida) return 'Selecciona el producto de salida (nuevo código).';
    const e = parseFloat(form.peso_entrada);
    const s = parseFloat(form.peso_salida);
    if (isNaN(e) || e <= 0) return 'El peso de entrada debe ser mayor que cero.';
    if (isNaN(s) || s < 0) return 'El peso de salida no es válido.';
    if (s > e) return 'El peso de salida no puede superar el de entrada (merma negativa).';
    if (form.fecha_fin < form.fecha_inicio) return 'La fecha de fin no puede ser anterior al inicio.';
    return null;
  };

  const handleSubmit = async () => {
    const error = validar();
    if (error) {
      toast.error(error);
      return;
    }
    setEnviando(true);
    try {
      await apiClient.post(`/ordenes-produccion/${ordenId}/registrar-transformacion/`, {
        maquina: parseInt(form.maquina, 10),
        producto_salida: parseInt(form.producto_salida, 10),
        peso_entrada: form.peso_entrada,
        peso_salida: form.peso_salida,
        fecha_inicio: new Date(form.fecha_inicio).toISOString(),
        fecha_fin: new Date(form.fecha_fin).toISOString(),
        observaciones: form.observaciones,
      });
      toast.success('Transformación registrada correctamente.');
      setForm(vacio);
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      const ax = err as AxiosError<{ detail?: unknown }>;
      toast.error(extraerError(ax.response?.data?.detail));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Registrar Transformación</DialogTitle>
          <DialogDescription>
            Registra el paso de una máquina. El producto de entrada se encadena
            automáticamente
            {entradaEsperada ? ` (entrará: ${entradaEsperada})` : ''}.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label>Máquina</Label>
            <Select value={form.maquina} onValueChange={(v) => setForm({ ...form, maquina: v })}>
              <SelectTrigger><SelectValue placeholder="Selecciona la máquina" /></SelectTrigger>
              <SelectContent>
                {maquinas.map((m) => (
                  <SelectItem key={m.id} value={String(m.id)}>{m.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label>Producto de salida (nuevo código)</Label>
            <Select value={form.producto_salida} onValueChange={(v) => setForm({ ...form, producto_salida: v })}>
              <SelectTrigger><SelectValue placeholder="Producto que sale de la máquina" /></SelectTrigger>
              <SelectContent>
                {productos.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>{p.codigo} — {p.descripcion}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-2">
              <Label>Peso entrada (kg)</Label>
              <Input
                type="number" step="0.001" min="0"
                value={form.peso_entrada}
                onChange={(e) => setForm({ ...form, peso_entrada: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label>Peso salida (kg)</Label>
              <Input
                type="number" step="0.001" min="0"
                value={form.peso_salida}
                onChange={(e) => setForm({ ...form, peso_salida: e.target.value })}
              />
            </div>
          </div>

          {merma !== null && (
            <p className={`text-sm ${merma < 0 ? 'text-red-600' : 'text-muted-foreground'}`}>
              Merma calculada: <strong>{merma.toFixed(3)} kg</strong>
            </p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-2">
              <Label>Inicio</Label>
              <Input
                type="datetime-local"
                value={form.fecha_inicio}
                onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label>Fin</Label>
              <Input
                type="datetime-local"
                value={form.fecha_fin}
                onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label>Observaciones (opcional)</Label>
            <Textarea
              value={form.observaciones}
              onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
              placeholder="Incidencias, parámetros del proceso, etc."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={enviando}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={enviando}>
            {enviando ? 'Registrando…' : 'Registrar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default RegistrarTransformacion;
