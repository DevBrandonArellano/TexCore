import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ProductSelect } from '../ui/product-select';
import { ShieldCheck } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import type { Producto, Bodega, Proveedor } from '../../lib/types';

interface RegistrarEntradaViewProps {
  productos: Producto[];
  bodegas: Bodega[];
  proveedores: Proveedor[];
  onDataRefresh: () => void;
}

function RegistrarEntradaViewImpl({ productos, bodegas, proveedores, onDataRefresh }: RegistrarEntradaViewProps) {
  const [formData, setFormData] = useState({ producto_id: '', bodega_destino_id: '', cantidad: '', documento_ref: '', lote_codigo: '', proveedor_id: '', pais: '', calidad: '', _justificacion_auditoria: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.producto_id || !formData.bodega_destino_id || !formData.cantidad || !formData._justificacion_auditoria) {
      toast.error("Producto, Bodega, Cantidad y Justificación son requeridos.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.post('/inventory/movimientos/', {
        tipo_movimiento: 'COMPRA',
        producto: parseInt(formData.producto_id),
        bodega_destino: parseInt(formData.bodega_destino_id),
        cantidad: parseFloat(formData.cantidad),
        lote_codigo: formData.lote_codigo,
        documento_ref: formData.documento_ref,
        proveedor: formData.proveedor_id ? parseInt(formData.proveedor_id) : null,
        pais: formData.pais,
        calidad: formData.calidad,
        _justificacion_auditoria: formData._justificacion_auditoria,
      });
      toast.success("Entrada de materia prima registrada con éxito.");
      onDataRefresh();
      setFormData({ producto_id: '', bodega_destino_id: '', cantidad: '', documento_ref: '', lote_codigo: '', proveedor_id: '', pais: '', calidad: '', _justificacion_auditoria: '' });
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || "Ocurrió un error al registrar la entrada.";
      toast.error("Error", { description: errorMsg });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Registrar Entrada de Materia Prima</CardTitle>
        <CardDescription>Usa este formulario para registrar la compra o llegada de nuevos materiales.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="entrada-producto">Producto</Label>
              <ProductSelect productos={productos} value={formData.producto_id} onValueChange={v => setFormData(f => ({ ...f, producto_id: v }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-bodega">Bodega de Destino</Label>
              <Select value={formData.bodega_destino_id} onValueChange={v => setFormData(f => ({ ...f, bodega_destino_id: v }))}>
                <SelectTrigger id="entrada-bodega"><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger>
                <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-lote">Código de Lote (Opcional)</Label>
              <Input id="entrada-lote" value={formData.lote_codigo} onChange={e => setFormData(f => ({ ...f, lote_codigo: e.target.value }))} placeholder="Ej: LOTE-MP-2026-001" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-cantidad">Cantidad</Label>
              <Input id="entrada-cantidad" type="number" step="any" value={formData.cantidad} onChange={e => setFormData(f => ({ ...f, cantidad: e.target.value }))} placeholder="0.00" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-proveedor">Proveedor</Label>
              <Select value={formData.proveedor_id} onValueChange={v => setFormData(f => ({ ...f, proveedor_id: v }))}>
                <SelectTrigger id="entrada-proveedor"><SelectValue placeholder="Selecciona" /></SelectTrigger>
                <SelectContent>{proveedores.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.nombre}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-pais">País</Label>
              <Input id="entrada-pais" value={formData.pais} onChange={e => setFormData(f => ({ ...f, pais: e.target.value }))} placeholder="Ej: Ecuador" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-calidad">Calidad</Label>
              <Input id="entrada-calidad" value={formData.calidad} onChange={e => setFormData(f => ({ ...f, calidad: e.target.value }))} placeholder="Ej: Primera" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-ref">Referencia</Label>
              <Input id="entrada-ref" value={formData.documento_ref} onChange={e => setFormData(f => ({ ...f, documento_ref: e.target.value }))} placeholder="Ej: Factura #123" />
            </div>
            <div className="space-y-2 md:col-span-2 p-3 bg-primary/5 rounded-lg border border-primary/20">
              <Label htmlFor="justificacion-entrada" className="flex items-center gap-2 font-bold text-primary">
                <ShieldCheck className="w-4 h-4" /> Justificación de la Entrada <span className="text-destructive">*</span>
              </Label>
              <Input id="justificacion-entrada" value={formData._justificacion_auditoria} onChange={e => setFormData(f => ({ ...f, _justificacion_auditoria: e.target.value }))} placeholder="Ej: Reposición mensual..." className="bg-background" />
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Registrando...' : 'Registrar Entrada'}</Button>
        </form>
      </CardContent>
    </Card>
  );
}

export const RegistrarEntradaView = React.memo(RegistrarEntradaViewImpl);
