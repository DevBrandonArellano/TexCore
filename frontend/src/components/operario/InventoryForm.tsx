import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { useAuth } from '../../lib/auth';
import { Producto, Bodega } from '../../lib/types';
import { toast } from 'sonner';
import { PackagePlus } from 'lucide-react';
import apiClient from '../../lib/axios';
import { AxiosError } from 'axios';
import { Movimiento } from '../../lib/types';

interface InventoryFormProps {
  onMovementCreated: (movement: Movimiento) => void;
}

// Tipos de movimiento simplificados para el operario
const tiposMovimientoOperario = [
  { value: 'COMPRA', label: 'Entrada - Compra de Material' },
  { value: 'PRODUCCION', label: 'Entrada - Producción' },
  { value: 'CONSUMO', label: 'Salida - Consumo de Producción' },
  { value: 'VENTA', label: 'Salida - Venta' },
  { value: 'AJUSTE', label: 'Ajuste de Inventario' },
];

export function InventoryForm({ onMovementCreated }: InventoryFormProps) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    productoId: '',
    bodegaId: '',
    tipo: '' as 'ENTRADA' | 'SALIDA' | '',
    tipoMovimiento: '',
    cantidad: '',
    documentoRef: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      try {
        const [productosRes, bodegasRes] = await Promise.all([
          apiClient.get<Producto[]>('/productos/'),
          apiClient.get<Bodega[]>('/bodegas/'),
        ]);
        setProductos(productosRes.data);
        setBodegas(bodegasRes.data);
      } catch (error) {
        console.error('Error fetching form data:', error);
        toast.error('Error al cargar datos para el formulario.');
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, []);

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.productoId) newErrors.productoId = 'Selecciona un producto.';
    if (!formData.bodegaId) newErrors.bodegaId = 'Selecciona una bodega.';
    if (!formData.tipo) newErrors.tipo = 'Selecciona si es ENTRADA o SALIDA.';
    if (!formData.tipoMovimiento) newErrors.tipoMovimiento = 'Selecciona el motivo del movimiento.';
    if (!formData.cantidad || Number(formData.cantidad) <= 0) {
      newErrors.cantidad = 'Ingresa una cantidad válida mayor a 0.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos.');
      return;
    }

    const payload = {
      producto: formData.productoId,
      cantidad: formData.cantidad,
      tipo_movimiento: formData.tipoMovimiento,
      bodega_origen: formData.tipo === 'SALIDA' ? formData.bodegaId : null,
      bodega_destino: formData.tipo === 'ENTRADA' ? formData.bodegaId : null,
      documento_ref: formData.documentoRef,
    };

    try {
      const response = await apiClient.post<Movimiento>('/inventory/movimientos/', payload);
      toast.success('Movimiento registrado con éxito.');
      onMovementCreated(response.data);
      // Reset form
      setFormData({
        productoId: '',
        bodegaId: '',
        tipo: '',
        tipoMovimiento: '',
        cantidad: '',
        documentoRef: '',
      });
      setErrors({});
    } catch (error) {
      console.error('Error submitting inventory movement:', error);
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.data) {
        toast.error('Error al registrar', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>,
        });
      } else {
        toast.error('Error de red o servidor.');
      }
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <PackagePlus className="w-5 h-5" />
          <CardTitle>Registrar Movimiento</CardTitle>
        </div>
        <CardDescription>
          Registra una entrada o salida de inventario en una bodega.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <p>Cargando datos del formulario...</p> : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Producto */}
              <div className="space-y-1">
                <Label htmlFor="productoId">Producto</Label>
                <Select value={formData.productoId} onValueChange={(v) => setFormData(f => ({ ...f, productoId: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona un producto" /></SelectTrigger>
                  <SelectContent>
                    {productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)}
                  </SelectContent>
                </Select>
                {errors.productoId && <p className="text-sm text-destructive">{errors.productoId}</p>}
              </div>

              {/* Bodega */}
              <div className="space-y-1">
                <Label htmlFor="bodegaId">Bodega</Label>
                <Select value={formData.bodegaId} onValueChange={(v) => setFormData(f => ({ ...f, bodegaId: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger>
                  <SelectContent>
                    {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
                {errors.bodegaId && <p className="text-sm text-destructive">{errors.bodegaId}</p>}
              </div>

              {/* Tipo (Entrada/Salida) */}
              <div className="space-y-1">
                <Label htmlFor="tipo">Acción</Label>
                <Select value={formData.tipo} onValueChange={(v: 'ENTRADA' | 'SALIDA') => setFormData(f => ({ ...f, tipo: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona una acción" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ENTRADA">ENTRADA (Ingreso a Bodega)</SelectItem>
                    <SelectItem value="SALIDA">SALIDA (Egreso de Bodega)</SelectItem>
                  </SelectContent>
                </Select>
                {errors.tipo && <p className="text-sm text-destructive">{errors.tipo}</p>}
              </div>

              {/* Tipo de Movimiento */}
              <div className="space-y-1">
                <Label htmlFor="tipoMovimiento">Motivo del Movimiento</Label>
                <Select value={formData.tipoMovimiento} onValueChange={(v) => setFormData(f => ({ ...f, tipoMovimiento: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecciona un motivo" /></SelectTrigger>
                  <SelectContent>
                    {tiposMovimientoOperario.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
                {errors.tipoMovimiento && <p className="text-sm text-destructive">{errors.tipoMovimiento}</p>}
              </div>
            </div>

            {/* Cantidad */}
            <div className="space-y-1">
              <Label htmlFor="cantidad">Cantidad</Label>
              <Input id="cantidad" type="number" min="0.01" step="0.01" value={formData.cantidad} onChange={(e) => setFormData(f => ({ ...f, cantidad: e.target.value }))} />
              {errors.cantidad && <p className="text-sm text-destructive">{errors.cantidad}</p>}
            </div>

            {/* Documento de Referencia */}
            <div className="space-y-1">
              <Label htmlFor="documentoRef">Documento de Referencia (Opcional)</Label>
              <Textarea id="documentoRef" value={formData.documentoRef} onChange={(e) => setFormData(f => ({ ...f, documentoRef: e.target.value }))} />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setFormData({ productoId: '', bodegaId: '', tipo: '', tipoMovimiento: '', cantidad: '', documentoRef: '' })}>Limpiar</Button>
              <Button type="submit">Registrar Movimiento</Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
