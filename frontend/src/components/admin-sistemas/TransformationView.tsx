import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { Producto, Bodega, LoteProduccion } from '../../lib/types';

interface TransformationViewProps {
  productos: Producto[];
  bodegas: Bodega[];
  lotesProduccion: LoteProduccion[];
}

export const TransformationView = ({ productos, bodegas, lotesProduccion }: TransformationViewProps) => {
  const [formData, setFormData] = useState({
    bodega_origen_id: '',
    bodega_destino_id: '',
    producto_origen_id: '',
    producto_destino_id: '',
    lote_origen_id: '', // ID del lote origen (LoteProduccion existente)
    nuevo_lote_codigo: '', // Opcional: para crear un nuevo lote destino o mantener el mismo
    cantidad: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.bodega_origen_id || !formData.bodega_destino_id || !formData.producto_origen_id || !formData.producto_destino_id || !formData.cantidad) {
      toast.error('Todos los campos son obligatorios, excepto el nuevo código de lote.');
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post('/inventory/transformaciones/', {
        bodega_origen_id: parseInt(formData.bodega_origen_id),
        bodega_destino_id: parseInt(formData.bodega_destino_id),
        producto_origen_id: parseInt(formData.producto_origen_id),
        producto_destino_id: parseInt(formData.producto_destino_id),
        lote_origen_id: formData.lote_origen_id ? parseInt(formData.lote_origen_id) : null,
        nuevo_lote_codigo: formData.nuevo_lote_codigo,
        cantidad: parseFloat(formData.cantidad),
      });
      toast.success('Transformación realizada con éxito.');
      setFormData({
        bodega_origen_id: '',
        bodega_destino_id: '',
        producto_origen_id: '',
        producto_destino_id: '',
        lote_origen_id: '',
        nuevo_lote_codigo: '',
        cantidad: '',
      });
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Error al procesar la transformación.';
      toast.error('Error', { description: errorMsg });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transformación de Producto</CardTitle>
        <CardDescription>Registra el cambio de código de un producto (ej. Lana Cruda a Tinturada) moviéndolo entre bodegas.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* ORIGEN */}
            <div className="space-y-4 p-4 border rounded-lg bg-muted/20">
              <h3 className="font-semibold text-sm">Origen</h3>
              <div className="space-y-2">
                <Label>Bodega Origen</Label>
                <Select value={formData.bodega_origen_id} onValueChange={v => setFormData(f => ({ ...f, bodega_origen_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona bodega" /></SelectTrigger>
                  <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Producto Actual</Label>
                <Select value={formData.producto_origen_id} onValueChange={v => setFormData(f => ({ ...f, producto_origen_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona producto" /></SelectTrigger>
                  <SelectContent>{productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Lote Actual (Opcional)</Label>
                <Select value={formData.lote_origen_id} onValueChange={v => setFormData(f => ({ ...f, lote_origen_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona lote" /></SelectTrigger>
                  <SelectContent>
                     <SelectItem value="0">Sin Lote</SelectItem>
                     {lotesProduccion.map(l => <SelectItem key={l.id} value={l.id.toString()}>{l.codigo_lote}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* DESTINO */}
            <div className="space-y-4 p-4 border rounded-lg bg-muted/20">
              <h3 className="font-semibold text-sm">Destino (Transformado)</h3>
              <div className="space-y-2">
                <Label>Bodega Destino</Label>
                <Select value={formData.bodega_destino_id} onValueChange={v => setFormData(f => ({ ...f, bodega_destino_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona bodega" /></SelectTrigger>
                  <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Nuevo Producto (Código)</Label>
                <Select value={formData.producto_destino_id} onValueChange={v => setFormData(f => ({ ...f, producto_destino_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona nuevo producto" /></SelectTrigger>
                  <SelectContent>{productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Código de Nuevo Lote (Opcional)</Label>
                <Input 
                    value={formData.nuevo_lote_codigo} 
                    onChange={e => setFormData(f => ({ ...f, nuevo_lote_codigo: e.target.value }))} 
                    placeholder="Dejar vacío para mantener el mismo lote" 
                />
                <p className="text-xs text-muted-foreground">Si se deja vacío, se usará el lote origen.</p>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Cantidad a Transformar</Label>
            <Input type="number" value={formData.cantidad} onChange={e => setFormData(f => ({ ...f, cantidad: e.target.value }))} placeholder="0.00" />
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Procesando...' : 'Registrar Transformación'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};
