import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { Loader2, OctagonPause } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { CategoriaParoMaquina } from '../../lib/types';

// Reason codes = Seis Grandes Pérdidas (OEE for Operators — Productivity Press)
const CATEGORIAS: { value: CategoriaParoMaquina; label: string }[] = [
    { value: 'AVERIA', label: 'Avería / Falla de Equipo' },
    { value: 'SETUP', label: 'Setup y Ajustes' },
    { value: 'MICROPARO', label: 'Paro Menor / Microparo' },
    { value: 'VELOCIDAD_REDUCIDA', label: 'Velocidad Reducida' },
    { value: 'RECHAZO_ARRANQUE', label: 'Rechazo de Arranque' },
    { value: 'DEFECTO_PROCESO', label: 'Defecto de Proceso' },
    { value: 'FALTA_MATERIAL', label: 'Falta de Material' },
    { value: 'MANTENIMIENTO_PLANIFICADO', label: 'Mantenimiento Planificado' },
    { value: 'OTRO', label: 'Otro' },
];

interface RegistrarParoModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    maquinaId: number | null;
    maquinaNombre?: string;
    onRegistrado?: () => void;
}

export function RegistrarParoModal({ open, onOpenChange, maquinaId, maquinaNombre, onRegistrado }: RegistrarParoModalProps) {
    const [categoria, setCategoria] = useState<string>('');
    const [inicio, setInicio] = useState('');
    const [fin, setFin] = useState('');
    const [planificado, setPlanificado] = useState(false);
    const [descripcion, setDescripcion] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const resetForm = () => {
        setCategoria('');
        setInicio('');
        setFin('');
        setPlanificado(false);
        setDescripcion('');
    };

    const handleClose = (nextOpen: boolean) => {
        if (!isSubmitting) {
            if (!nextOpen) resetForm();
            onOpenChange(nextOpen);
        }
    };

    const handleConfirmar = async () => {
        if (!maquinaId) return;
        if (!categoria) {
            toast.error('Selecciona una categoría (reason code) para el paro.');
            return;
        }
        if (!inicio) {
            toast.error('Indica la fecha/hora de inicio del paro.');
            return;
        }
        setIsSubmitting(true);
        try {
            const payload: Record<string, unknown> = {
                maquina: maquinaId,
                categoria,
                inicio,
                planificado,
            };
            if (fin) payload.fin = fin;
            if (descripcion) payload.descripcion = descripcion;

            await apiClient.post('/paros-maquina/', payload);
            toast.success('Paro de máquina registrado correctamente.');
            onRegistrado?.();
            handleClose(false);
        } catch (error: any) {
            const msg = error.response?.data?.error?.message || 'Error al registrar el paro de máquina.';
            toast.error(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Registrar Paro de Máquina</DialogTitle>
                    <DialogDescription>
                        {maquinaNombre ? `${maquinaNombre} — ` : ''}
                        Reason code de downtime (Seis Grandes Pérdidas). Alimenta el cálculo de OEE.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-2">
                        <Label>Categoría (Reason Code) *</Label>
                        <Select value={categoria} onValueChange={setCategoria}>
                            <SelectTrigger>
                                <SelectValue placeholder="Selecciona una categoría" />
                            </SelectTrigger>
                            <SelectContent>
                                {CATEGORIAS.map((c) => (
                                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="paro-inicio">Inicio *</Label>
                            <Input
                                id="paro-inicio"
                                type="datetime-local"
                                value={inicio}
                                onChange={(e) => setInicio(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="paro-fin">Fin (vacío = en curso)</Label>
                            <Input
                                id="paro-fin"
                                type="datetime-local"
                                value={fin}
                                onChange={(e) => setFin(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="paro-planificado"
                            checked={planificado}
                            onCheckedChange={(v) => setPlanificado(Boolean(v))}
                        />
                        <Label htmlFor="paro-planificado" className="text-sm font-normal cursor-pointer">
                            Paro planificado (no penaliza Disponibilidad)
                        </Label>
                    </div>
                    <div className="space-y-2">
                        <Label>Descripción (opcional)</Label>
                        <Textarea
                            value={descripcion}
                            onChange={(e) => setDescripcion(e.target.value)}
                            placeholder="Ej: rodamiento del motor principal"
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => handleClose(false)} disabled={isSubmitting}>
                        Cancelar
                    </Button>
                    <Button onClick={handleConfirmar} disabled={isSubmitting}>
                        {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <OctagonPause className="h-4 w-4 mr-2" />}
                        Registrar Paro
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
