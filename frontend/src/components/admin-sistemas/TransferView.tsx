import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ProductSelect } from '../ui/product-select';
import { ShieldCheck } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import type { Producto, Bodega } from '../../lib/types';
import { type StockItem, validateTransfer } from './inventoryUtils';

interface TransferViewProps {
  productos: Producto[];
  bodegas: Bodega[];
  stock: StockItem[];
}

function TransferViewImpl({ productos, bodegas, stock }: TransferViewProps) {
  const [formData, setFormData] = useState({ producto_id: '', bodega_origen_id: '', bodega_destino_id: '', cantidad: '', lote_id: '', observaciones: '', _justificacion_auditoria: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const availableLots = useMemo(() => {
    if (!formData.producto_id || !formData.bodega_origen_id) return [];
    return stock.filter(item =>
      String(item.producto_id ?? '') === formData.producto_id &&
      String(item.bodega_id ?? '') === formData.bodega_origen_id &&
      parseFloat(item.cantidad) > 0
    );
  }, [formData.producto_id, formData.bodega_origen_id, stock]);

  const validate = () => {
    const newErrors = validateTransfer(formData, availableLots);
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setIsSubmitting(true);
    try {
      await apiClient.post('/inventory/transferencias/', {
        producto_id: parseInt(formData.producto_id),
        bodega_origen_id: parseInt(formData.bodega_origen_id),
        bodega_destino_id: parseInt(formData.bodega_destino_id),
        cantidad: parseFloat(formData.cantidad),
        lote_id: (formData.lote_id && formData.lote_id !== 'null') ? parseInt(formData.lote_id) : null,
        observaciones: formData.observaciones,
        _justificacion_auditoria: formData._justificacion_auditoria,
      });
      toast.success('Transferencia exitosa');
      setFormData({ producto_id: '', bodega_origen_id: '', bodega_destino_id: '', cantidad: '', lote_id: '', observaciones: '', _justificacion_auditoria: '' });
    } catch (error: any) {
      toast.error('Error', { description: error.response?.data?.error || 'Error en transferencia' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transferencia de Stock</CardTitle>
        <CardDescription>Mover materiales entre bodegas.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Producto</Label>
              <ProductSelect productos={productos} value={formData.producto_id} onValueChange={v => setFormData(p => ({ ...p, producto_id: v, lote_id: '' }))} />
              {errors.producto_id && <p className="text-xs text-destructive">{errors.producto_id}</p>}
            </div>
            <div className="space-y-2">
              <Label>Bodega Origen</Label>
              <Select value={formData.bodega_origen_id} onValueChange={v => setFormData(p => ({ ...p, bodega_origen_id: v, lote_id: '' }))}>
                <SelectTrigger><SelectValue placeholder="Origen" /></SelectTrigger>
                <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
              </Select>
              {errors.bodega_origen_id && <p className="text-xs text-destructive">{errors.bodega_origen_id}</p>}
            </div>
            <div className="space-y-2">
              <Label>Lote (Opcional si el producto no usa lotes)</Label>
              <Select value={formData.lote_id} onValueChange={v => setFormData(p => ({ ...p, lote_id: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder={availableLots.length > 0 ? "Selecciona un lote" : "No hay lotes disponibles"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="null">Sin Lote (General)</SelectItem>
                  {availableLots.filter(s => s.lote_id).map(s => (
                    <SelectItem key={s.id} value={s.lote_id!.toString()}>
                      {s.lote_codigo} ({s.cantidad} disponibles)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.stock && <p className="text-xs text-destructive font-bold">{errors.stock}</p>}
            </div>
            <div className="space-y-2">
              <Label>Cantidad</Label>
              <Input type="number" step="any" value={formData.cantidad} onChange={e => setFormData(p => ({ ...p, cantidad: e.target.value }))} />
              {errors.cantidad && <p className="text-xs text-destructive font-bold">{errors.cantidad}</p>}
            </div>
            <div className="space-y-2">
              <Label>Bodega Destino</Label>
              <Select value={formData.bodega_destino_id} onValueChange={v => setFormData(p => ({ ...p, bodega_destino_id: v }))}>
                <SelectTrigger><SelectValue placeholder="Destino" /></SelectTrigger>
                <SelectContent>{bodegas.filter(b => b.id.toString() !== formData.bodega_origen_id).map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
              </Select>
              {errors.bodega_destino_id && <p className="text-xs text-destructive">{errors.bodega_destino_id}</p>}
            </div>
            <div className="space-y-2">
              <Label>Observaciones</Label>
              <Input value={formData.observaciones} onChange={e => setFormData(p => ({ ...p, observaciones: e.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2 p-3 bg-primary/5 rounded-lg border border-primary/20">
              <Label className="flex items-center gap-2 font-bold text-primary">
                <ShieldCheck className="w-4 h-4" /> Justificación Obligatoria <span className="text-destructive">*</span>
              </Label>
              <Input value={formData._justificacion_auditoria} onChange={e => setFormData(p => ({ ...p, _justificacion_auditoria: e.target.value }))} placeholder="Motivo del traslado..." className="bg-background" />
              {errors._justificacion_auditoria && <p className="text-sm text-destructive">{errors._justificacion_auditoria}</p>}
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting}>Transferir</Button>
        </form>
      </CardContent>
    </Card>
  );
}

export const TransferView = React.memo(TransferViewImpl);
