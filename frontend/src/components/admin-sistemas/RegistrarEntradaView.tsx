import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ProductSelect } from '../ui/product-select';
import { SearchableSelect } from '../ui/searchable-select';
import { toast } from 'sonner';
import type { Producto, Bodega, Proveedor } from '../../lib/types';
import { PAISES } from '../../lib/paises';
import { inventarioApi } from '../../lib/api/inventarioApi';
import { formatApiError } from '../../lib/errorUtils';

const CALIDAD_OPCIONES = ['Primera', 'Segunda', 'Saldo / Retazo'];

interface RegistrarEntradaViewProps {
  productos: Producto[];
  bodegas: Bodega[];
  proveedores: Proveedor[];
  /** Avisa que hubo una recepción (opcional: la pestaña de stock pide los datos al montarse). */
  onDataRefresh?: () => void;
}

const hoy = () => new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD en hora local

const formularioVacio = () => ({
  proveedor: '', producto: '', bodega_recepcion: '', lote_proveedor: '', cantidad_kg: '',
  costo_unitario: '', fecha_recepcion: hoy(), numero_documento_entrada: '', pais: '', calidad: '',
});

/**
 * Recepción de materia prima F0-001: única vía para registrar una compra.
 * Crea el lote de MP (proveedor, lote del proveedor, costo y certificado), suma
 * el stock y registra el movimiento COMPRA en una sola transacción del servidor.
 */
function RegistrarEntradaViewImpl({ productos, bodegas, proveedores, onDataRefresh }: RegistrarEntradaViewProps) {
  const [form, setForm] = useState(formularioVacio);
  const [certificado, setCertificado] = useState<File | null>(null);
  const [inputArchivoKey, setInputArchivoKey] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const campo = (clave: keyof ReturnType<typeof formularioVacio>) => (valor: string) =>
    setForm((f) => ({ ...f, [clave]: valor }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const obligatorios = [form.proveedor, form.producto, form.bodega_recepcion, form.lote_proveedor.trim(),
      form.cantidad_kg, form.costo_unitario, form.fecha_recepcion];
    if (obligatorios.some((v) => !v)) {
      toast.error('Proveedor, producto, bodega, lote del proveedor, cantidad, costo y fecha son requeridos.');
      return;
    }
    setIsSubmitting(true);
    try {
      const lote = await inventarioApi.registrarEntradaMateriaPrima({
        proveedor: Number(form.proveedor),
        producto: Number(form.producto),
        bodega_recepcion: Number(form.bodega_recepcion),
        lote_proveedor: form.lote_proveedor.trim(),
        cantidad_kg: form.cantidad_kg,
        costo_unitario: form.costo_unitario,
        fecha_recepcion: form.fecha_recepcion,
        numero_documento_entrada: form.numero_documento_entrada.trim(),
        pais: form.pais,
        calidad: form.calidad,
        certificado_calidad: certificado,
      });
      toast.success(`Recepción registrada: lote ${lote.lote_proveedor}.`);
      onDataRefresh?.();
      setForm(formularioVacio());
      setCertificado(null);
      setInputArchivoKey((k) => k + 1);
    } catch (error) {
      const formatted = formatApiError(error);
      toast.error(formatted.message, { description: formatted.note });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recepción de Materia Prima (F0-001)</CardTitle>
        <CardDescription>
          Registra la llegada de material del proveedor. Cada recepción crea un lote trazable con su costo
          y certificado, y suma el stock en la bodega de recepción.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="recepcion-proveedor">Proveedor</Label>
              <SearchableSelect
                id="recepcion-proveedor"
                items={proveedores.map(p => ({ value: p.id.toString(), label: p.nombre }))}
                value={form.proveedor}
                onValueChange={campo('proveedor')}
                placeholder="Selecciona un proveedor"
                searchPlaceholder="Buscar proveedor..."
                emptyLabel="No se encontraron proveedores"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-producto">Producto</Label>
              <ProductSelect productos={productos} value={form.producto} onValueChange={campo('producto')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-bodega">Bodega de recepción</Label>
              <Select value={form.bodega_recepcion} onValueChange={campo('bodega_recepcion')}>
                <SelectTrigger id="recepcion-bodega"><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger>
                <SelectContent>
                  {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-lote">Lote del proveedor</Label>
              <Input id="recepcion-lote" value={form.lote_proveedor}
                onChange={e => campo('lote_proveedor')(e.target.value)} placeholder="Ej: HS-2026-0915" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-cantidad">Cantidad (kg)</Label>
              <Input id="recepcion-cantidad" type="number" step="0.001" min="0.001" value={form.cantidad_kg}
                onChange={e => campo('cantidad_kg')(e.target.value)} placeholder="0.000" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-costo">Costo unitario</Label>
              <Input id="recepcion-costo" type="number" step="0.001" min="0" value={form.costo_unitario}
                onChange={e => campo('costo_unitario')(e.target.value)} placeholder="Costo por kg" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-fecha">Fecha de recepción</Label>
              <Input id="recepcion-fecha" type="date" value={form.fecha_recepcion}
                onChange={e => campo('fecha_recepcion')(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-documento">N.º de documento</Label>
              <Input id="recepcion-documento" value={form.numero_documento_entrada}
                onChange={e => campo('numero_documento_entrada')(e.target.value)} placeholder="Ej: Factura #123" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-pais">País</Label>
              <SearchableSelect
                id="recepcion-pais"
                options={PAISES}
                value={form.pais}
                onValueChange={campo('pais')}
                placeholder="Selecciona un país"
                searchPlaceholder="Buscar país..."
                emptyLabel="No se encontraron países"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recepcion-calidad">Calidad</Label>
              <Select value={form.calidad || undefined} onValueChange={campo('calidad')}>
                <SelectTrigger id="recepcion-calidad"><SelectValue placeholder="Selecciona una calidad" /></SelectTrigger>
                <SelectContent>
                  {CALIDAD_OPCIONES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="recepcion-certificado">Certificado de calidad</Label>
              <Input key={inputArchivoKey} id="recepcion-certificado" type="file" accept=".pdf,image/*"
                onChange={e => setCertificado(e.target.files?.[0] ?? null)} />
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Registrando...' : 'Registrar recepción'}</Button>
        </form>
      </CardContent>
    </Card>
  );
}

export const RegistrarEntradaView = React.memo(RegistrarEntradaViewImpl);
