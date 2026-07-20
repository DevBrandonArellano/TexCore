import React, { useState, useEffect } from 'react';
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
import { Alert, AlertDescription } from '../ui/alert';
import { Loader2, Tag, TriangleAlert } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { LoteProduccion } from '../../lib/types';
import { printLabel } from '../../lib/printing';

const MENSAJE_POR_RESULTADO: Record<string, string> = {
    zebra: 'Enviada a la impresora Zebra.',
    pdf: 'PDF generado — se abrió el diálogo de impresión.',
    clipboard: 'Código ZPL copiado al portapapeles (sin impresora disponible).',
};

const MOTIVOS = [
    { value: 'CORRECCION_PESO', label: 'Corrección de Peso' },
    { value: 'RECLASIFICACION', label: 'Reclasificación de Calidad' },
    { value: 'REEMPAQUE', label: 'Reempaque' },
    { value: 'OTRO', label: 'Otro' },
];

const CALIDAD_OPTIONS = [
    { value: 'primera', label: 'Primera Calidad' },
    { value: 'segunda', label: 'Segunda Calidad' },
    { value: 'saldo', label: 'Saldo / Retazo' },
];

interface ReetiquetarModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    lote: LoteProduccion | null;
    onReetiquetado?: (zpl: string) => void;
}

export function ReetiquetarModal({ open, onOpenChange, lote, onReetiquetado }: ReetiquetarModalProps) {
    const [motivo, setMotivo] = useState('');
    const [detalleMotivo, setDetalleMotivo] = useState('');
    const [pesoNeto, setPesoNeto] = useState('');
    const [calidad, setCalidad] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (lote) {
            setPesoNeto(String(lote.peso_neto_producido ?? ''));
            setCalidad(lote.clasificacion_calidad ?? '');
        }
    }, [lote]);

    const handleClose = (nextOpen: boolean) => {
        if (!isSubmitting) {
            if (!nextOpen) {
                setMotivo('');
                setDetalleMotivo('');
            }
            onOpenChange(nextOpen);
        }
    };

    const handleConfirmar = async () => {
        if (!lote) return;
        if (!motivo) {
            toast.error('Selecciona un motivo para reetiquetar.');
            return;
        }

        const cambios: Record<string, number | string> = {};
        if (pesoNeto !== '' && Number(pesoNeto) !== lote.peso_neto_producido) {
            cambios.peso_neto_producido = Number(pesoNeto);
        }
        if (calidad && calidad !== lote.clasificacion_calidad) {
            cambios.clasificacion_calidad = calidad;
        }
        if (Object.keys(cambios).length === 0) {
            toast.error('Debes modificar al menos un dato (peso neto o calidad).');
            return;
        }

        setIsSubmitting(true);
        try {
            const res = await apiClient.post<{ zpl: string; evento: { version: number } }>(
                `/lotes-produccion/${lote.id}/reetiquetar/`,
                { cambios, motivo, detalle_motivo: detalleMotivo, formato: 'ZPL' }
            );
            const resultado = await printLabel(lote.id, res.data.zpl);
            toast.success(`Lote reetiquetado (v${res.data.evento.version}). Etiqueta anterior anulada. ${MENSAJE_POR_RESULTADO[resultado]}`);
            onReetiquetado?.(res.data.zpl);
            handleClose(false);
        } catch (error: any) {
            const msg = error.response?.data?.error?.message || 'Error al reetiquetar el lote.';
            toast.error(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2"><Tag className="h-4 w-4" /> Reetiquetar Lote</DialogTitle>
                    <DialogDescription>
                        {lote ? `Lote ${lote.codigo_lote} — ` : ''}
                        Cambia datos de la etiqueta. La versión anterior queda anulada; el código de lote no cambia.
                    </DialogDescription>
                </DialogHeader>
                <Alert variant="destructive" className="py-2">
                    <TriangleAlert className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                        Esta acción requiere autorización de supervisor y queda registrada en auditoría.
                    </AlertDescription>
                </Alert>
                <div className="space-y-4 py-2">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <Label>Peso Neto (kg)</Label>
                            <Input
                                type="number" step="0.001"
                                value={pesoNeto}
                                onChange={(e) => setPesoNeto(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Calidad</Label>
                            <Select value={calidad} onValueChange={setCalidad}>
                                <SelectTrigger><SelectValue placeholder="Sin cambio" /></SelectTrigger>
                                <SelectContent>
                                    {CALIDAD_OPTIONS.map((c) => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label>Motivo *</Label>
                        <Select value={motivo} onValueChange={setMotivo}>
                            <SelectTrigger><SelectValue placeholder="Selecciona un motivo" /></SelectTrigger>
                            <SelectContent>
                                {MOTIVOS.map((m) => (
                                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label>Detalle (opcional)</Label>
                        <Textarea
                            value={detalleMotivo}
                            onChange={(e) => setDetalleMotivo(e.target.value)}
                            placeholder="Ej: re-pesaje en báscula certificada tras reclamo de cliente"
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => handleClose(false)} disabled={isSubmitting}>
                        Cancelar
                    </Button>
                    <Button onClick={handleConfirmar} disabled={isSubmitting || !motivo} variant="destructive">
                        {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Tag className="h-4 w-4 mr-2" />}
                        Reetiquetar
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
