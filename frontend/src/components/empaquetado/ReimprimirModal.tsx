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
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Loader2, Printer } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { printLabel } from '../../lib/printing';

const MENSAJE_POR_RESULTADO: Record<string, string> = {
    zebra: 'Enviado a la impresora Zebra.',
    pdf: 'PDF generado — se abrió el diálogo de impresión.',
    clipboard: 'Código ZPL copiado al portapapeles (sin impresora disponible).',
};

const MOTIVOS = [
    { value: 'DANIADA', label: 'Etiqueta Dañada' },
    { value: 'PERDIDA', label: 'Etiqueta Perdida' },
    { value: 'ATASCO', label: 'Atasco de Impresora' },
    { value: 'REEMPAQUE', label: 'Reempaque' },
    { value: 'OTRO', label: 'Otro' },
];

interface ReimprimirModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    loteId: number | null;
    codigoLote?: string;
    onReimpreso?: (zpl: string) => void;
}

export function ReimprimirModal({ open, onOpenChange, loteId, codigoLote, onReimpreso }: ReimprimirModalProps) {
    const [motivo, setMotivo] = useState('');
    const [detalleMotivo, setDetalleMotivo] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

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
        if (!loteId) return;
        if (!motivo) {
            toast.error('Selecciona un motivo para reimprimir la etiqueta.');
            return;
        }
        setIsSubmitting(true);
        try {
            const res = await apiClient.post<{ zpl: string; evento: { version: number; secuencia: number } }>(
                `/lotes-produccion/${loteId}/reimprimir/`,
                { motivo, detalle_motivo: detalleMotivo, formato: 'ZPL' }
            );
            const resultado = await printLabel(loteId, res.data.zpl);
            toast.success(`Etiqueta reimpresa (v${res.data.evento.version}). ${MENSAJE_POR_RESULTADO[resultado]}`);
            onReimpreso?.(res.data.zpl);
            handleClose(false);
        } catch (error: any) {
            const msg = error.response?.data?.error?.message || 'Error al reimprimir la etiqueta.';
            toast.error(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Reimprimir Etiqueta</DialogTitle>
                    <DialogDescription>
                        {codigoLote ? `Lote ${codigoLote} — ` : ''}
                        Copia idéntica de la etiqueta vigente. El motivo queda registrado en auditoría.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-2">
                        <Label>Motivo *</Label>
                        <Select value={motivo} onValueChange={setMotivo}>
                            <SelectTrigger>
                                <SelectValue placeholder="Selecciona un motivo" />
                            </SelectTrigger>
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
                            placeholder="Ej: etiqueta rasgada durante el traslado a bodega"
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => handleClose(false)} disabled={isSubmitting}>
                        Cancelar
                    </Button>
                    <Button onClick={handleConfirmar} disabled={isSubmitting || !motivo}>
                        {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Printer className="h-4 w-4 mr-2" />}
                        Reimprimir
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
