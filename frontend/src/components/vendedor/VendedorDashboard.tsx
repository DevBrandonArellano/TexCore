import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Users, ShoppingBag, DollarSign, Calendar, Search, Plus, CreditCard, TrendingUp, Trash2, Printer, FileSpreadsheet, Download, ShieldCheck, Ban, Pencil, Clock, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import type { Cliente, PedidoVenta, Producto } from '../../lib/types';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { useAuth } from '../../lib/auth';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import { format } from 'date-fns';
import { parseFechaPedido, calcularDiasMora, calcularPorcentajeCredito } from './pedidoUtils';
import { AnularPedidoModal } from './AnularPedidoModal';
import { EditarPedidoModal } from './EditarPedidoModal';
import { HistorialPedidoModal } from './HistorialPedidoModal';
import { PagoReversionModal } from './PagoReversionModal';
import { NuevaVentaDialog } from './NuevaVentaDialog';
import { ClienteDetailDialog } from './ClienteDetailDialog';
import { useClientesVendedor } from './useClientesVendedor';
import { usePedidosVendedor } from './usePedidosVendedor';
import { usePagosCliente } from './usePagosCliente';
import { useReportesVendedor } from './useReportesVendedor';

export function VendedorDashboard() {
  const { profile } = useAuth();
  const vendedorId = profile?.user?.id;

  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const orderSearchTerm = searchParams.get('orderSearch') || '';

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [clientesRes, pedidosRes, productosRes] = await Promise.all([
        apiClient.get('/clientes/'),
        apiClient.get('/pedidos-venta/', { params: { limit: 100 } }),
        apiClient.get('/productos/', { params: { tipo: 'hilo,tela,subproducto' } })
      ]);
      setClientes(Array.isArray(clientesRes.data) ? clientesRes.data : (clientesRes.data as any).results || []);
      setPedidos(Array.isArray(pedidosRes.data) ? pedidosRes.data : (pedidosRes.data as any).results || []);
      setProductos(Array.isArray(productosRes.data) ? productosRes.data : (productosRes.data as any).results || []);
    } catch (error: any) {
      if (error?.response?.status === 401) return; // sesión expirada — manejado globalmente
      console.error('Error fetching data:', error);
      toast.error('Error al cargar la información del vendedor');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const clientesHook = useClientesVendedor(clientes, searchTerm, fetchData);
  const pedidosHook = usePedidosVendedor(pedidos, orderSearchTerm, fetchData);
  const pagosHook = usePagosCliente(clientesHook.selectedCliente, clientesHook.setSelectedCliente, fetchData);
  const reportesHook = useReportesVendedor(vendedorId);

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Ventas</h1>
          <p className="text-muted-foreground">Gestión comercial, seguimiento de deuda y pedidos.</p>
        </div>
        <div className="flex gap-2">
          <NuevaVentaDialog
            isOpen={pedidosHook.isOrderDialogOpen}
            onOpenChange={pedidosHook.setIsOrderDialogOpen}
            clientes={clientes}
            productos={productos}
            orderForm={pedidosHook.orderForm}
            setOrderForm={pedidosHook.setOrderForm}
            orderItems={pedidosHook.orderItems}
            newItem={pedidosHook.newItem}
            setNewItem={pedidosHook.setNewItem}
            addOrderItem={pedidosHook.addOrderItem}
            removeOrderItem={pedidosHook.removeOrderItem}
            onSubmit={pedidosHook.handleCreateOrder}
          />

          <Dialog open={clientesHook.isDialogOpen} onOpenChange={(open) => {
            clientesHook.setIsDialogOpen(open);
            if (!open) clientesHook.resetClienteForm();
          }}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Plus className="w-4 h-4" />
                Nuevo Cliente
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>{clientesHook.editingCliente ? 'Editar Cliente' : 'Registrar Nuevo Cliente'}</DialogTitle>
                <DialogDescription>Ingresa los datos generales del cliente.</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="ruc">RUC/Cédula</Label>
                  <Input id="ruc" value={clientesHook.formData.ruc_cedula} onChange={e => clientesHook.setFormData({ ...clientesHook.formData, ruc_cedula: e.target.value })} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="nombre">Nombre / Razón Social</Label>
                  <Input id="nombre" value={clientesHook.formData.nombre_razon_social} onChange={e => clientesHook.setFormData({ ...clientesHook.formData, nombre_razon_social: e.target.value })} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="direccion">Dirección</Label>
                  <Input id="direccion" value={clientesHook.formData.direccion_envio} onChange={e => clientesHook.setFormData({ ...clientesHook.formData, direccion_envio: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label>Nivel de Precio</Label>
                    <Select value={clientesHook.formData.nivel_precio} onValueChange={(v: any) => clientesHook.setFormData({ ...clientesHook.formData, nivel_precio: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="mayorista">Mayorista</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="limite_credito">Límite de Crédito ($)</Label>
                    <Input id="limite_credito" type="number" step="0.001" value={clientesHook.formData.limite_credito} onChange={e => clientesHook.setFormData({ ...clientesHook.formData, limite_credito: e.target.value })} onFocus={(e) => e.target.select()} />
                  </div>
                  <div className="grid gap-2">
                    <Label>Plazo Crédito</Label>
                    <Select value={(clientesHook.formData.plazo_credito_dias || 0).toString()} onValueChange={v => clientesHook.setFormData({ ...clientesHook.formData, plazo_credito_dias: parseInt(v) })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">Contado (0 Días)</SelectItem>
                        <SelectItem value="8">8 Días</SelectItem>
                        <SelectItem value="30">30 Días</SelectItem>
                        <SelectItem value="45">45 Días</SelectItem>
                        <SelectItem value="60">60 Días</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex items-center justify-between space-x-2 border p-3 rounded-lg">
                  <div className="space-y-0.5">
                    <Label className="text-base">Tiene Beneficios</Label>
                    <p className="text-sm text-muted-foreground">Activar descuentos especiales.</p>
                  </div>
                  <Switch className="scale-75 shadow-sm data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-slate-400" checked={clientesHook.formData.tiene_beneficio} onCheckedChange={v => clientesHook.setFormData({ ...clientesHook.formData, tiene_beneficio: v })} />
                </div>
                {clientesHook.editingCliente && (
                  <div className="space-y-2 p-3 bg-primary/5 rounded-lg border border-primary/20">
                    <Label htmlFor="justificacion" className="flex items-center gap-2 font-bold text-primary">
                      <ShieldCheck className="w-4 h-4" /> Justificación <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="justificacion"
                      value={clientesHook.formData._justificacion_auditoria}
                      onChange={e => clientesHook.setFormData({ ...clientesHook.formData, _justificacion_auditoria: e.target.value })}
                      placeholder="Ej: Cambio de dirección solicitado por el cliente..."
                      className="bg-background"
                    />
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button onClick={clientesHook.handleCreateOrUpdateCliente}>{clientesHook.editingCliente ? 'Actualizar' : 'Registrar'}</Button>
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
              ${(Array.isArray(clientes) ? clientes : []).reduce((acc, c) => acc + (typeof c.saldo_pendiente === 'string' ? parseFloat(c.saldo_pendiente) : c.saldo_pendiente), 0).toFixed(3)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pedidos Realizados</CardTitle>
            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Array.isArray(pedidos) ? pedidos.length : 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Clientes Totales</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Array.isArray(clientes) ? clientes.length : 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Beneficiarios</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(Array.isArray(clientes) ? clientes : []).filter(c => c.tiene_beneficio).length}</div>
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
          <TabsTrigger value="reportes" className="gap-2">
            <FileSpreadsheet className="w-4 h-4" /> Reportes Excel
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
                  <Input placeholder="Buscar cliente..." className="pl-8" value={searchTerm} onChange={e => {
                    const val = e.target.value;
                    setSearchParams(prev => {
                      if (val) prev.set('search', val);
                      else prev.delete('search');
                      return prev;
                    }, { replace: true });
                  }} />
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 flex flex-col pt-0">
              <div className="flex-1 overflow-auto rounded-md border relative">
                <Table className="min-w-max">
                  <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
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
                      clientesHook.paginatedClientes.map(cliente => {
                        const saldo = typeof cliente.saldo_pendiente === 'string' ? parseFloat(cliente.saldo_pendiente) : cliente.saldo_pendiente;
                        const isPaid = saldo <= 0;
                        const inactiveClass = !cliente.is_active ? 'opacity-50 bg-slate-50' : '';
                        const limiteCredito = parseFloat(cliente.limite_credito.toString());
                        const porcentajeCredito = calcularPorcentajeCredito(saldo, limiteCredito);
                        const diasMoraText = calcularDiasMora(cliente.ultima_compra?.fecha, cliente.cartera_vencida);

                        return (
                          <TableRow key={cliente.id} className={inactiveClass}>
                            <TableCell>
                              <div className="flex flex-col cursor-pointer hover:underline" onClick={() => clientesHook.openClienteDetail(cliente)}>
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
                                      <span className="font-bold text-destructive">${saldo.toFixed(3)}</span>
                                      <span className="text-muted-foreground">de ${limiteCredito.toFixed(0)}</span>
                                    </div>
                                    <div className="w-24 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full ${porcentajeCredito > 80 ? 'bg-red-500' : 'bg-orange-400'}`}
                                        style={{ width: `${porcentajeCredito}%` }}
                                      />
                                    </div>
                                  </>
                                )}
                                {parseFloat(cliente.cartera_vencida?.toString() || '0') > 0 && (
                                  <div className="flex flex-col gap-1 mt-1">
                                    <Badge variant="destructive" className="w-fit text-[9px] px-1 py-0 h-4">Mora: ${parseFloat(cliente.cartera_vencida!.toString()).toFixed(3)}</Badge>
                                    {diasMoraText && (
                                      <span className="text-[9px] text-destructive flex items-center gap-1 font-bold">
                                        <Calendar className="w-3 h-3" /> {diasMoraText}
                                      </span>
                                    )}
                                  </div>
                                )}
                                <span className="text-[10px] text-muted-foreground">{cliente.plazo_credito_dias === 0 ? 'Contado' : `Crédito: ${cliente.plazo_credito_dias} Días`}</span>
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
                              <div className="flex justify-end gap-1">
                                <Button variant="ghost" size="icon" onClick={() => clientesHook.openEditDialog(cliente)}>
                                  <CreditCard className="w-4 h-4" />
                                </Button>
                                {cliente.is_active && (
                                  <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={() => clientesHook.handleInactivarCliente(cliente)}>
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
              {!loading && clientesHook.filteredClientes.length > 0 && (
                <div className="flex items-center justify-between mt-4">
                  <span className="text-sm text-muted-foreground">
                    Página {clientesHook.currentClientesPage} de {clientesHook.totalClientesPages}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => clientesHook.setCurrentClientesPage(Math.max(1, clientesHook.currentClientesPage - 1))}
                      disabled={clientesHook.currentClientesPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      Anterior
                    </Button>
                    <span className="flex items-center gap-1 text-sm">
                      <span className="text-muted-foreground">Ir a</span>
                      <Input
                        type="number"
                        min={1}
                        max={clientesHook.totalClientesPages}
                        defaultValue={clientesHook.currentClientesPage}
                        key={clientesHook.currentClientesPage}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const v = parseInt((e.target as HTMLInputElement).value, 10);
                            if (!isNaN(v) && v >= 1 && v <= clientesHook.totalClientesPages) clientesHook.setCurrentClientesPage(v);
                          }
                        }}
                        onBlur={(e) => {
                          const v = parseInt(e.target.value, 10);
                          if (!isNaN(v) && v >= 1 && v <= clientesHook.totalClientesPages) clientesHook.setCurrentClientesPage(v);
                        }}
                        className="w-14 h-8 text-center py-0 px-1"
                      />
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => clientesHook.setCurrentClientesPage(Math.min(clientesHook.totalClientesPages, clientesHook.currentClientesPage + 1))}
                      disabled={clientesHook.currentClientesPage === clientesHook.totalClientesPages}
                    >
                      Siguiente
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
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
                  <Input placeholder="Buscar por guía o cliente..." className="pl-8" value={orderSearchTerm} onChange={e => {
                    const val = e.target.value;
                    setSearchParams(prev => {
                      if (val) prev.set('orderSearch', val);
                      else prev.delete('orderSearch');
                      return prev;
                    }, { replace: true });
                  }} />
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 flex flex-col pt-0">
              <div className="flex-1 overflow-auto rounded-md border relative">
                <Table className="min-w-max">
                  <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
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
                    {pedidosHook.filteredPedidos.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">No se encontraron pedidos.</TableCell>
                      </TableRow>
                    ) : (
                      pedidosHook.paginatedPedidos.map(p => (
                        <TableRow key={p.id} className={p.anulado ? 'opacity-50 bg-red-50/30' : ''}>

                          <TableCell className="text-xs font-mono">{format(parseFechaPedido(p.fecha_pedido), 'dd/MM/yyyy HH:mm')}</TableCell>
                          <TableCell className="font-medium">{p.cliente_nombre}</TableCell>
                          <TableCell>{p.guia_remision || '-'}</TableCell>
                          <TableCell>
                            <div className="flex flex-col gap-1">
                              {p.anulado ? (
                                <Badge variant="destructive" className="text-xs w-fit">Anulado</Badge>
                              ) : (
                                <Badge
                                  variant={p.esta_pagado ? "outline" : "destructive"}
                                  className={
                                    p.esta_pagado
                                      ? "text-green-600 border-green-200 bg-green-50 w-fit"
                                      : parseFloat(String((p as any).porcentaje_pagado ?? 0)) > 0
                                        ? "text-amber-700 border-amber-200 bg-amber-50 w-fit"
                                        : "w-fit"
                                  }
                                >
                                  {p.esta_pagado
                                    ? "Pagado"
                                    : parseFloat(String((p as any).porcentaje_pagado ?? 0)) > 0
                                      ? `Abonado ${parseFloat(String((p as any).porcentaje_pagado)).toFixed(0)}%`
                                      : "Pendiente pago"}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-bold">
                            <span className={p.anulado ? 'line-through text-muted-foreground' : ''}>
                              ${(
                                (p.detalles?.reduce((sum: number, det: any) => {
                                  const subtotal = det.peso * det.precio_unitario;
                                  const iva = det.incluye_iva ? subtotal * 0.15 : 0;
                                  return sum + subtotal + iva;
                                }, 0) || 0) - parseFloat(p.valor_retencion?.toString() || '0')
                              ).toFixed(3)}
                            </span>

                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex gap-1 justify-end">
                              <Button variant="ghost" size="icon" title="Imprimir PDF" onClick={() => pedidosHook.handlePrintOrder(p)}>
                                <Printer className="w-4 h-4" />
                              </Button>
                              {!p.anulado && p.estado === 'pendiente' && (
                                <>
                                  <Button variant="ghost" size="icon" title="Editar pedido" onClick={() => pedidosHook.setPedidoEditar(p)}>
                                    <Pencil className="w-4 h-4" />
                                  </Button>
                                  <Button variant="ghost" size="icon" title="Anular pedido" className="text-destructive hover:text-destructive" onClick={() => pedidosHook.setPedidoAnular(p)}>
                                    <Ban className="w-4 h-4" />
                                  </Button>
                                </>
                              )}
                              {p.anulado && (
                                <Button variant="ghost" size="icon" title="Ver motivo de anulación" onClick={() => pedidosHook.setPedidoHistorial(p)}>
                                  <Clock className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
              {pedidosHook.filteredPedidos.length > 0 && (
                <div className="flex items-center justify-between mt-4">
                  <span className="text-sm text-muted-foreground">
                    Página {pedidosHook.currentPedidosPage} de {pedidosHook.totalPedidosPages}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => pedidosHook.setCurrentPedidosPage(Math.max(1, pedidosHook.currentPedidosPage - 1))}
                      disabled={pedidosHook.currentPedidosPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      Anterior
                    </Button>
                    <span className="flex items-center gap-1 text-sm">
                      <span className="text-muted-foreground">Ir a</span>
                      <Input
                        type="number"
                        min={1}
                        max={pedidosHook.totalPedidosPages}
                        defaultValue={pedidosHook.currentPedidosPage}
                        key={pedidosHook.currentPedidosPage}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const v = parseInt((e.target as HTMLInputElement).value, 10);
                            if (!isNaN(v) && v >= 1 && v <= pedidosHook.totalPedidosPages) pedidosHook.setCurrentPedidosPage(v);
                          }
                        }}
                        onBlur={(e) => {
                          const v = parseInt(e.target.value, 10);
                          if (!isNaN(v) && v >= 1 && v <= pedidosHook.totalPedidosPages) pedidosHook.setCurrentPedidosPage(v);
                        }}
                        className="w-14 h-8 text-center py-0 px-1"
                      />
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => pedidosHook.setCurrentPedidosPage(Math.min(pedidosHook.totalPedidosPages, pedidosHook.currentPedidosPage + 1))}
                      disabled={pedidosHook.currentPedidosPage === pedidosHook.totalPedidosPages}
                    >
                      Siguiente
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reportes">
          <Card>
            <CardHeader>
              <CardTitle>Reportes Comerciales Avanzados</CardTitle>
              <CardDescription>Genera sábanas de datos en Excel conectadas en vivo a la base de datos.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl">
                <div className="space-y-2">
                  <Label>Fecha de Inicio del Periodo</Label>
                  <Input type="date" value={reportesHook.reportFechas.inicio} onChange={(e) => reportesHook.setReportFechas({ ...reportesHook.reportFechas, inicio: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Fecha de Fin del Periodo</Label>
                  <Input type="date" value={reportesHook.reportFechas.fin} onChange={(e) => reportesHook.setReportFechas({ ...reportesHook.reportFechas, fin: e.target.value })} />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t pt-6 max-w-4xl">
                <div className="flex flex-col items-center justify-center p-6 border rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors gap-3">
                  <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                    <ShoppingBag className="w-6 h-6 text-green-700" />
                  </div>
                  <h3 className="font-semibold text-center">Ventas Detalladas</h3>
                  <p className="text-xs text-center text-muted-foreground mb-2">Desglose de cada producto vendido en el periodo.</p>
                  <Button variant="outline" className="w-full gap-2 text-green-700 border-green-200 mt-auto" onClick={reportesHook.handleExportVentas}>
                    <Download className="w-4 h-4" /> Bajar Excel
                  </Button>
                </div>

                <div className="flex flex-col items-center justify-center p-6 border rounded-lg bg-indigo-50 hover:bg-indigo-100 transition-colors gap-3">
                  <div className="w-12 h-12 rounded-full bg-indigo-200 flex items-center justify-center">
                    <TrendingUp className="w-6 h-6 text-indigo-700" />
                  </div>
                  <h3 className="font-semibold text-center">Top Clientes</h3>
                  <p className="text-xs text-center text-muted-foreground mb-2">Ranking de cartera según el monto comprado.</p>
                  <Button variant="outline" className="w-full gap-2 text-indigo-700 border-indigo-200 mt-auto" onClick={reportesHook.handleExportTopClientes}>
                    <Download className="w-4 h-4" /> Bajar Excel
                  </Button>
                </div>

                <div className="flex flex-col items-center justify-center p-6 border rounded-lg bg-red-50 hover:bg-red-100 transition-colors gap-3">
                  <div className="w-12 h-12 rounded-full bg-red-200 flex items-center justify-center">
                    <AlertCircle className="w-6 h-6 text-red-700" />
                  </div>
                  <h3 className="font-semibold text-center">Cartera Vencida</h3>
                  <p className="text-xs text-center text-muted-foreground mb-2">Saldos pendientes e impagos actualizados hoy.</p>
                  <Button variant="outline" className="w-full gap-2 text-red-700 border-red-200 mt-auto" onClick={reportesHook.handleExportDeudores}>
                    <Download className="w-4 h-4" /> Bajar Excel
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

      </Tabs>

      <ClienteDetailDialog
        isOpen={clientesHook.isDetailOpen}
        onOpenChange={clientesHook.setIsDetailOpen}
        selectedCliente={clientesHook.selectedCliente}
        isPagoDialogOpen={pagosHook.isPagoDialogOpen}
        setIsPagoDialogOpen={pagosHook.setIsPagoDialogOpen}
        pagoForm={pagosHook.pagoForm}
        setPagoForm={pagosHook.setPagoForm}
        handleCreatePago={pagosHook.handleCreatePago}
        handlePrintOrder={pedidosHook.handlePrintOrder}
        handleInitiatePagoReversion={pagosHook.handleInitiatePagoReversion}
      />

      <AnularPedidoModal
        pedido={pedidosHook.pedidoAnular}
        onClose={() => pedidosHook.setPedidoAnular(null)}
        onSuccess={() => {
          pedidosHook.setPedidoAnular(null);
          fetchData();
        }}
      />
      <EditarPedidoModal
        pedido={pedidosHook.pedidoEditar}
        onClose={() => pedidosHook.setPedidoEditar(null)}
        onSuccess={() => {
          pedidosHook.setPedidoEditar(null);
          fetchData();
        }}
      />
      <HistorialPedidoModal
        pedido={pedidosHook.pedidoHistorial}
        onClose={() => pedidosHook.setPedidoHistorial(null)}
      />
      <PagoReversionModal
        pago={pagosHook.pagoRevertir}
        justificacion={pagosHook.pagoReversionJustificacion}
        loading={pagosHook.pagoReversionLoading}
        onJustificacionChange={pagosHook.setPagoReversionJustificacion}
        onClose={() => pagosHook.setPagoRevertir(null)}
        onConfirm={pagosHook.handleConfirmPagoReversion}
      />
    </div>
  );
}
