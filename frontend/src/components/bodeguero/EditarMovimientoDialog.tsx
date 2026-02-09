
import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';

interface EditarMovimientoDialogProps {
    movimiento: any | null; // Usar tipo any temporalmente para flexibilidad, idealmente usar MovimientoInventario
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export function EditarMovimientoDialog({ movimiento, open, onClose, onSuccess }: EditarMovimientoDialogProps) {
    const [cantidad, setCantidad] = useState('');
    const [documentoRef, setDocumentoRef] = useState('');
    const [razonCambio, setRazonCambio] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (movimiento) {
            setCantidad(movimiento.entrada || movimiento.cantidad || '');
            setDocumentoRef(movimiento.documento_ref || '');
            setRazonCambio('');
        }
    }, [movimiento]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!movimiento) return;

        if (!razonCambio || razonCambio.length < 10) {
            toast.error("Debes proporcionar una razón detallada del cambio (mínimo 10 caracteres).");
            return;
        }

        setIsSubmitting(true);
        try {
            await apiClient.put(`/inventory/movimientos/${movimiento.movimiento_id || movimiento.id}/`, {
                cantidad: parseFloat(cantidad),
                documento_ref: documentoRef,
                razon_cambio: razonCambio
            });
            toast.success("Movimiento actualizado con éxito");
            onSuccess();
            onClose();
        } catch (error: any) {
            console.error('Error al actualizar:', error);
            const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Error al actualizar el movimiento";
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
                    <DialogTitle>Editar Entrada de Inventario</DialogTitle>
                    <DialogDescription>
                        Modifica los detalles de la entrada. Todos los cambios quedarán registrados en la auditoría.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 py-4">
                    <div className="grid w-full items-center gap-1.5">
                        <Label htmlFor="producto">Producto</Label>
                        <Input id="producto" value={movimiento.producto_nombre || movimiento.producto || ''} disabled className="bg-muted" />
                    </div>

                    <div className="grid w-full items-center gap-1.5">
                        <Label htmlFor="cantidad">Cantidad (Entrada)</Label>
                        <Input
                            id="cantidad"
                            type="number"
                            step="0.01"
                            value={cantidad}
                            onChange={(e) => setCantidad(e.target.value)}
                            required
                        />
                        <p className="text-[0.8rem] text-muted-foreground">
                            Valor actual: {movimiento.entrada || movimiento.cantidad}
                        </p>
                    </div>

                    <div className="grid w-full items-center gap-1.5">
                        <Label htmlFor="doc_ref">Documento de Referencia</Label>
                        <Input
                            id="doc_ref"
                            value={documentoRef}
                            onChange={(e) => setDocumentoRef(e.target.value)}
                        />
                    </div>

                    <div className="grid w-full items-center gap-1.5">
                        <Label htmlFor="razon">Razón del Cambio (Obligatorio)</Label>
                        <Textarea
                            id="razon"
                            value={razonCambio}
                            onChange={(e) => setRazonCambio(e.target.value)}
                            placeholder="Explique por qué se está realizando este cambio..."
                            className="resize-none"
                            required
                        />
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
