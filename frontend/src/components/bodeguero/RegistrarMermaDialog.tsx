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
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ProductSelect } from '../ui/product-select';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { Producto, Bodega } from '../../lib/types';

interface RegistrarMermaDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    productos: Producto[];
    bodegas: Bodega[];
    onSuccess: () => void;
}

// Control de mermas: MERMA es una SALIDA de inventario (el material se pierde)
// — descuenta StockBodega igual que VENTA/CONSUMO (inventory/views.py,
// MovimientoInventarioViewSet.create()). Antes de este componente no existía
// UI para registrar mermas; solo se creaban vía script/ORM en registro_lote.py.
export function RegistrarMermaDialog({ open, onOpenChange, productos, bodegas, onSuccess }: RegistrarMermaDialogProps) {
    const [productoId, setProductoId] = useState('');
    const [bodegaId, setBodegaId] = useState('');
    const [cantidad, setCantidad] = useState('');
    const [motivo, setMotivo] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const resetForm = () => {
        setProductoId('');
        setBodegaId('');
        setCantidad('');
        setMotivo('');
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!productoId || !bodegaId || !cantidad || parseFloat(cantidad) <= 0) {
            toast.error('Producto, Bodega y Cantidad son requeridos.');
            return;
        }
        if (!motivo.trim()) {
            toast.error('Debes indicar el motivo de la merma.');
            return;
        }

        setIsSubmitting(true);
        try {
            await apiClient.post('/inventory/movimientos/', {
                tipo_movimiento: 'MERMA',
                producto: parseInt(productoId),
                bodega_origen: parseInt(bodegaId),
                cantidad: parseFloat(cantidad),
                observaciones: motivo,
            });
            toast.success('Merma registrada — stock descontado.');
            resetForm();
            onOpenChange(false);
            onSuccess();
        } catch (error: any) {
            const errorMsg = error.response?.data?.error || 'Ocurrió un error al registrar la merma.';
            toast.error('Error', { description: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg) });
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Registrar Merma</DialogTitle>
                    <DialogDescription>
                        Registra material perdido o desperdiciado. Se descuenta del stock de la bodega de origen.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 py-2">
                    <div className="space-y-2">
                        <Label htmlFor="merma-producto">Producto</Label>
                        <ProductSelect productos={productos} value={productoId} onValueChange={setProductoId} />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="merma-bodega">Bodega de Origen</Label>
                        <Select value={bodegaId} onValueChange={setBodegaId}>
                            <SelectTrigger id="merma-bodega"><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger>
                            <SelectContent>
                                {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="merma-cantidad">Cantidad</Label>
                        <Input
                            id="merma-cantidad"
                            type="number"
                            step="any"
                            value={cantidad}
                            onChange={(e) => setCantidad(e.target.value)}
                            placeholder="0.00"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="merma-motivo">Motivo de la Merma</Label>
                        <Textarea
                            id="merma-motivo"
                            value={motivo}
                            onChange={(e) => setMotivo(e.target.value)}
                            placeholder="Ej: Material dañado en bodega, hilo defectuoso..."
                            className="resize-none"
                        />
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="secondary" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting ? 'Registrando...' : 'Registrar Merma'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
