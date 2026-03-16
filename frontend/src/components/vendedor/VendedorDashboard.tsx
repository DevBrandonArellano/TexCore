import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Users, ShoppingBag, DollarSign, Calendar, Search, Plus, CreditCard, CheckCircle, AlertCircle, TrendingUp, Package, Trash2, Printer, History, FileSpreadsheet, Download, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Cliente, PedidoVenta, DetallePedido, Producto } from '../../lib/types';
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
import { es } from 'date-fns/locale';

/**
 * Parsea fecha_pedido del backend (UTC).
 * - Con Z o +00:00: ya es UTC → JS convierte a hora local al formatear.
 * - Sin timezone: se asume UTC para evitar desfase (ej: "2026-03-09T19:30" sin Z = local en JS, añadimos Z).
 */
function parseFechaPedido(value: string): Date {
  if (!value) return new Date();
  const trimmed = (value || '').trim();
  if (!trimmed) return new Date();
  if (trimmed.includes('T') && !/Z|[+-]\d{2}:?\d{2}$/.test(trimmed)) {
    return new Date(trimmed.endsWith('Z') ? trimmed : trimmed + 'Z');
  }
  if (trimmed.includes('T')) return new Date(trimmed);
  return new Date(trimmed + 'T12:00:00Z');
}

interface OrderItem {
  producto: string;
  cantidad: number;
  piezas: number;
  peso: number;
  precio_unitario: number;
  incluye_iva?: boolean;
}

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

  // Reportes States
  const [reportFechas, setReportFechas] = useState({
    inicio: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    fin: new Date().toISOString().split('T')[0]
  });

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
    saldo_pendiente: '0.000',
    limite_credito: '0.000',
    plazo_credito_dias: 0,
    cartera_vencida: '0.000',
    _justificacion_auditoria: ''
  });

  // Form States - Pedido
  const [orderForm, setOrderForm] = useState({
    cliente: '',
    guia_remision: '',
    esta_pagado: false,
    aplica_retencion: false,
    valor_retencion: '0'
  });
  const [pagoForm, setPagoForm] = useState({
    monto: '',
    metodo_pago: 'transferencia',
    comprobante: '',
    notas: ''
  });
  const [isPagoDialogOpen, setIsPagoDialogOpen] = useState(false);
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [newItem, setNewItem] = useState<{
    producto: string;
    cantidad: number;
    piezas: number;
    peso: string;
    precio_unitario: string;
    incluye_iva: boolean;
  }>({
    producto: '',
    cantidad: 1,
    piezas: 1,
    peso: '',
    precio_unitario: '',
    incluye_iva: true
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [clientesRes, pedidosRes, productosRes] = await Promise.all([
        apiClient.get('/clientes/'),
        apiClient.get('/pedidos-venta/', { params: { limit: 100 } }),
        apiClient.get('/productos/', { params: { tipo: 'hilo,tela,subproducto' } })
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
        limite_credito: parseFloat(formData.limite_credito),
        plazo_credito_dias: parseInt(formData.plazo_credito_dias as any),
        _justificacion_auditoria: formData._justificacion_auditoria
      };
      // @ts-ignore
      delete dataToSend.saldo_pendiente;
      // @ts-ignore
      delete dataToSend.cartera_vencida;

      if (editingCliente) {
        await apiClient.put(`/clientes/${editingCliente.id}/`, dataToSend);
        toast.success('Cliente actualizado correctamente');
      } else {
        // @ts-ignore
        delete dataToSend._justificacion_auditoria;
        await apiClient.post('/clientes/', dataToSend);
        toast.success('Cliente registrado correctamente');
      }
      setIsDialogOpen(false);
      setEditingCliente(null);
      setFormData({
        ruc_cedula: '',
        nombre_razon_social: '',
        direccion_envio: '',
        nivel_precio: 'normal',
        tiene_beneficio: false,
        saldo_pendiente: '0.000',
        limite_credito: '0.000',
        plazo_credito_dias: 0,
        cartera_vencida: '0.000',
        _justificacion_auditoria: ''
      });
      fetchData();
    } catch (error: any) {
      console.error('Error saving cliente:', error);
      if (error.response?.data) {
        const data = error.response.data;
        if (data.detail) {
          toast.error(data.detail);
        } else if (typeof data === 'object') {
          const messages = Object.entries(data).map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`).join('\\n');
          toast.error('Error de validación', { description: messages || 'Revisa los campos enviados.' });
        } else {
          toast.error('Error al guardar el cliente');
        }
      } else {
        toast.error('Error de conexión o servidor al guardar el cliente');
      }
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
      limite_credito: cliente.limite_credito.toString(),
      plazo_credito_dias: cliente.plazo_credito_dias || 0,
      cartera_vencida: cliente.cartera_vencida?.toString() || '0.000',
      _justificacion_auditoria: ''
    });
    setIsDialogOpen(true);
  };

  const handleInactivarCliente = async (cliente: Cliente) => {
    if (!window.confirm(`¿Estás seguro de que deseas inactivar al cliente ${cliente.nombre_razon_social}?`)) {
      return;
    }

    try {
      await apiClient.patch(`/clientes/${cliente.id}/`, {
        is_active: false,
        _justificacion_auditoria: 'Inactivación del cliente desde el panel comercial'
      });
      toast.success('Cliente inactivado correctamente');
      fetchData();
    } catch (error: any) {
      console.error('Error inactivating cliente:', error);
      toast.error('Error al inactivar el cliente');
    }
  };

  // --- Pedido Handlers ---
  const addOrderItem = () => {
    const pesoVal = parseFloat(newItem.peso) || 0;
    const precioVal = parseFloat(newItem.precio_unitario) || 0;

    if (!newItem.producto || pesoVal <= 0 || precioVal <= 0) {
      toast.error('Por favor completa todos los campos del item');
      return;
    }
    setOrderItems([...orderItems, { 
      ...newItem, 
      peso: pesoVal, 
      precio_unitario: precioVal 
    }]);
    setNewItem({
      producto: '',
      cantidad: 1,
      piezas: 1,
      peso: '',
      precio_unitario: '',
      incluye_iva: true
    });
  };

  const removeOrderItem = (index: number) => {
    setOrderItems(orderItems.filter((_, i) => i !== index));
  };

  const calculateOrderTotal = () => {
    return orderItems.reduce((acc, item) => {
      const subtotal = item.peso * item.precio_unitario;
      const iva = item.incluye_iva ? subtotal * 0.15 : 0;
      return acc + subtotal + iva;
    }, 0);
  };

  const handleCreateOrder = async () => {
    if (!orderForm.cliente || orderItems.length === 0) {
      toast.error('Por favor selecciona un cliente y añade al menos un producto');
      return;
    }
    
    const retencionNum = parseFloat(orderForm.valor_retencion) || 0;
    if (orderForm.aplica_retencion && retencionNum < 0) {
      toast.error('El valor de retención no puede ser negativo');
      return;
    }

    const totalCalculado = calculateOrderTotal();
    if (orderForm.aplica_retencion && retencionNum > totalCalculado) {
      toast.error('El valor de retención no puede superar el total de la factura');
      return;
    }

    try {
      // Map frontend expected format into API exactly
      // Notice the API actually does the IVA logic if its enabled, but just for payload:
      const orderData = {
        ...orderForm,
        cliente: parseInt(orderForm.cliente),
        detalles: orderItems,
        // Agregamos la retención al payload si el backend lo soporta,
        // o lo podemos tratar como un pago automático inmediato por ese monto, 
        // dependiendo de la implementación de Django. Por ahora lo pasamos.
        valor_retencion: orderForm.aplica_retencion ? retencionNum : 0
      };

      await apiClient.post('/pedidos-venta/', orderData);
      toast.success('Pedido creado correctamente');
      setIsOrderDialogOpen(false);
      setOrderItems([]);
      setOrderForm({ cliente: '', guia_remision: '', esta_pagado: false, aplica_retencion: false, valor_retencion: '0' });
      fetchData();
    } catch (error: any) {
      console.error('Error saving order:', error);
      const errorMsg = error.response?.data?.cliente || error.response?.data?.detail || 'Error al guardar el pedido';
      toast.error(errorMsg);
    }
  };

  const handleCreatePago = async () => {
    if (!selectedCliente || !pagoForm.monto || parseFloat(pagoForm.monto) <= 0) {
      toast.error('Por favor ingresa un monto válido');
      return;
    }

    try {
      const pagoData = {
        cliente: selectedCliente.id,
        monto: parseFloat(pagoForm.monto),
        metodo_pago: pagoForm.metodo_pago,
        comprobante: pagoForm.comprobante,
        notas: pagoForm.notas
      };

      await apiClient.post('/pagos-cliente/', pagoData);
      toast.success('Pago registrado correctamente');
      setIsPagoDialogOpen(false);
      setPagoForm({ monto: '', metodo_pago: 'transferencia', comprobante: '', notas: '' });

      // Refresh selected client data to show new balance/payment
      const updatedClient = await apiClient.get(`/clientes/${selectedCliente.id}/`);
      setSelectedCliente(updatedClient.data);
      fetchData();
    } catch (error: any) {
      console.error('Error recording payment:', error);
      toast.error('Error al registrar el pago');
    }
  };

  // --- Print Handler ---
  const handlePrintOrder = async (pedido: PedidoVenta) => {
    try {
      const response = await apiClient.get(`/pedidos-venta/${pedido.id}/download_pdf/`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pedido_${pedido.guia_remision || pedido.id}.pdf`);
      document.body.appendChild(link);
      link.click();

      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

    } catch (error) {
      console.error("Error downloading PDF", error);
      toast.error("Error al descargar el PDF de la nota de venta.");
    }
  };

  // --- Reports Handlers ---
  const handleExportVentas = async () => {
    if (!vendedorId) {
      toast.error("No se pudo identificar al vendedor. Cierra sesión e inicia de nuevo.");
      return;
    }
    try {
      const url = `/reporting/vendedores/${vendedorId}/ventas?fecha_inicio=${reportFechas.inicio}&fecha_fin=${reportFechas.fin}&format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `ventas_vendedor_${reportFechas.inicio}_${reportFechas.fin}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      toast.success("Excel descargado correctamente.");
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error("No se encontraron datos para estos parámetros.");
      } else if (error.response?.status === 500) {
        toast.error("Error del servidor al generar el reporte. Revisa los logs.");
      } else if (error.response?.status === 422) {
        toast.error("Parámetros inválidos. Verifica las fechas.");
      } else {
        toast.error("Error al exportar el reporte.");
      }
    }
  };

  const handleExportTopClientes = async () => {
    try {
      const url = `/reporting/vendedores/${vendedorId}/top-clientes?fecha_inicio=${reportFechas.inicio}&fecha_fin=${reportFechas.fin}&format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', `top_clientes_${reportFechas.inicio}_${reportFechas.fin}.xlsx`);
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error("No se encontraron clientes para estos parámetros.");
      } else {
        toast.error("Error al exportar el reporte.");
      }
    }
  };

  const handleExportDeudores = async () => {
    try {
      const url = `/reporting/vendedores/${vendedorId}/deudores?format=xlsx`;
      const response = await apiClient.get(url, { responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', `clientes_deudores.xlsx`);
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error("No se encontraron deudores en su cartera.");
      } else {
        toast.error("Error al exportar el reporte.");
      }
    }
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

  const selectedClientDetails = useMemo(() => {
    if (!orderForm.cliente) return null;
    return clientes.find(c => c.id.toString() === orderForm.cliente);
  }, [orderForm.cliente, clientes]);

  const isValidatingCash = useMemo(() => {
    if (!selectedClientDetails) return false;
    // Si es de contado (0 dias) y el pedido NO esta marcado como pagado, requerirá advertencia
    return selectedClientDetails.plazo_credito_dias === 0 && !orderForm.esta_pagado;
  }, [selectedClientDetails, orderForm.esta_pagado]);

  return (
    <div className="flex flex-col h-full space-y-6">
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
                    <Label>Guía de Remisión / Factura</Label>
                    <Input value={orderForm.guia_remision} onChange={e => setOrderForm({ ...orderForm, guia_remision: e.target.value })} placeholder="Ej: GR-001" />
                  </div>
                </div>

                {selectedClientDetails && (
                  <div className={`p-3 rounded-lg border flex gap-3 ${parseFloat(selectedClientDetails.cartera_vencida?.toString() || '0') > 0 ? 'bg-red-50 border-red-200' : 'bg-slate-50'}`}>
                     <div className="text-muted-foreground flex items-center justify-center">
                        {parseFloat(selectedClientDetails.cartera_vencida?.toString() || '0') > 0 ? <AlertCircle className="w-6 h-6 text-destructive"/> : <CheckCircle className="w-6 h-6 text-green-600"/> }
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
                          {productos.map(p => (
                            <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <div className="flex flex-col gap-1 mt-1">
                        <div className="flex items-center space-x-2 px-1">
                          <Switch id="iva-mode" className="scale-75 shadow-sm data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-slate-400" checked={newItem.incluye_iva} onCheckedChange={(v) => setNewItem({...newItem, incluye_iva: v})} />
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
                        onChange={e => {
                          let valStr = e.target.value.replace(',', '.');
                          // Remove leading zeros formatting (e.g., '010' -> '10') but keep '0.5'
                          if (valStr.length > 1 && valStr.startsWith('0') && !valStr.startsWith('0.')) {
                            valStr = valStr.replace(/^0+/, '');
                            if (valStr === '') valStr = '0'; // If they typed '00', keep one '0'
                          }
                          setNewItem({ ...newItem, peso: valStr });
                        }}
                        onFocus={(e) => e.target.select()}
                      />
                    </div>
                    <div className="col-span-3 grid gap-1.5 pb-6">
                      <Label className="text-[10px] uppercase text-muted-foreground">Precio Unit ($)</Label>
                      <Input 
                        type="text" 
                        className="h-8 text-xs font-mono" 
                        value={newItem.precio_unitario} 
                        onChange={e => {
                          let valStr = e.target.value.replace(',', '.');
                          // Remove leading zeros formatting (e.g., '010' -> '10') but keep '0.5'
                          if (valStr.length > 1 && valStr.startsWith('0') && !valStr.startsWith('0.')) {
                            valStr = valStr.replace(/^0+/, '');
                            if (valStr === '') valStr = '0';
                          }
                          setNewItem({ ...newItem, precio_unitario: valStr });
                        }}
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
                            <TableCell className="text-right py-2 text-primary">${calculateOrderTotal().toFixed(3)}</TableCell>
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
                        let valStr = e.target.value;
                        // Reemplazar coma por punto para decimales
                        valStr = valStr.replace(',', '.');
                        // Expresión regular para validar solo números y punto decimal
                        if (valStr === '' || /^\d*\.?\d*$/.test(valStr)) {
                          // Validar que no superte el total (opcional aquí para feedback visual, pero bloqueado en el envío)
                          const numVal = parseFloat(valStr) || 0;
                          if (numVal <= calculateOrderTotal()) {
                            setOrderForm({ ...orderForm, valor_retencion: valStr });
                          }
                        }
                      }}
                      onBlur={e => {
                        if (e.target.value === '' || e.target.value === '.') {
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
                        <span>${(calculateOrderTotal() - parseFloat(orderForm.valor_retencion)).toFixed(3)}</span>
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
                    <Input id="limite_credito" type="number" step="0.001" value={formData.limite_credito} onChange={e => setFormData({ ...formData, limite_credito: e.target.value })} onFocus={(e) => e.target.select()} /> 
                  </div>
                  <div className="grid gap-2">
                    <Label>Plazo Crédito</Label>
                    <Select value={(formData.plazo_credito_dias || 0).toString()} onValueChange={v => setFormData({ ...formData, plazo_credito_dias: parseInt(v) })}>
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
                  <Switch className="scale-75 shadow-sm data-[state=checked]:bg-blue-600 data-[state=unchecked]:bg-slate-400" checked={formData.tiene_beneficio} onCheckedChange={v => setFormData({ ...formData, tiene_beneficio: v })} />
                </div>
                {editingCliente && (
                  <div className="space-y-2 p-3 bg-primary/5 rounded-lg border border-primary/20">
                    <Label htmlFor="justificacion" className="flex items-center gap-2 font-bold text-primary">
                      <ShieldCheck className="w-4 h-4" /> Justificación <span className="text-destructive">*</span>
                    </Label>
                    <Input 
                      id="justificacion" 
                      value={formData._justificacion_auditoria} 
                      onChange={e => setFormData({ ...formData, _justificacion_auditoria: e.target.value })} 
                      placeholder="Ej: Cambio de dirección solicitado por el cliente..." 
                      className="bg-background"
                    />
                  </div>
                )}
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
              ${clientes.reduce((acc, c) => acc + (typeof c.saldo_pendiente === 'string' ? parseFloat(c.saldo_pendiente) : c.saldo_pendiente), 0).toFixed(3)}
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
                      filteredClientes.map(cliente => {
                        const saldo = typeof cliente.saldo_pendiente === 'string' ? parseFloat(cliente.saldo_pendiente) : cliente.saldo_pendiente;
                        const isPaid = saldo <= 0;
                        const inactiveClass = !cliente.is_active ? 'opacity-50 bg-slate-50' : '';

                        // Cálculo de días en mora
                        let diasMoraText = "";
                        if (cliente.ultima_compra?.fecha && parseFloat(cliente.cartera_vencida?.toString() || '0') > 0) {
                          const lastPurchase = new Date(cliente.ultima_compra.fecha);
                          const today = new Date();
                          const diffTime = Math.abs(today.getTime() - lastPurchase.getTime());
                          const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                          diasMoraText = `Últ. factura hace ${diffDays} días`;
                        }

                        return (
                          <TableRow key={cliente.id} className={inactiveClass}>
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
                                      <span className="font-bold text-destructive">${saldo.toFixed(3)}</span>
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
                                <Button variant="ghost" size="icon" onClick={() => openEditDialog(cliente)}>
                                  <CreditCard className="w-4 h-4" />
                                </Button>
                                {cliente.is_active && (
                                  <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={() => handleInactivarCliente(cliente)}>
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
                  {filteredPedidos.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">No se encontraron pedidos.</TableCell>
                    </TableRow>
                  ) : (
                    filteredPedidos.map(p => (
                      <TableRow key={p.id}>
                        <TableCell className="text-xs font-mono">{format(parseFechaPedido(p.fecha_pedido), 'dd/MM/yyyy HH:mm')}</TableCell>
                        <TableCell className="font-medium">{p.cliente_nombre}</TableCell>
                        <TableCell>{p.guia_remision || '-'}</TableCell>
                        <TableCell>
                          <Badge variant={p.esta_pagado ? "outline" : "destructive"} className={p.esta_pagado ? "text-green-600 border-green-200 bg-green-50" : ""}>
                            {p.esta_pagado ? "Pagado" : "Pendiente"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-bold">
                          ${(p.detalles?.reduce((sum: number, det: any) => sum + (det.peso * det.precio_unitario), 0) || 0).toFixed(3)}
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
              </div>
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
                  <Input type="date" value={reportFechas.inicio} onChange={(e) => setReportFechas({ ...reportFechas, inicio: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Fecha de Fin del Periodo</Label>
                  <Input type="date" value={reportFechas.fin} onChange={(e) => setReportFechas({ ...reportFechas, fin: e.target.value })} />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t pt-6 max-w-4xl">
                <div className="flex flex-col items-center justify-center p-6 border rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors gap-3">
                  <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                    <ShoppingBag className="w-6 h-6 text-green-700" />
                  </div>
                  <h3 className="font-semibold text-center">Ventas Detalladas</h3>
                  <p className="text-xs text-center text-muted-foreground mb-2">Desglose de cada producto vendido en el periodo.</p>
                  <Button variant="outline" className="w-full gap-2 text-green-700 border-green-200 mt-auto" onClick={handleExportVentas}>
                    <Download className="w-4 h-4" /> Bajar Excel
                  </Button>
                </div>

                <div className="flex flex-col items-center justify-center p-6 border rounded-lg bg-indigo-50 hover:bg-indigo-100 transition-colors gap-3">
                  <div className="w-12 h-12 rounded-full bg-indigo-200 flex items-center justify-center">
                    <TrendingUp className="w-6 h-6 text-indigo-700" />
                  </div>
                  <h3 className="font-semibold text-center">Top Clientes</h3>
                  <p className="text-xs text-center text-muted-foreground mb-2">Ranking de cartera según el monto comprado.</p>
                  <Button variant="outline" className="w-full gap-2 text-indigo-700 border-indigo-200 mt-auto" onClick={handleExportTopClientes}>
                    <Download className="w-4 h-4" /> Bajar Excel
                  </Button>
                </div>

                <div className="flex flex-col items-center justify-center p-6 border rounded-lg bg-red-50 hover:bg-red-100 transition-colors gap-3">
                  <div className="w-12 h-12 rounded-full bg-red-200 flex items-center justify-center">
                    <AlertCircle className="w-6 h-6 text-red-700" />
                  </div>
                  <h3 className="font-semibold text-center">Cartera Vencida</h3>
                  <p className="text-xs text-center text-muted-foreground mb-2">Saldos pendientes e impagos actualizados hoy.</p>
                  <Button variant="outline" className="w-full gap-2 text-red-700 border-red-200 mt-auto" onClick={handleExportDeudores}>
                    <Download className="w-4 h-4" /> Bajar Excel
                  </Button>
                </div>
              </div>
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
              <div className={`p-3 rounded border ${parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0') > 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
                <p className="text-[10px] uppercase text-muted-foreground mb-1">
                  {parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0') >= 0 ? 'Saldo Pendiente' : 'Saldo a Favor'}
                </p>
                <div className="flex justify-between items-end">
                  <p className={`text-xl font-bold ${parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0') > 0 ? 'text-destructive' : 'text-green-600'}`}>
                    ${Math.abs(parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0')).toFixed(3)}
                  </p>
                  {parseFloat(selectedCliente?.cartera_vencida?.toString() || '0') > 0 && (
                     <div className="text-right flex flex-col items-end">
                        <span className="text-[10px] text-destructive font-bold flex items-center gap-1"><AlertCircle className="w-3 h-3"/> Cartera Vencida</span>
                        <span className="text-sm font-bold text-destructive">${parseFloat(selectedCliente?.cartera_vencida?.toString() || '0').toFixed(3)}</span>
                     </div>
                  )}
                </div>
              </div>
              <div className="bg-slate-50 p-3 rounded border">
                <p className="text-[10px] uppercase text-muted-foreground mb-1">Límite Crédito</p>
                <div className="flex items-center justify-between">
                  <p className="text-xl font-bold">${parseFloat(selectedCliente?.limite_credito?.toString() || '0').toFixed(0)}</p>
                  <Dialog open={isPagoDialogOpen} onOpenChange={setIsPagoDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" className="h-7 gap-1 bg-primary">
                        <DollarSign className="w-3 h-3" /> Abonos
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[400px]">
                      <DialogHeader>
                        <DialogTitle>Registrar Abono / Pago</DialogTitle>
                        <DialogDescription>Abona al saldo del cliente: {selectedCliente?.nombre_razon_social}</DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                          <Label>Monto a Abonar ($) <span className="text-destructive">*</span></Label>
                          <Input type="number" step="0.01" value={pagoForm.monto} onChange={e => setPagoForm({ ...pagoForm, monto: e.target.value })} placeholder="0.00" />
                        </div>
                        <div className="grid gap-2">
                          <Label>Método de Pago</Label>
                          <Select value={pagoForm.metodo_pago} onValueChange={v => setPagoForm({ ...pagoForm, metodo_pago: v })}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="transferencia">Transferencia</SelectItem>
                              <SelectItem value="efectivo">Efectivo</SelectItem>
                              <SelectItem value="cheque">Cheque</SelectItem>
                              <SelectItem value="otro">Otro</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="grid gap-2">
                          <Label>Referencia / Comprobante</Label>
                          <Input value={pagoForm.comprobante} onChange={e => setPagoForm({ ...pagoForm, comprobante: e.target.value })} placeholder="# Transacción" />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setIsPagoDialogOpen(false)}>Cancelar</Button>
                        <Button onClick={handleCreatePago}>Confirmar Abono</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>
            </div>

            <section>
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 underline decoration-primary">
                <History className="w-4 h-4" /> Historial Comercial
              </h3>
              <Tabs defaultValue="ventas" className="w-full">
                <TabsList className="grid w-full grid-cols-2 h-8">
                  <TabsTrigger value="ventas" className="text-[10px]">Pedidos / Deuda</TabsTrigger>
                  <TabsTrigger value="pagos" className="text-[10px]">Abonos / Recibos</TabsTrigger>
                </TabsList>

                <TabsContent value="ventas" className="pt-3">
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader className="bg-slate-50">
                        <TableRow className="h-8">
                          <TableHead className="text-[10px]">Fecha</TableHead>
                          <TableHead className="text-[10px]">Guía</TableHead>
                          <TableHead className="text-[10px] text-right">Monto</TableHead>
                          <TableHead className="text-[10px] text-right">Acción</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedCliente?.pedidos && selectedCliente.pedidos.length > 0 ? (
                          selectedCliente.pedidos.map(p => (
                            <TableRow key={p.id} className="h-10">
                              <TableCell className="py-2 text-[10px]">{format(parseFechaPedido(p.fecha_pedido), 'dd/MM/yy')}</TableCell>
                              <TableCell className="py-2 text-[10px] font-mono">{p.guia_remision}</TableCell>
                              <TableCell className="py-2 text-right font-mono text-xs font-bold">${parseFloat(p.total?.toString() || '0').toFixed(2)}</TableCell>
                              <TableCell className="py-2 text-right">
                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handlePrintOrder(p)}>
                                  <Printer className="w-3 h-3" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))
                        ) : <TableRow><TableCell colSpan={4} className="text-center py-4 text-xs italic">Sin registros</TableCell></TableRow>}
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>

                <TabsContent value="pagos" className="pt-3">
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader className="bg-slate-50">
                        <TableRow className="h-8">
                          <TableHead className="text-[10px]">Fecha</TableHead>
                          <TableHead className="text-[10px]">Método</TableHead>
                          <TableHead className="text-[10px] text-right">Monto</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedCliente?.pagos && selectedCliente.pagos.length > 0 ? (
                          selectedCliente.pagos.map(p => (
                            <TableRow key={p.id} className="h-10">
                              <TableCell className="py-2 text-[10px]">{format(new Date(p.fecha), 'dd/MM/yy')}</TableCell>
                              <TableCell className="py-2 text-[10px] flex items-center gap-1 capitalize">
                                <CheckCircle className="w-2.5 h-2.5 text-green-500" /> {p.metodo_pago}
                              </TableCell>
                              <TableCell className="py-2 text-right font-mono text-xs text-green-600 font-bold">+ ${parseFloat(p.monto.toString()).toFixed(2)}</TableCell>
                            </TableRow>
                          ))
                        ) : <TableRow><TableCell colSpan={3} className="text-center py-4 text-xs italic">No hay abonos aún</TableCell></TableRow>}
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>
              </Tabs>
            </section>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface HistoryIconProps extends React.SVGProps<SVGSVGElement> { }
const HistoryIcon: React.FC<HistoryIconProps> = (props) => <History {...props} />;
