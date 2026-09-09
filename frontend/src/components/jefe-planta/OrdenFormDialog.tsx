import React from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../ui/dialog';
import { Factory } from 'lucide-react';
import type { OrdenProduccion, Producto, Bodega, Area } from '../../lib/types';
import type { OrdenFormData } from './ordenUtils';

interface OrdenFormDialogProps {
  isOpen: boolean;
  onDialogOpenChange: (open: boolean) => void;
  onCancel: () => void;
  editingOrden: OrdenProduccion | null;
  formData: OrdenFormData;
  setFormData: React.Dispatch<React.SetStateAction<OrdenFormData>>;
  errors: Record<string, string>;
  productos: Producto[];
  bodegas: Bodega[];
  areas: Area[];
  loading: boolean;
  isSubmitting: boolean;
  onSubmit: () => void;
}

function OrdenFormDialogImpl({
  isOpen,
  onDialogOpenChange,
  onCancel,
  editingOrden,
  formData,
  setFormData,
  errors,
  productos,
  bodegas,
  areas,
  loading,
  isSubmitting,
  onSubmit,
}: OrdenFormDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onDialogOpenChange}>
      <DialogTrigger asChild>
        <Button disabled={loading}>
          <Factory className="w-4 h-4 mr-2" />
          {loading ? 'Cargando Catálogos...' : 'Nueva Orden'}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editingOrden ? 'Editar Orden de Producción' : 'Nueva Orden de Producción'}</DialogTitle>
          <DialogDescription>
            {editingOrden ? 'Modifica los datos de la orden.' : 'Completa el formulario para crear una nueva orden de producción.'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="codigo">Código <span className="text-destructive">*</span></Label>
            <Input id="codigo" value={formData.codigo} onChange={e => setFormData({ ...formData, codigo: e.target.value })} className={errors.codigo ? 'border-destructive' : ''} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="peso_neto_requerido">Peso Neto Requerido (Kg) <span className="text-destructive">*</span></Label>
            <Input id="peso_neto_requerido" type="number" value={formData.peso_neto_requerido} onChange={e => setFormData({ ...formData, peso_neto_requerido: e.target.value })} className={errors.peso_neto_requerido ? 'border-destructive' : ''} />
          </div>
          {editingOrden && (
            <div className="space-y-2">
              <Label htmlFor="producto_entrada">Producto Entrada <span className="text-destructive">*</span></Label>
              <Select value={formData.producto_entrada} onValueChange={v => setFormData({ ...formData, producto_entrada: v })}>
                <SelectTrigger className={errors.producto_entrada ? 'border-destructive' : ''}>
                  <SelectValue placeholder={productos.length ? "Selecciona producto de entrada" : "No hay productos disponibles"} />
                </SelectTrigger>
                <SelectContent>
                  {productos.length > 0 ? (
                    productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)
                  ) : (
                    <div className="py-2 px-4 text-sm text-muted-foreground">Sin productos</div>
                  )}
                </SelectContent>
              </Select>
              {errors.producto_entrada && <p className="text-sm text-destructive">{errors.producto_entrada}</p>}
            </div>
          )}
          {editingOrden && (
            <div className="space-y-2">
              <Label htmlFor="bodega_entrada">Bodega Entrada</Label>
              <Select value={formData.bodega_entrada} onValueChange={v => setFormData({ ...formData, bodega_entrada: v })}>
                <SelectTrigger>
                  <SelectValue placeholder={bodegas.length ? "Selecciona bodega de entrada" : "No hay bodegas disponibles"} />
                </SelectTrigger>
                <SelectContent>
                  {bodegas.length > 0 ? (
                    bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)
                  ) : (
                    <div className="py-2 px-4 text-sm text-muted-foreground">Sin bodegas</div>
                  )}
                </SelectContent>
              </Select>
            </div>
          )}
          {editingOrden && (
            <div className="space-y-2">
              <Label htmlFor="producto_salida">Producto Salida <span className="text-destructive">*</span></Label>
              <Select value={formData.producto_salida} onValueChange={v => setFormData({ ...formData, producto_salida: v })}>
                <SelectTrigger className={errors.producto_salida ? 'border-destructive' : ''}>
                  <SelectValue placeholder={productos.length ? "Selecciona producto de salida" : "No hay productos disponibles"} />
                </SelectTrigger>
                <SelectContent>
                  {productos.length > 0 ? (
                    productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)
                  ) : (
                    <div className="py-2 px-4 text-sm text-muted-foreground">Sin productos</div>
                  )}
                </SelectContent>
              </Select>
              {errors.producto_salida && <p className="text-sm text-destructive">{errors.producto_salida}</p>}
            </div>
          )}
          {editingOrden && (
            <div className="space-y-2">
              <Label htmlFor="bodega_salida">Bodega Salida</Label>
              <Select value={formData.bodega_salida} onValueChange={v => setFormData({ ...formData, bodega_salida: v })}>
                <SelectTrigger>
                  <SelectValue placeholder={bodegas.length ? "Selecciona bodega de salida" : "No hay bodegas disponibles"} />
                </SelectTrigger>
                <SelectContent>
                  {bodegas.length > 0 ? (
                    bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)
                  ) : (
                    <div className="py-2 px-4 text-sm text-muted-foreground">Sin bodegas</div>
                  )}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="area">Área Responsable <span className="text-destructive">*</span></Label>
            <Select value={formData.area} onValueChange={v => setFormData({ ...formData, area: v })}>
              <SelectTrigger><SelectValue placeholder={areas.length ? "Selecciona el área de destino" : "No hay áreas registradas"} /></SelectTrigger>
              <SelectContent>
                {areas.length > 0 ? (
                  areas.map(a => <SelectItem key={a.id} value={a.id.toString()}>{a.nombre}</SelectItem>)
                ) : (
                  <div className="py-2 px-4 text-sm text-muted-foreground">Sin áreas disponibles</div>
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="prioridad">Prioridad <span className="text-destructive">*</span></Label>
            <Select value={formData.prioridad} onValueChange={v => setFormData({ ...formData, prioridad: v })}>
              <SelectTrigger><SelectValue placeholder="Selecciona una prioridad" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="baja">Baja</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="alta">Alta</SelectItem>
                <SelectItem value="urgente">Urgente</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="fecha_inicio_planificada">Fecha Inicio</Label>
            <Input id="fecha_inicio_planificada" type="date" value={formData.fecha_inicio_planificada} onChange={e => setFormData({ ...formData, fecha_inicio_planificada: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="fecha_fin_planificada">Fecha Fin</Label>
            <Input id="fecha_fin_planificada" type="date" value={formData.fecha_fin_planificada} onChange={e => setFormData({ ...formData, fecha_fin_planificada: e.target.value })} />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="observaciones">Observaciones</Label>
            <Input id="observaciones" value={formData.observaciones} onChange={e => setFormData({ ...formData, observaciones: e.target.value })} placeholder="Instrucciones especiales..." />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>Cancelar</Button>
          <Button onClick={onSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Guardando...' : (editingOrden ? 'Actualizar' : 'Crear')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const OrdenFormDialog = React.memo(OrdenFormDialogImpl);
