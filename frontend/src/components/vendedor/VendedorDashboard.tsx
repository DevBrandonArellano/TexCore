import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Users, ShoppingBag, DollarSign, Calendar, Search, Plus, CreditCard, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react';
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

export function VendedorDashboard() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
  const [detallesPedido, setDetallesPedido] = useState<DetallePedido[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingCliente, setEditingCliente] = useState<Cliente | null>(null);
  
  const [formData, setFormData] = useState({
    ruc_cedula: '',
    nombre_razon_social: '',
    direccion_envio: '',
    nivel_precio: 'normal' as 'normal' | 'mayorista',
    tiene_beneficio: false,
    saldo_pendiente: '0.00'
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [clientesRes, pedidosRes, detallesRes, productosRes] = await Promise.all([
        apiClient.get('/clientes/'),
        apiClient.get('/pedidos-venta/'),
        apiClient.get('/detalles-pedido/'),
        apiClient.get('/productos/')
      ]);
      setClientes(clientesRes.data);
      setPedidos(pedidosRes.data);
      setDetallesPedido(detallesRes.data);
      setProductos(productosRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar la información del vendedor');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateOrUpdateCliente = async () => {
    try {
      const dataToSend = {
        ...formData,
        saldo_pendiente: parseFloat(formData.saldo_pendiente)
      };

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
    } catch (error) {
      console.error('Error saving cliente:', error);
      toast.error('Error al guardar el cliente');
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
      saldo_pendiente: cliente.saldo_pendiente.toString()
    });
    setIsDialogOpen(true);
  };

  const filteredClientes = useMemo(() => {
    return clientes.filter(c => 
      c.nombre_razon_social.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.ruc_cedula.includes(searchTerm)
    );
  }, [clientes, searchTerm]);

  const getClientStats = (clienteId: number) => {
    const clientOrders = pedidos
      .filter(p => p.cliente === clienteId)
      .sort((a, b) => new Date(b.fecha_pedido).getTime() - new Date(a.fecha_pedido).getTime());
    
    // const lastOrder = clientOrders[0];
    // let lastPurchaseInfo = { date: 'N/A', product: 'N/A', quantity: 0 };
    // Logic moved to backend


    const totalDeuda = clientOrders
      .filter(p => !p.esta_pagado)
      .length;

    return { totalDeuda };
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Ventas</h1>
          <p className="text-muted-foreground">Gestión de clientes, beneficios y estados de cuenta.</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={(open) => {
           setIsDialogOpen(open);
           if (!open) setEditingCliente(null);
        }}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Nuevo Cliente
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>{editingCliente ? 'Editar Cliente' : 'Registrar Nuevo Cliente'}</DialogTitle>
              <DialogDescription>
                Ingresa los datos del cliente y configura sus beneficios.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="ruc">RUC/Cédula</Label>
                <Input id="ruc" value={formData.ruc_cedula} onChange={e => setFormData({...formData, ruc_cedula: e.target.value})} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="nombre">Nombre / Razón Social</Label>
                <Input id="nombre" value={formData.nombre_razon_social} onChange={e => setFormData({...formData, nombre_razon_social: e.target.value})} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="direccion">Dirección</Label>
                <Input id="direccion" value={formData.direccion_envio} onChange={e => setFormData({...formData, direccion_envio: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label>Nivel de Precio</Label>
                  <Select value={formData.nivel_precio} onValueChange={(v: any) => setFormData({...formData, nivel_precio: v})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="mayorista">Mayorista</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="saldo">Saldo Pendiente ($)</Label>
                  <Input id="saldo" type="number" step="0.01" value={formData.saldo_pendiente} onChange={e => setFormData({...formData, saldo_pendiente: e.target.value})} />
                </div>
              </div>
              <div className="flex items-center justify-between space-x-2 border p-3 rounded-lg">
                <div className="space-y-0.5">
                  <Label className="text-base">Tiene Beneficios</Label>
                  <p className="text-sm text-muted-foreground">Activar descuentos especiales.</p>
                </div>
                <Switch checked={formData.tiene_beneficio} onCheckedChange={v => setFormData({...formData, tiene_beneficio: v})} />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleCreateOrUpdateCliente}>{editingCliente ? 'Actualizar' : 'Registrar'}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Clientes</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{clientes.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Clientes con Beneficio</CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{clientes.filter(c => c.tiene_beneficio).length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pedidos Totales</CardTitle>
            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pedidos.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cuentas por Cobrar</CardTitle>
            <DollarSign className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${clientes.reduce((acc, c) => acc + (typeof c.saldo_pendiente === 'string' ? parseFloat(c.saldo_pendiente) : c.saldo_pendiente), 0).toFixed(2)}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle>Directorio de Clientes</CardTitle>
              <CardDescription>Consulta el estado financiero y última actividad de cada cliente.</CardDescription>
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
                  <CardTitle className="text-xs" style={{display: 'none'}}>Hidden hack</CardTitle>
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
                    const { totalDeuda } = getClientStats(cliente.id);
                    const isPaid = (typeof cliente.saldo_pendiente === 'string' ? parseFloat(cliente.saldo_pendiente) : cliente.saldo_pendiente) <= 0;

                    return (
                      <TableRow key={cliente.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{cliente.nombre_razon_social}</span>
                            <span className="text-xs text-muted-foreground">{cliente.ruc_cedula}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {isPaid ? (
                              <Badge variant="outline" className="text-green-600 bg-green-50 border-green-200 gap-1">
                                <CheckCircle className="w-3 h-3" /> Pagado
                              </Badge>
                            ) : (
                              <div className="flex flex-col">
                                <Badge variant="destructive" className="gap-1 mb-1">
                                  <AlertCircle className="w-3 h-3" /> Con Saldo
                                </Badge>
                                <span className="text-xs font-mono text-destructive tracking-tighter">
                                  Deuda: ${cliente.saldo_pendiente}
                                </span>
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {cliente.tiene_beneficio ? (
                            <Badge className="bg-primary/10 text-primary border-primary/20" variant="outline">Activo</Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">Ninguno</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {cliente.ultima_compra ? (
                            <div className="flex flex-col text-sm">
                              <span className="text-muted-foreground font-mono">
                                {format(new Date(cliente.ultima_compra.fecha), 'dd MMM yyyy', { locale: es })}
                              </span>
                              <div className="flex flex-col gap-1 mt-1">
                                {cliente.ultima_compra.items.slice(0, 2).map((item, idx) => (
                                  <span key={idx} className="text-xs font-medium truncate max-w-[200px]" title={`${item.cantidad}x ${item.producto}`}>
                                    {item.cantidad}x {item.producto}
                                  </span>
                                ))}
                                {cliente.ultima_compra.items.length > 2 && (
                                  <span className="text-xs text-muted-foreground">
                                    +{cliente.ultima_compra.items.length - 2} más...
                                  </span>
                                )}
                              </div>
                            </div>
                          ) : (
                             <span className="text-xs text-muted-foreground">No hay registro</span>
                          )}
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
    </div>
  );
}
