import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Users, ShoppingBag, DollarSign, Calendar, Search, Plus, CreditCard, CheckCircle, AlertCircle, TrendingUp, Package, Trash2, Printer, History } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Cliente, PedidoVenta, DetallePedido, Producto } from '../../lib/types';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface OrderItem {
  producto: string;
  cantidad: number;
  piezas: number;
  peso: number;
  precio_unitario: number;
}

export function VendedorDashboard() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [orderSearchTerm, setOrderSearchTerm] = useState('');

  // Dialog States
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isOrderDialogOpen, setIsOrderDialogOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Edit/Select States
  const [editingCliente, setEditingCliente] = useState<Cliente | null>(null);
  const [selectedCliente, setSelectedCliente] = useState<Cliente | null>(null);

  // Form States - Cliente
  const [formData, setFormData] = useState({
    ruc_cedula: '',
    nombre_razon_social: '',
    direccion_envio: '',
    nivel_precio: 'normal' as 'normal' | 'mayorista',
    tiene_beneficio: false,
    saldo_pendiente: '0.00',
    limite_credito: '0.00'
  });

  // Form States - Pedido
  const [orderForm, setOrderForm] = useState({
    cliente: '',
    guia_remision: '',
    esta_pagado: false
  });
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [newItem, setNewItem] = useState<OrderItem>({
    producto: '',
    cantidad: 1,
    piezas: 1,
    peso: 0,
    precio_unitario: 0
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [clientesRes, pedidosRes, productosRes] = await Promise.all([
        apiClient.get('/clientes/'),
        apiClient.get('/pedidos-venta/', { params: { limit: 100 } }),
        apiClient.get('/productos/')
      ]);
      setClientes(clientesRes.data);
      setPedidos(pedidosRes.data);
      setProductos(productosRes.data);
    } catch (error: any) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar la información del vendedor');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // --- Cliente Handlers ---
  const handleCreateOrUpdateCliente = async () => {
    try {
      const dataToSend = {
        ...formData,
        limite_credito: parseFloat(formData.limite_credito)
      };
      // @ts-ignore
      delete dataToSend.saldo_pendiente;

      if (editingCliente) {
        await apiClient.put(`/clientes/${editingCliente.id}/`, dataToSend);
        toast.success('Cliente actualizado correctamente');
      } else {
        await apiClient.post('/clientes/', dataToSend);
        toast.success('Cliente registrado correctamente');
      }
      setIsDialogOpen(false);
      setEditingCliente(null);
      fetchData();
    } catch (error: any) {
      console.error('Error saving cliente:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar el cliente');
    }
  };

  const openEditDialog = (cliente: Cliente) => {
    setEditingCliente(cliente);
    setFormData({
      ruc_cedula: cliente.ruc_cedula,
      nombre_razon_social: cliente.nombre_razon_social,
      direccion_envio: cliente.direccion_envio,
      nivel_precio: cliente.nivel_precio,
      tiene_beneficio: cliente.tiene_beneficio,
      saldo_pendiente: cliente.saldo_pendiente.toString(),
      limite_credito: cliente.limite_credito.toString()
    });
    setIsDialogOpen(true);
  };

  // --- Pedido Handlers ---
  const addOrderItem = () => {
    if (!newItem.producto || newItem.peso <= 0 || newItem.precio_unitario <= 0) {
      toast.error('Por favor completa todos los campos del item');
      return;
    }
    setOrderItems([...orderItems, newItem]);
    setNewItem({
      producto: '',
      cantidad: 1,
      piezas: 1,
      peso: 0,
      precio_unitario: 0
    });
  };

  const removeOrderItem = (index: number) => {
    setOrderItems(orderItems.filter((_, i) => i !== index));
  };

  const calculateOrderTotal = () => {
    return orderItems.reduce((acc, item) => acc + (item.peso * item.precio_unitario), 0);
  };

  const handleCreateOrder = async () => {
    if (!orderForm.cliente || orderItems.length === 0) {
      toast.error('Por favor selecciona un cliente y añade al menos un producto');
      return;
    }

    try {
      const orderData = {
        ...orderForm,
        cliente: parseInt(orderForm.cliente),
        detalles: orderItems
      };

      await apiClient.post('/pedidos-venta/', orderData);
      toast.success('Pedido creado correctamente');
      setIsOrderDialogOpen(false);
      setOrderItems([]);
      setOrderForm({ cliente: '', guia_remision: '', esta_pagado: false });
      fetchData();
    } catch (error: any) {
      console.error('Error saving order:', error);
      const errorMsg = error.response?.data?.cliente || error.response?.data?.detail || 'Error al guardar el pedido';
      toast.error(errorMsg);
    }
  };

  // --- Print Handler ---
  const handlePrintOrder = (pedido: PedidoVenta) => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const total = pedido.detalles?.reduce((sum: number, det: any) => sum + (det.peso * det.precio_unitario), 0) || 0;
    const itemsHtml = pedido.detalles?.map((det: any) => `
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #eee;">${productos.find(p => p.id === det.producto)?.descripcion || 'Producto'}</td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">${det.piezas}</td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">${det.peso.toFixed(2)} kg</td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">$${det.precio_unitario.toFixed(2)}</td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">$${(det.peso * det.precio_unitario).toFixed(2)}</td>
      </tr>
    `).join('') || '';

    printWindow.document.write(`
      <html>
        <head>
          <title>Nota de Venta - ${pedido.guia_remision || pedido.id}</title>
          <style>
            body { font-family: 'Inter', sans-serif; color: #333; line-height: 1.5; padding: 40px; }
            .header { display: flex; justify-content: space-between; border-bottom: 2px solid #000; pb: 20px; mb: 20px; }
            .company { font-size: 24px; font-bold; }
            .order-info { text-align: right; }
            .section { margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; }
            th { background: #f8f9fa; padding: 10px; text-align: left; font-size: 12px; text-transform: uppercase; }
            .total-row { font-size: 18px; font-weight: bold; border-top: 2px solid #000; }
            @media print { .no-print { display: none; } }
          </style>
        </head>
        <body>
          <div class="header" style="margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1a1a1a; padding-bottom: 20px;">
            <div>
              <div style="font-size: 28px; font-weight: 800; color: #1a1a1a;">TEXCORE INDUSTRIAL</div>
              <div style="font-size: 12px; color: #666; margin-top: 4px;">Soluciones Textiles de Alta Calidad</div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 18px; font-weight: 700;">NOTA DE VENTA</div>
              <div style="font-size: 14px; color: #e11d48; font-weight: 600;">${pedido.guia_remision || 'OD-' + pedido.id}</div>
              <div style="font-size: 12px; color: #666;">Fecha: ${format(new Date(pedido.fecha_pedido), 'dd/MM/yyyy HH:mm')}</div>
            </div>
          </div>

          <div style="display: grid; grid-template-cols: 1fr 1fr; gap: 40px; margin-bottom: 40px;">
            <div style="background: #fdfdfd; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
              <div style="font-size: 10px; font-weight: 800; color: #999; text-transform: uppercase; margin-bottom: 8px;">Cliente</div>
              <div style="font-size: 16px; font-weight: 700;">${pedido.cliente_nombre || clientes.find(c => c.id === pedido.cliente)?.nombre_razon_social}</div>
              <div style="font-size: 13px; color: #444; margin-top: 4px;">RUC/CED: ${clientes.find(c => c.id === pedido.cliente)?.ruc_cedula}</div>
              <div style="font-size: 13px; color: #444;">Dirección: ${clientes.find(c => c.id === pedido.cliente)?.direccion_envio}</div>
            </div>
            <div style="text-align: right; padding: 20px;">
                <div style="font-size: 10px; font-weight: 800; color: #999; text-transform: uppercase; margin-bottom: 8px;">Estado de Pago</div>
                <div style="font-size: 14px; font-weight: 700; color: ${pedido.esta_pagado ? '#16a34a' : '#e11d48'};">
                    ${pedido.esta_pagado ? 'PAGADO - GRACIAS' : 'VENTA A CRÉDITO - PENDIENTE'}
                </div>
            </div>
          </div>

          <table>
            <thead>
              <tr>
                <th>Descripción del Producto</th>
                <th style="text-align: center;">Piezas</th>
                <th style="text-align: right;">Peso</th>
                <th style="text-align: right;">Precio Unit.</th>
                <th style="text-align: right;">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              ${itemsHtml}
              <tr>
                <td colspan="3"></td>
                <td style="padding: 20px 8px; text-align: right; font-weight: bold;">TOTAL A PAGAR</td>
                <td style="padding: 20px 8px; text-align: right; font-size: 20px; font-weight: 800; color: #1a1a1a;">$${total.toFixed(2)}</td>
              </tr>
            </tbody>
          </table>

          <div style="margin-top: 100px; display: grid; grid-template-columns: 1fr 1fr; gap: 100px; text-align: center;">
            <div style="border-top: 1px solid #333; padding-top: 10px; font-size: 12px;">Entregado por: ${pedido.vendedor_nombre || 'Firma Autorizada'}</div>
            <div style="border-top: 1px solid #333; padding-top: 10px; font-size: 12px;">Recibido conforme: ${pedido.cliente_nombre || 'Firma Cliente'}</div>
          </div>

          <div class="no-print" style="margin-top: 40px; text-align: center;">
            <button onclick="window.print()" style="padding: 10px 20px; background: #000; color: #fff; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">IMPRIMIR AHORA</button>
          </div>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // --- Filters ---
  const filteredClientes = useMemo(() => {
    return clientes.filter(c =>
      c.nombre_razon_social.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.ruc_cedula.includes(searchTerm)
    );
  }, [clientes, searchTerm]);

  const filteredPedidos = useMemo(() => {
    return pedidos.filter(p =>
      p.cliente_nombre?.toLowerCase().includes(orderSearchTerm.toLowerCase()) ||
      p.guia_remision?.toLowerCase().includes(orderSearchTerm.toLowerCase())
    );
  }, [pedidos, orderSearchTerm]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Ventas</h1>
          <p className="text-muted-foreground">Gestión comercial, seguimiento de deuda y pedidos.</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={isOrderDialogOpen} onOpenChange={setIsOrderDialogOpen}>
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
                        {clientes.map(c => (
                          <SelectItem key={c.id} value={c.id.toString()}>
                            {c.nombre_razon_social} (Límite: ${c.limite_credito})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label>Guía de Remisión / Ref</Label>
                    <Input value={orderForm.guia_remision} onChange={e => setOrderForm({ ...orderForm, guia_remision: e.target.value })} placeholder="Ej: GR-001" />
                  </div>
                </div>

                <div className="border rounded-lg p-4 space-y-4 bg-slate-50/50">
                  <h3 className="font-semibold text-sm flex items-center gap-2">
                    <Package className="w-4 h-4" /> Añadir Productos
                  </h3>
                  <div className="grid grid-cols-12 gap-2 items-end">
                    <div className="col-span-5 grid gap-1.5">
                      <Label className="text-[10px] uppercase text-muted-foreground">Producto</Label>
                      <Select value={newItem.producto} onValueChange={v => {
                        const p = productos.find(prod => prod.id.toString() === v);
                        setNewItem({ ...newItem, producto: v, precio_unitario: p?.precio_base || 0 });
                      }}>
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Producto..." />
                        </SelectTrigger>
                        <SelectContent>
                          {productos.map(p => (
                            <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-2 grid gap-1.5">
                      <Label className="text-[10px] uppercase text-muted-foreground">Peso (kg)</Label>
                      <Input type="number" className="h-8 text-xs font-mono" value={newItem.peso} onChange={e => setNewItem({ ...newItem, peso: parseFloat(e.target.value) })} />
                    </div>
                    <div className="col-span-3 grid gap-1.5">
                      <Label className="text-[10px] uppercase text-muted-foreground">Precio Unit ($)</Label>
                      <Input type="number" className="h-8 text-xs font-mono" value={newItem.precio_unitario} onChange={e => setNewItem({ ...newItem, precio_unitario: parseFloat(e.target.value) })} />
                    </div>
                    <div className="col-span-2">
                      <Button size="sm" variant="outline" className="w-full h-8" onClick={addOrderItem}>Add</Button>
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
                            <TableHead className="py-0 text-[10px] text-right">Subtotal</TableHead>
                            <TableHead className="py-0 text-[10px] text-right"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {orderItems.map((item, idx) => (
                            <TableRow key={idx} className="h-8">
                              <TableCell className="py-1 text-xs">{productos.find(p => p.id.toString() === item.producto)?.descripcion}</TableCell>
                              <TableCell className="py-1 text-xs text-right font-mono">{item.peso.toFixed(2)}</TableCell>
                              <TableCell className="py-1 text-xs text-right font-mono">${item.precio_unitario.toFixed(2)}</TableCell>
                              <TableCell className="py-1 text-xs text-right font-mono font-bold">${(item.peso * item.precio_unitario).toFixed(2)}</TableCell>
                              <TableCell className="py-1 text-right">
                                <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => removeOrderItem(idx)}>
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                          <TableRow className="bg-primary/5 font-bold">
                            <TableCell colSpan={3} className="text-right py-2">TOTAL PEDIDO:</TableCell>
                            <TableCell className="text-right py-2 text-primary">${calculateOrderTotal().toFixed(2)}</TableCell>
                            <TableCell></TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="space-y-0.5">
                    <Label>¿Está pagado?</Label>
                    <p className="text-xs text-muted-foreground">Si se marca como pagado, no afectará el saldo pendiente del cliente.</p>
                  </div>
                  <Switch checked={orderForm.esta_pagado} onCheckedChange={v => setOrderForm({ ...orderForm, esta_pagado: v })} />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOrderDialogOpen(false)}>Cancelar</Button>
                <Button className="bg-primary" onClick={handleCreateOrder}>Finalizar y Guardar</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Plus className="w-4 h-4" />
                Nuevo Cliente
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>{editingCliente ? 'Editar Cliente' : 'Registrar Nuevo Cliente'}</DialogTitle>
                <DialogDescription>Ingresa los datos generales del cliente.</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="ruc">RUC/Cédula</Label>
                  <Input id="ruc" value={formData.ruc_cedula} onChange={e => setFormData({ ...formData, ruc_cedula: e.target.value })} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="nombre">Nombre / Razón Social</Label>
                  <Input id="nombre" value={formData.nombre_razon_social} onChange={e => setFormData({ ...formData, nombre_razon_social: e.target.value })} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="direccion">Dirección</Label>
                  <Input id="direccion" value={formData.direccion_envio} onChange={e => setFormData({ ...formData, direccion_envio: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label>Nivel de Precio</Label>
                    <Select value={formData.nivel_precio} onValueChange={(v: any) => setFormData({ ...formData, nivel_precio: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="mayorista">Mayorista</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="limite_credito">Límite de Crédito ($)</Label>
                    <Input id="limite_credito" type="number" step="0.01" value={formData.limite_credito} onChange={e => setFormData({ ...formData, limite_credito: e.target.value })} />
                  </div>
                </div>
                <div className="flex items-center justify-between space-x-2 border p-3 rounded-lg">
                  <div className="space-y-0.5">
                    <Label className="text-base">Tiene Beneficios</Label>
                    <p className="text-sm text-muted-foreground">Activar descuentos especiales.</p>
                  </div>
                  <Switch checked={formData.tiene_beneficio} onCheckedChange={v => setFormData({ ...formData, tiene_beneficio: v })} />
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleCreateOrUpdateCliente}>{editingCliente ? 'Actualizar' : 'Registrar'}</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cuentas por Cobrar</CardTitle>
            <DollarSign className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">
              ${clientes.reduce((acc, c) => acc + (typeof c.saldo_pendiente === 'string' ? parseFloat(c.saldo_pendiente) : c.saldo_pendiente), 0).toFixed(2)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pedidos Realizados</CardTitle>
            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pedidos.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Clientes Totales</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{clientes.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Beneficiarios</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{clientes.filter(c => c.tiene_beneficio).length}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="clientes" className="space-y-4">
        <TabsList>
          <TabsTrigger value="clientes" className="gap-2">
            <Users className="w-4 h-4" /> Clientes
          </TabsTrigger>
          <TabsTrigger value="pedidos" className="gap-2">
            <ShoppingBag className="w-4 h-4" /> Últimas Ventas
          </TabsTrigger>
        </TabsList>

        <TabsContent value="clientes">
          <Card>
            <CardHeader>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <CardTitle>Directorio de Clientes</CardTitle>
                  <CardDescription>Consulta el estado financiero y última actividad.</CardDescription>
                </div>
                <div className="relative w-full md:w-72">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input placeholder="Buscar cliente..." className="pl-8" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cliente</TableHead>
                      <TableHead>Estado Cuenta</TableHead>
                      <TableHead>Beneficio</TableHead>
                      <TableHead>Última Compra</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <TableRow key={i}>
                          <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                          <TableCell className="text-right"><Skeleton className="h-8 w-8 ml-auto" /></TableCell>
                        </TableRow>
                      ))
                    ) : (
                      filteredClientes.map(cliente => {
                        const saldo = typeof cliente.saldo_pendiente === 'string' ? parseFloat(cliente.saldo_pendiente) : cliente.saldo_pendiente;
                        const isPaid = saldo <= 0;

                        return (
                          <TableRow key={cliente.id}>
                            <TableCell>
                              <div className="flex flex-col cursor-pointer hover:underline" onClick={() => { setSelectedCliente(cliente); setIsDetailOpen(true); }}>
                                <span className="font-semibold text-primary">{cliente.nombre_razon_social}</span>
                                <span className="text-[10px] text-muted-foreground font-mono">{cliente.ruc_cedula}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex flex-col gap-1">
                                {isPaid ? (
                                  <Badge variant="outline" className="text-green-600 bg-green-50 border-green-200 w-fit">Pagado</Badge>
                                ) : (
                                  <>
                                    <div className="flex justify-between text-[10px] mb-0.5">
                                      <span className="font-bold text-destructive">${saldo.toFixed(2)}</span>
                                      <span className="text-muted-foreground">de ${parseFloat(cliente.limite_credito.toString()).toFixed(0)}</span>
                                    </div>
                                    <div className="w-24 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full ${(saldo / parseFloat(cliente.limite_credito.toString())) > 0.8 ? 'bg-red-500' : 'bg-orange-400'}`}
                                        style={{ width: `${Math.min((saldo / parseFloat(cliente.limite_credito.toString())) * 100, 100)}%` }}
                                      />
                                    </div>
                                  </>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              {cliente.tiene_beneficio ? (
                                <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-none">Especial</Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground">Regular</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {cliente.ultima_compra ? (
                                <div className="flex flex-col text-[10px]">
                                  <span className="font-bold">{format(new Date(cliente.ultima_compra.fecha), 'dd/MM/yyyy')}</span>
                                  <span className="text-muted-foreground truncate max-w-[120px]">{cliente.ultima_compra.items[0]?.producto}</span>
                                </div>
                              ) : <span className="text-xs text-muted-foreground italic">Sin ventas</span>}
                            </TableCell>
                            <TableCell className="text-right">
                              <Button variant="ghost" size="icon" onClick={() => openEditDialog(cliente)}>
                                <CreditCard className="w-4 h-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pedidos">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Historial de Ventas Recientes</CardTitle>
                <div className="relative w-64">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input placeholder="Buscar por guía o cliente..." className="pl-8" value={orderSearchTerm} onChange={e => setOrderSearchTerm(e.target.value)} />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Guía / Ref</TableHead>
                    <TableHead>Estado Pago</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPedidos.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">No se encontraron pedidos.</TableCell>
                    </TableRow>
                  ) : (
                    filteredPedidos.map(p => (
                      <TableRow key={p.id}>
                        <TableCell className="text-xs font-mono">{format(new Date(p.fecha_pedido), 'dd/MM/yyyy HH:mm')}</TableCell>
                        <TableCell className="font-medium">{p.cliente_nombre}</TableCell>
                        <TableCell>{p.guia_remision || '-'}</TableCell>
                        <TableCell>
                          <Badge variant={p.esta_pagado ? "outline" : "destructive"} className={p.esta_pagado ? "text-green-600 border-green-200 bg-green-50" : ""}>
                            {p.esta_pagado ? "Pagado" : "Pendiente"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-bold">
                          ${(p.detalles?.reduce((sum: number, det: any) => sum + (det.peso * det.precio_unitario), 0) || 0).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="icon" onClick={() => handlePrintOrder(p)}>
                            <Printer className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Cliente Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Expediente de Cliente: {selectedCliente?.nombre_razon_social}</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-50 p-3 rounded border">
                <p className="text-[10px] uppercase text-muted-foreground mb-1">Saldo Actual</p>
                <p className="text-xl font-bold text-destructive">${parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0').toFixed(2)}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded border">
                <p className="text-[10px] uppercase text-muted-foreground mb-1">Límite Crédito</p>
                <p className="text-xl font-bold">${parseFloat(selectedCliente?.limite_credito?.toString() || '0').toFixed(0)}</p>
              </div>
            </div>

            <section>
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 underline decoration-primary">
                <History className="w-4 h-4" /> Historial de Transacciones
              </h3>
              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead className="text-[10px]">Fecha</TableHead>
                      <TableHead className="text-[10px]">Guía</TableHead>
                      <TableHead className="text-[10px]">Pago</TableHead>
                      <TableHead className="text-[10px] text-right">Monto</TableHead>
                      <TableHead className="text-[10px] text-right">Acción</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedCliente?.pedidos && selectedCliente.pedidos.length > 0 ? (
                      selectedCliente.pedidos.map(p => (
                        <TableRow key={p.id}>
                          <TableCell className="py-2 text-[10px]">{format(new Date(p.fecha_pedido), 'dd/MM/yyyy')}</TableCell>
                          <TableCell className="py-2 text-[10px] font-mono">{p.guia_remision}</TableCell>
                          <TableCell className="py-2">
                            <Badge className="text-[9px] h-3.5 px-1" variant={p.esta_pagado ? "outline" : "destructive"}>
                              {p.esta_pagado ? "SÍ" : "NO"}
                            </Badge>
                          </TableCell>
                          <TableCell className="py-2 text-right font-mono text-xs">${parseFloat(p.total.toString()).toFixed(2)}</TableCell>
                          <TableCell className="py-2 text-right">
                            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handlePrintOrder(p)}>
                              <Printer className="w-3 h-3" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : <TableRow><TableCell colSpan={5} className="text-center py-4 text-xs italic">Sin registros</TableCell></TableRow>}
                  </TableBody>
                </Table>
              </div>
            </section>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface HistoryIconProps extends React.SVGProps<SVGSVGElement> { }
const HistoryIcon: React.FC<HistoryIconProps> = (props) => <History {...props} />;
