import React, { useState } from 'react';
import { Button } from '../ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';

interface EliminarMovimientoDialogProps {
    movimiento: any | null; // igual que EditarMovimientoDialog: tipo flexible del row del Kardex
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

// Reversión de un movimiento individual: antes de este diálogo, DELETE
// /inventory/movimientos/{id}/ devolvía 500 sin revertir stock (el destroy()
// genérico de DRF no seteaba la justificación que exige AuditableModelMixin).
// Ahora el backend revierte el stock (MovimientoReversionService) y solo
// entonces elimina — este diálogo pide la justificación obligatoria.
export function EliminarMovimientoDialog({ movimiento, open, onClose, onSuccess }: EliminarMovimientoDialogProps) {
    const [justificacion, setJustificacion] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleConfirm = async () => {
        if (!movimiento) return;
        if (!justificacion.trim()) {
            toast.error('Debes indicar la justificación para eliminar el movimiento.');
            return;
        }

        setIsSubmitting(true);
        try {
            await apiClient.delete(`/inventory/movimientos/${movimiento.movimiento_id || movimiento.id}/`, {
                data: { justificacion },
            });
            toast.success('Movimiento eliminado — stock revertido.');
            setJustificacion('');
            onSuccess();
            onClose();
        } catch (error: any) {
            const errorMsg =
                error.response?.data?.error ||
                error.response?.data?.justificacion ||
                'Error al eliminar el movimiento.';
            toast.error(errorMsg);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!movimiento) return null;

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Eliminar Movimiento</DialogTitle>
                    <DialogDescription>
                        Esta acción revierte el efecto en el stock de la bodega y elimina el movimiento.
                        {movimiento.producto_nombre || movimiento.producto ? (
                            <p className="mt-2 font-medium text-slate-900">
                                {movimiento.producto_nombre || movimiento.producto} — {movimiento.tipo_movimiento} ({movimiento.cantidad})
                            </p>
                        ) : null}
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-2 py-2">
                    <Label htmlFor="eliminar-justificacion">Justificación (Obligatoria)</Label>
                    <Textarea
                        id="eliminar-justificacion"
                        value={justificacion}
                        onChange={(e) => setJustificacion(e.target.value)}
                        placeholder="Explica por qué se elimina este movimiento..."
                        className="resize-none"
                    />
                </div>
                <DialogFooter>
                    <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
                        Cancelar
                    </Button>
                    <Button type="button" variant="destructive" onClick={handleConfirm} disabled={isSubmitting}>
                        {isSubmitting ? 'Eliminando...' : 'Eliminar y Revertir'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
