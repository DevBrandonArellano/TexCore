import React, { useMemo } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { ShoppingBag, Package, AlertCircle, CheckCircle, Trash2 } from 'lucide-react';
import type { Cliente, Producto } from '../../lib/types';
import { calculateItemsTotal, normalizarInputNumerico } from './pedidoUtils';

interface OrderItem {
  producto: string;
  cantidad: number;
  piezas: number;
  peso: number;
  precio_unitario: number;
  incluye_iva?: boolean;
}

interface OrderForm {
  cliente: string;
  guia_remision: string;
  esta_pagado: boolean;
  aplica_retencion: boolean;
  valor_retencion: string;
}

interface NewItemForm {
  producto: string;
  cantidad: number;
  piezas: number;
  peso: string;
  precio_unitario: string;
  incluye_iva: boolean;
}

interface NuevaVentaDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  clientes: Cliente[];
  productos: Producto[];
  orderForm: OrderForm;
  setOrderForm: React.Dispatch<React.SetStateAction<OrderForm>>;
  orderItems: OrderItem[];
  newItem: NewItemForm;
  setNewItem: React.Dispatch<React.SetStateAction<NewItemForm>>;
  addOrderItem: () => void;
  removeOrderItem: (index: number) => void;
  onSubmit: () => void;
}

function NuevaVentaDialogImpl({
  isOpen,
  onOpenChange,
  clientes,
  productos,
  orderForm,
  setOrderForm,
  orderItems,
  newItem,
  setNewItem,
  addOrderItem,
  removeOrderItem,
  onSubmit,
}: NuevaVentaDialogProps) {
  const selectedClientDetails = useMemo(() => {
    if (!orderForm.cliente || !Array.isArray(clientes)) return null;
    return clientes.find(c => c.id.toString() === orderForm.cliente);
  }, [orderForm.cliente, clientes]);

  const isValidatingCash = useMemo(() => {
    if (!selectedClientDetails) return false;
    // Si es de contado (0 dias) y el pedido NO esta marcado como pagado, requerirá advertencia
    return selectedClientDetails.plazo_credito_dias === 0 && !orderForm.esta_pagado;
  }, [selectedClientDetails, orderForm.esta_pagado]);

  const orderTotal = calculateItemsTotal(orderItems);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="gap-2 bg-green-600 hover:bg-green-700">
          <ShoppingBag className="w-4 h-4" />
          Venta Nueva
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Registrar Nueva Venta</DialogTitle>
          <DialogDescription>Genera un nuevo pedido para un cliente. El sistema validará el límite de crédito.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-6 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label>Cliente <span className="text-destructive">*</span></Label>
              <Select value={orderForm.cliente} onValueChange={v => setOrderForm({ ...orderForm, cliente: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona un cliente" />
                </SelectTrigger>
                <SelectContent>
                  {(Array.isArray(clientes) ? clientes : []).map(c => (
                    <SelectItem key={c.id} value={c.id.toString()}>
                      {c.nombre_razon_social} (Límite: ${c.limite_credito})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>Guía de Remisión / Factura</Label>
              <Input value={orderForm.guia_remision} onChange={e => setOrderForm({ ...orderForm, guia_remision: e.target.value })} placeholder="Ej: GR-001" />
            </div>
          </div>

          {selectedClientDetails && (
            <div className={`p-3 rounded-lg border flex gap-3 ${parseFloat(selectedClientDetails.cartera_vencida?.toString() || '0') > 0 ? 'bg-red-50 border-red-200' : 'bg-slate-50'}`}>
              <div className="text-muted-foreground flex items-center justify-center">
                {parseFloat(selectedClientDetails.cartera_vencida?.toString() || '0') > 0 ? <AlertCircle className="w-6 h-6 text-destructive" /> : <CheckCircle className="w-6 h-6 text-green-600" />}
              </div>
              <div className="flex flex-col">
                <span className="font-semibold text-sm">
                  {parseFloat(selectedClientDetails.cartera_vencida?.toString() || '0') > 0
                    ? 'Cliente con Cartera Vencida'
                    : `Plazo de Crédito Autorizado: ${selectedClientDetails.plazo_credito_dias === 0 ? 'Contado' : selectedClientDetails.plazo_credito_dias + ' Días'}`}
                </span>
                <span className="text-xs text-muted-foreground">
                  {parseFloat(selectedClientDetails.cartera_vencida?.toString() || '0') > 0
                    ? 'Atención: Según políticas, este cliente no puede generar nuevos pedidos a crédito hasta que regularice su deuda pendiente.'
                    : `El vencimiento se calculará sumando los días de crédito a la fecha de hoy.`}
                </span>
              </div>
            </div>
          )}

          <div className="border rounded-lg p-4 space-y-4 bg-slate-50/50">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Package className="w-4 h-4" /> Añadir Productos
            </h3>
            <div className="grid grid-cols-12 gap-2 items-end">
              <div className="col-span-5 grid gap-1.5">
                <Label className="text-[10px] uppercase text-muted-foreground">Producto</Label>
                <Select value={newItem.producto} onValueChange={v => {
                  const p = productos.find(prod => prod.id.toString() === v);
                  setNewItem({ ...newItem, producto: v, precio_unitario: (p?.precio_base || 0).toString() });
                }}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Producto..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(Array.isArray(productos) ? productos : []).map(p => (
                      <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="flex flex-col gap-1 mt-1">
                  <div className="flex items-center space-x-2 px-1">
                    <Switch id="iva-mode" className="scale-75 shadow-sm data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-slate-400" checked={newItem.incluye_iva} onCheckedChange={(v) => setNewItem({ ...newItem, incluye_iva: v })} />
                    <Label htmlFor="iva-mode" className="text-[10px]">Aplicar +15% IVA</Label>
                  </div>
                </div>
              </div>
              <div className="col-span-2 grid gap-1.5 pb-6">
                <Label className="text-[10px] uppercase text-muted-foreground">Peso / Metros (kg / Mts)</Label>
                <Input
                  type="text"
                  className="h-8 text-xs font-mono"
                  value={newItem.peso}
                  onChange={e => setNewItem({ ...newItem, peso: normalizarInputNumerico(e.target.value) })}
                  onFocus={(e) => e.target.select()}
                />
              </div>
              <div className="col-span-3 grid gap-1.5 pb-6">
                <Label className="text-[10px] uppercase text-muted-foreground">Precio Unit ($)</Label>
                <Input
                  type="text"
                  className="h-8 text-xs font-mono"
                  value={newItem.precio_unitario}
                  onChange={e => setNewItem({ ...newItem, precio_unitario: normalizarInputNumerico(e.target.value) })}
                  onFocus={(e) => e.target.select()}
                />
              </div>
              <div className="col-span-2 pb-6">
                <Button size="sm" variant="outline" className="w-full h-8" onClick={addOrderItem}>Añadir</Button>
              </div>
            </div>

            {orderItems.length > 0 && (
              <div className="border rounded bg-white overflow-hidden">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow className="h-8">
                      <TableHead className="py-0 text-[10px]">Prod</TableHead>
                      <TableHead className="py-0 text-[10px] text-right">Peso</TableHead>
                      <TableHead className="py-0 text-[10px] text-right">Precio</TableHead>
                      <TableHead className="py-0 text-[10px] text-center">IVA</TableHead>
                      <TableHead className="py-0 text-[10px] text-right">Subtotal</TableHead>
                      <TableHead className="py-0 text-[10px] text-right"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orderItems.map((item, idx) => {
                      const subtotal = item.peso * item.precio_unitario;
                      const iva = item.incluye_iva ? subtotal * 0.15 : 0;
                      const total_item = subtotal + iva;

                      return (
                        <TableRow key={idx} className="h-8">
                          <TableCell className="py-1 text-xs">{productos.find(p => p.id.toString() === item.producto)?.descripcion}</TableCell>
                          <TableCell className="py-1 text-xs text-right font-mono">{item.peso.toFixed(3)}</TableCell>
                          <TableCell className="py-1 text-xs text-right font-mono">${item.precio_unitario.toFixed(3)}</TableCell>
                          <TableCell className="py-1 text-xs text-center">
                            {item.incluye_iva ? <Badge variant="secondary" className="text-[9px] h-4 py-0">+15%</Badge> : '-'}
                          </TableCell>
                          <TableCell className="py-1 text-xs text-right font-mono font-bold">
                            ${total_item.toFixed(3)}
                          </TableCell>
                          <TableCell className="py-1 text-right">
                            <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => removeOrderItem(idx)}>
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    <TableRow className="bg-primary/5 font-bold">
                      <TableCell colSpan={4} className="text-right py-2">TOTAL PEDIDO (Incl. Impuestos):</TableCell>
                      <TableCell className="text-right py-2 text-primary">${orderTotal.toFixed(3)}</TableCell>
                      <TableCell></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            )}
          </div>

          {orderItems.length > 0 && (
            <div className="flex flex-col gap-3 p-3 border rounded-lg bg-orange-50/30">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>¿El cliente te emite retención?</Label>
                  <p className="text-xs text-muted-foreground">Activa esto para ingresar el valor de la retención a descontar.</p>
                </div>
                <Switch className="scale-75 shadow-sm data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-slate-400" checked={orderForm.aplica_retencion} onCheckedChange={v => {
                  setOrderForm({ ...orderForm, aplica_retencion: v, valor_retencion: v ? orderForm.valor_retencion : '0' });
                }} />
              </div>
              {orderForm.aplica_retencion && (
                <div className="flex items-center gap-3 pt-2 mt-2 border-t">
                  <Label className="flex-1 whitespace-nowrap">Valor de Retención ($)</Label>
                  <Input
                    type="text"
                    className="w-32 font-mono text-right"
                    value={orderForm.valor_retencion}
                    onChange={e => {
                      const valStr = e.target.value.replace(',', '.');
                      if (valStr === '' || /^\d+(\.\d*)?$/.test(valStr)) {
                        const numVal = parseFloat(valStr) || 0;
                        if (numVal <= orderTotal) {
                          setOrderForm({ ...orderForm, valor_retencion: valStr });
                        }
                      }
                    }}
                    onBlur={e => {
                      if (e.target.value === '' || e.target.value === '.' || e.target.value === '0') {
                        setOrderForm({ ...orderForm, valor_retencion: '0' });
                      }
                    }}
                    onFocus={(e) => e.target.select()}
                  />
                </div>
              )}
              {orderForm.aplica_retencion && (parseFloat(orderForm.valor_retencion) > 0) && (
                <div className="flex justify-between items-center text-sm font-bold bg-primary px-3 py-2 text-primary-foreground rounded-md mt-2">
                  <span>TOTAL A COBRAR (Menos Retención):</span>
                  <span>${(orderTotal - parseFloat(orderForm.valor_retencion)).toFixed(3)}</span>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div className="space-y-0.5">
              <Label>¿El cliente pagó en caja?</Label>
              <p className="text-xs text-muted-foreground">Marca si ya recibiste el dinero, es requisito para despachar al contado.</p>
            </div>
            <Switch className="scale-75 shadow-sm data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-slate-400" checked={orderForm.esta_pagado} onCheckedChange={v => setOrderForm({ ...orderForm, esta_pagado: v })} />
          </div>

          {isValidatingCash && (
            <div className="bg-orange-50 text-orange-800 p-3 rounded-md text-xs border border-orange-200">
              <AlertCircle className="w-4 h-4 inline mr-1 mb-0.5" /> <strong>Atención de Seguridad:</strong> Este cliente es de contado (0 días crédito). Como este pedido no ha sido pagado, <strong>recuerda</strong> que no se le permitirá generar un segundo pedido hasta que esta factura sea cancelada.
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button className="bg-primary" onClick={onSubmit}>Finalizar y Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const NuevaVentaDialog = React.memo(NuevaVentaDialogImpl);
