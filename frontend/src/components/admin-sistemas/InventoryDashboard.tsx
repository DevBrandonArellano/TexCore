import React, { useState, useEffect, useMemo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ProductSelect } from '../ui/product-select';
import { Package, TrendingUp, AlertTriangle, RefreshCw, Box, Archive, FileText, CheckCircle2, Clock, Truck, ShieldCheck, FileSpreadsheet, PlusCircle, Scan, Tag, Barcode, Printer, Trash2, AlertCircle, Edit2, Download, Send, History, ChevronLeft, ChevronRight, LogIn, Share2 } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Producto, Bodega, LoteProduccion, Proveedor, Movimiento } from '../../lib/types';
import { TransformationView } from './TransformationView';
import { EditarMovimientoDialog } from '../bodeguero/EditarMovimientoDialog';
import { AuditoriaDialog } from '../bodeguero/AuditoriaDialog';
import { Badge } from '../ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

interface StockItem {
  id: number;
  producto: string;
  bodega: string;
  lote: string | null;
  cantidad: string;
}

const ITEMS_PER_PAGE = 10;

// 1. StockView Component (Presentational)
const StockView = ({ stock, loading }: { stock: StockItem[], loading: boolean }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredStock = useMemo(() => {
    return stock.filter(item =>
      item.producto.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.bodega.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.lote && item.lote.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  }, [stock, searchTerm]);

  const paginatedStock = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredStock.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredStock, currentPage]);

  const totalPages = Math.ceil(filteredStock.length / ITEMS_PER_PAGE);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stock Actual</CardTitle>
        <CardDescription>Inventario disponible en todas las bodegas.</CardDescription>
        <Input
          placeholder="Buscar por producto, bodega o lote..."
          value={searchTerm}
          onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
          className="w-full mt-4"
        />
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col pt-0">
        <div className="flex-1 overflow-auto rounded-md border relative">
          <Table className="min-w-max">
            <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
              <TableRow>
                <TableHead>Producto</TableHead>
                <TableHead>Bodega</TableHead>
                <TableHead>Lote</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
              </TableRow>
            </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index}><TableCell colSpan={4}><Skeleton className="h-5 w-full" /></TableCell></TableRow>
              ))
            ) : paginatedStock.length > 0 ? (
              paginatedStock.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.producto}</TableCell>
                  <TableCell>{item.bodega}</TableCell>
                  <TableCell>{item.lote || '-'}</TableCell>
                  <TableCell className="text-right">{item.cantidad}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow><TableCell colSpan={4} className="text-center">No hay stock para mostrar.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
        </div>
        <div className="flex items-center justify-between mt-4 flex-shrink-0">
          <span className="text-sm text-muted-foreground">Página {currentPage} de {totalPages}</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1 || loading}><ChevronLeft className="w-4 h-4 mr-1" />Anterior</Button>
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages || loading}>Siguiente<ChevronRight className="w-4 h-4 ml-1" /></Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// 2. RegistrarEntradaView Component
const RegistrarEntradaView = ({ productos, bodegas, proveedores, onDataRefresh }: { productos: Producto[], bodegas: Bodega[], proveedores: Proveedor[], onDataRefresh: () => void }) => {
  const [formData, setFormData] = useState({ producto_id: '', bodega_destino_id: '', cantidad: '', documento_ref: '', lote_codigo: '', proveedor_id: '', pais: '', calidad: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.producto_id || !formData.bodega_destino_id || !formData.cantidad) {
      toast.error("Producto, Bodega de Destino y Cantidad son requeridos.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.post('/inventory/movimientos/', {
        tipo_movimiento: 'COMPRA',
        producto: parseInt(formData.producto_id),
        bodega_destino: parseInt(formData.bodega_destino_id),
        cantidad: parseFloat(formData.cantidad),
        lote_codigo: formData.lote_codigo, // Nuevo campo para crear/asignar lote
        documento_ref: formData.documento_ref,
        proveedor: formData.proveedor_id ? parseInt(formData.proveedor_id) : null,
        pais: formData.pais,
        calidad: formData.calidad,
      });
      toast.success("Entrada de materia prima registrada con éxito.");
      onDataRefresh();
      setFormData({ producto_id: '', bodega_destino_id: '', cantidad: '', documento_ref: '', lote_codigo: '', proveedor_id: '', pais: '', calidad: '' });
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
              <ProductSelect
                productos={productos}
                value={formData.producto_id}
                onValueChange={v => setFormData(f => ({ ...f, producto_id: v }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-bodega">Bodega de Destino</Label>
              <Select value={formData.bodega_destino_id} onValueChange={v => setFormData(f => ({ ...f, bodega_destino_id: v }))}><SelectTrigger id="entrada-bodega"><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger><SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent></Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-lote">Código de Lote (Opcional)</Label>
              <Input id="entrada-lote" value={formData.lote_codigo} onChange={e => setFormData(f => ({ ...f, lote_codigo: e.target.value }))} placeholder="Ej: LOTE-MP-2026-001" />
              <p className="text-xs text-muted-foreground">Deja en blanco si no aplica.</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-cantidad">Cantidad</Label>
              <Input id="entrada-cantidad" type="number" step="any" value={formData.cantidad} onChange={e => setFormData(f => ({ ...f, cantidad: e.target.value }))} placeholder="e.g., 100.5" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entrada-proveedor">Proveedor</Label>
              <Select value={formData.proveedor_id} onValueChange={v => setFormData(f => ({ ...f, proveedor_id: v }))}>
                <SelectTrigger id="entrada-proveedor"><SelectValue placeholder="Selecciona un proveedor" /></SelectTrigger>
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
              <Label htmlFor="entrada-ref">Documento de Referencia</Label>
              <Input id="entrada-ref" value={formData.documento_ref} onChange={e => setFormData(f => ({ ...f, documento_ref: e.target.value }))} placeholder="Ej: Factura #12345" />
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Registrando...' : 'Registrar Entrada'}</Button>
        </form>
      </CardContent>
    </Card>
  );
};

// ... (TransferView and KardexView remain the same) ...
const TransferView = ({ productos, bodegas, lotesProduccion }: { productos: Producto[], bodegas: Bodega[], lotesProduccion: LoteProduccion[] }) => {
  const [formData, setFormData] = useState({
    producto_id: '',
    bodega_origen_id: '',
    bodega_destino_id: '',
    cantidad: '',
    lote_id: '',
    observaciones: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.producto_id) newErrors.producto_id = 'Producto es requerido.';
    if (!formData.bodega_origen_id) newErrors.bodega_origen_id = 'Bodega de origen es requerida.';
    if (!formData.bodega_destino_id) newErrors.bodega_destino_id = 'Bodega de destino es requerida.';
    if (!formData.cantidad || parseFloat(formData.cantidad) <= 0) newErrors.cantidad = 'Cantidad debe ser un número positivo.';
    if (formData.bodega_origen_id && formData.bodega_origen_id === formData.bodega_destino_id) {
      newErrors.bodega_destino_id = 'La bodega de destino no puede ser la misma que la de origen.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) {
      toast.error('Por favor, corrige los errores en el formulario.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        producto_id: parseInt(formData.producto_id),
        bodega_origen_id: parseInt(formData.bodega_origen_id),
        bodega_destino_id: parseInt(formData.bodega_destino_id),
        cantidad: parseFloat(formData.cantidad),
        lote_id: formData.lote_id ? parseInt(formData.lote_id) : null,
        observaciones: formData.observaciones,
      };
      await apiClient.post('/inventory/transferencias/', payload);
      toast.success('Transferencia realizada con éxito');
      setFormData({
        producto_id: '',
        bodega_origen_id: '',
        bodega_destino_id: '',
        cantidad: '',
        lote_id: '',
        observaciones: '',
      });
    } catch (error: any) {
      if (error.response?.data) {
        const data = error.response.data;
        if (data.error) {
          toast.error('Error en la transferencia', { description: data.error });
        } else if (typeof data === 'object') {
          // Si el backend devuelve validaciones de campos (del serializer)
          const messages = Object.entries(data).map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`).join('\n');
          toast.error('Error de validación', { description: messages || 'Revisa los campos enviados.' });
        } else {
          toast.error('Error en la transferencia', { description: 'Ocurrió un error inesperado.' });
        }
      } else {
        toast.error('Error en la transferencia', { description: 'No se pudo conectar con el servidor.' });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Realizar Transferencia</CardTitle>
        <CardDescription>Mueve stock de una bodega a otra.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="producto_id">Producto</Label>
              <ProductSelect
                productos={productos}
                value={formData.producto_id}
                onValueChange={(value) => setFormData(prev => ({ ...prev, producto_id: value, lote_id: '' }))}
              />
              {errors.producto_id && <p className="text-sm text-destructive">{errors.producto_id}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="cantidad">Cantidad</Label>
              <Input id="cantidad" type="number" value={formData.cantidad} onChange={(e) => setFormData(prev => ({ ...prev, cantidad: e.target.value }))} placeholder="e.g., 10.5" />
              {errors.cantidad && <p className="text-sm text-destructive">{errors.cantidad}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="bodega_origen_id">Bodega de Origen</Label>
              <Select value={formData.bodega_origen_id} onValueChange={(value) => setFormData(prev => ({ ...prev, bodega_origen_id: value }))}>
                <SelectTrigger id="bodega_origen_id"><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger>
                <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
              </Select>
              {errors.bodega_origen_id && <p className="text-sm text-destructive">{errors.bodega_origen_id}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="bodega_destino_id">Bodega de Destino</Label>
              <Select value={formData.bodega_destino_id} onValueChange={(value) => setFormData(prev => ({ ...prev, bodega_destino_id: value }))} disabled={!formData.bodega_origen_id}>
                <SelectTrigger id="bodega_destino_id"><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger>
                <SelectContent>{bodegas.filter(b => b.id.toString() !== formData.bodega_origen_id).map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
              </Select>
              {errors.bodega_destino_id && <p className="text-sm text-destructive">{errors.bodega_destino_id}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="lote_id">Lote (Opcional)</Label>
              <Select value={formData.lote_id} onValueChange={(value) => setFormData(prev => ({ ...prev, lote_id: value }))} disabled={lotesProduccion.length === 0}>
                <SelectTrigger id="lote_id"><SelectValue placeholder="Selecciona un lote si aplica" /></SelectTrigger>
                <SelectContent>{lotesProduccion.map(l => <SelectItem key={l.id} value={l.id.toString()}>{l.codigo_lote}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="observaciones">Observaciones / Comentarios</Label>
              <Input id="observaciones" value={formData.observaciones} onChange={e => setFormData(prev => ({ ...prev, observaciones: e.target.value }))} placeholder="Agrega un comentario sobre la transferencia" />
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Transfiriendo...' : 'Realizar Transferencia'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

const KardexView = ({ productos, bodegas, proveedores }: { productos: Producto[], bodegas: Bodega[], proveedores: Proveedor[] }) => {
  const [selectedBodega, setSelectedBodega] = useState('');
  const [selectedProducto, setSelectedProducto] = useState('');
  const [selectedProveedor, setSelectedProveedor] = useState('all');
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [loteCodigo, setLoteCodigo] = useState('');
  const [kardexData, setKardexData] = useState<Movimiento[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Estados para diálogos
  const [editingMovimiento, setEditingMovimiento] = useState<any | null>(null);
  const [showAuditDialog, setShowAuditDialog] = useState(false);
  const [selectedAuditId, setSelectedAuditId] = useState<number | null>(null);

  const handleFetchKardex = async () => {
    if (!selectedBodega || !selectedProducto) {
      toast.info('Por favor, selecciona una bodega y un producto.');
      return;
    }
    setIsLoading(true);
    try {
      const response = await apiClient.get(`/inventory/bodegas/${selectedBodega}/kardex/`, {
        params: { 
          producto_id: selectedProducto,
          ...(selectedProveedor !== 'all' && { proveedor_id: selectedProveedor }),
          ...(fechaInicio && { fecha_inicio: fechaInicio }),
          ...(fechaFin && { fecha_fin: fechaFin }),
          ...(loteCodigo && { lote_codigo: loteCodigo })
        },
      });
      console.log("Kardex data:", response.data);
      setKardexData(response.data);
      if (response.data.length === 0) {
        toast.info('No se encontraron movimientos para esta selección.');
      }
    } catch (error) {
      toast.error('Error al consultar el Kardex.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditClick = (movimiento: any) => {
    setEditingMovimiento(movimiento);
  };

  const handleAuditClick = (movimientoId: number) => {
    setSelectedAuditId(movimientoId);
    setShowAuditDialog(true);
  };

  const handleExportKardex = async () => {
    if (!selectedBodega) {
      toast.info('Por favor, selecciona al menos una bodega para exportar.');
      return;
    }
    
    // Si no hay producto, exportamos el stock general
    const esReporteGeneral = !selectedProducto;
    
    try {
      // Llamada al microservicio en el puerto 8002 configurado
      const prodParam = !esReporteGeneral ? `&producto_id=${selectedProducto}` : '';
      const provParam = selectedProveedor !== 'all' ? `&proveedor_id=${selectedProveedor}` : '';
      const initParam = fechaInicio ? `&fecha_inicio=${fechaInicio}` : '';
      const finParam = fechaFin ? `&fecha_fin=${fechaFin}` : '';
      const loteParam = loteCodigo ? `&lote_codigo=${loteCodigo}` : '';
      const url = `/api/reporting/export/kardex?bodega_id=${selectedBodega}${prodParam}${provParam}${initParam}${finParam}${loteParam}&format=xlsx`;
      
      window.open(url, "_blank");
      
      if (esReporteGeneral) {
        toast.success('Generando reporte general de stock en Excel...');
      } else {
        toast.success('Generando Kardex en Excel...');
      }
    } catch (error) {
      toast.error('Error al intentar descargar el Excel.');
    }
  };

  return (
    <Card className="flex flex-col h-full min-h-0">
      <CardHeader className="flex-shrink-0">
        <CardTitle>Consultar Kardex</CardTitle>
        <CardDescription>Consulta el historial de movimientos de un producto en una bodega.</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col pt-0 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3 items-end flex-shrink-0 bg-slate-50 p-3 rounded-md border">
          <div className="space-y-1 col-span-1">
            <Label htmlFor="kardex-bodega" className="text-xs font-semibold">Bodega</Label>
            <Select value={selectedBodega} onValueChange={setSelectedBodega}>
              <SelectTrigger id="kardex-bodega" className="h-8 text-xs"><SelectValue placeholder="Bodega" /></SelectTrigger>
              <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1 col-span-1">
            <Label htmlFor="kardex-proveedor" className="text-xs font-semibold">Proveedor</Label>
            <Select value={selectedProveedor} onValueChange={setSelectedProveedor}>
              <SelectTrigger id="kardex-proveedor" className="h-8 text-xs"><SelectValue placeholder="Todos" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los proveedores</SelectItem>
                {proveedores.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.nombre}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1 col-span-1 md:col-span-2">
            <Label htmlFor="kardex-producto" className="text-xs font-semibold">Producto</Label>
            <div className="h-8">
              <ProductSelect
                productos={productos}
                value={selectedProducto}
                onValueChange={setSelectedProducto}
              />
            </div>
          </div>
          <div className="space-y-1 col-span-1">
            <Label htmlFor="fecha-inicio" className="text-xs font-semibold">Desde</Label>
            <Input id="fecha-inicio" type="date" className="h-8 text-xs" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
          </div>
          <div className="space-y-1 col-span-1">
            <Label htmlFor="fecha-fin" className="text-xs font-semibold">Hasta</Label>
            <Input id="fecha-fin" type="date" className="h-8 text-xs" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
          </div>
          <div className="space-y-1 col-span-1">
            <Label htmlFor="lote-codigo" className="text-xs font-semibold">Lote</Label>
            <Input id="lote-codigo" type="text" placeholder="Código Lote" className="h-8 text-xs" value={loteCodigo} onChange={(e) => setLoteCodigo(e.target.value)} />
          </div>
          <div className="flex gap-2 col-span-1 md:col-span-5 justify-end">
            <Button onClick={handleExportKardex} variant="outline" size="sm" className="gap-2 text-green-700 border-green-200 hover:bg-green-50">
              <Download className="w-3 h-3" />
              Excel
            </Button>
            <Button onClick={handleFetchKardex} disabled={isLoading} size="sm">
              {isLoading ? 'Consultando...' : 'Consultar Kardex'}
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-auto rounded-md border relative bg-white">
          <Table className="min-w-max text-xs">
            <TableHeader className="sticky top-0 z-10 bg-slate-100 shadow-sm border-b">
              <TableRow className="h-8">
                <TableHead className="py-1 px-2 h-auto text-slate-700">Fecha</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700">Código</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700">Descripción</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700">Operación</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700">Lote</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700 text-right">Entrada</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700 text-right">Salida</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700 text-right font-bold">Saldo</TableHead>
                <TableHead className="py-1 px-2 h-auto text-slate-700 text-center">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={9} className="text-center py-4">Cargando datos...</TableCell></TableRow>
            ) : kardexData.length > 0 ? (
              <>
                {kardexData.map((row, index) => (
                  <TableRow key={index} className={`h-7 ${row.editado ? "bg-amber-50/50" : ""} hover:bg-slate-50 transition-colors`}>
                    <TableCell className="py-1 px-2 font-mono whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        {row.fecha && row.tipo_movimiento !== "SALDO INICIAL" ? new Date(row.fecha).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' }) : row.fecha}
                        {row.editado && <span title="Editado"><AlertCircle className="w-3 h-3 text-amber-500" /></span>}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 px-2 font-mono">{row.codigo_producto || '-'}</TableCell>
                    <TableCell className="py-1 px-2 truncate max-w-[200px]" title={row.descripcion_producto}>{row.descripcion_producto || '-'}</TableCell>
                    <TableCell className="py-1 px-2">
                      <div className="flex flex-col">
                        <span className={`font-semibold ${row.tipo_movimiento === 'SALDO INICIAL' ? 'text-blue-600' : ''}`}>{row.tipo_movimiento}</span>
                        {row.documento_ref && row.documento_ref !== '-' && <span className="text-[0.65rem] text-slate-500 font-mono truncate max-w-[150px]">{row.documento_ref}</span>}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 px-2 font-mono">{row.lote || '-'}</TableCell>
                    <TableCell className="py-1 px-2 text-right text-green-700 font-mono">
                      {row.entrada ? Number(row.entrada).toFixed(2) : ''}
                    </TableCell>
                    <TableCell className="py-1 px-2 text-right text-red-600 font-mono">
                      {row.salida ? Number(row.salida).toFixed(2) : ''}
                    </TableCell>
                    <TableCell className="py-1 px-2 text-right font-bold font-mono bg-slate-50/50">
                      {Number(row.saldo_resultante).toFixed(2)}
                    </TableCell>
                    <TableCell className="py-1 px-2 text-center align-middle">
                      {row.tipo_movimiento !== "SALDO INICIAL" && (
                        <div className="flex items-center justify-center gap-1">
                          {row.tipo_movimiento === 'Compra de Material' && row.estado === 'APROBADO' && (
                            <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full" onClick={() => handleEditClick(row)} title="Editar">
                              <Edit2 className="h-3 w-3 text-blue-600" />
                            </Button>
                          )}
                          {(row.editado || row.has_audit) && (
                            <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full" onClick={() => handleAuditClick(row.id || row.movimiento_id || 0)} title="Historial">
                              <FileText className="h-3 w-3 text-amber-600" />
                            </Button>
                          )}
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                
                {/* Panel de Totales de Control al final */}
                <TableRow className="h-8 bg-slate-100 font-bold border-t-2 border-slate-200">
                  <TableCell colSpan={5} className="py-2 px-2 text-right uppercase text-[0.7rem] tracking-wider text-slate-600">
                    Totales de Control del Periodo
                  </TableCell>
                  <TableCell className="py-2 px-2 text-right text-green-700 font-mono">
                    {kardexData.reduce((sum, row) => sum + (Number(row.entrada) || 0), 0).toFixed(2)}
                  </TableCell>
                  <TableCell className="py-2 px-2 text-right text-red-600 font-mono">
                    {kardexData.reduce((sum, row) => sum + (Number(row.salida) || 0), 0).toFixed(2)}
                  </TableCell>
                  <TableCell className="py-2 px-2 text-right font-mono">
                    {kardexData.length > 0 ? Number(kardexData[kardexData.length - 1].saldo_resultante).toFixed(2) : '0.00'}
                  </TableCell>
                  <TableCell></TableCell>
                </TableRow>
              </>
            ) : (
              <TableRow><TableCell colSpan={9} className="text-center py-8 text-slate-500">Selecciona los parámetros y consulta para ver datos.</TableCell></TableRow>
            )}
            </TableBody>
          </Table>
        </div>

        <EditarMovimientoDialog
          movimiento={editingMovimiento}
          open={!!editingMovimiento}
          onClose={() => setEditingMovimiento(null)}
          onSuccess={() => {
            handleFetchKardex();
            setEditingMovimiento(null);
          }}
        />

        <AuditoriaDialog
          movimientoId={selectedAuditId}
          open={showAuditDialog}
          onClose={() => setShowAuditDialog(false)}
        />
      </CardContent>
    </Card>
  );
};


// 4. Reportes Avanzados View
const ReportesView = ({ bodegas, productos }: { bodegas: Bodega[], productos: Producto[] }) => {
  const [reportType, setReportType] = useState('retro-kardex');
  
  // Retro-Kardex state
  const [rkFechaCorte, setRkFechaCorte] = useState('');
  const [rkBodega, setRkBodega] = useState('all');
  const [rkProducto, setRkProducto] = useState('');
  const [rkData, setRkData] = useState<any[]>([]);
  const [rkLoading, setRkLoading] = useState(false);

  // Lotes state
  const [mlLoteCodigo, setMlLoteCodigo] = useState('');
  const [mlData, setMlData] = useState<any>(null);
  const [mlLoading, setMlLoading] = useState(false);

  const fetchRetroKardex = async () => {
    if (!rkProducto || !rkFechaCorte) {
      toast.info('Producto y Fecha de Corte son obligatorios.');
      return;
    }
    setRkLoading(true);
    try {
      const response = await apiClient.get('/inventory/retro-kardex/', {
        params: {
          producto_id: rkProducto,
          fecha_corte: rkFechaCorte,
          ...(rkBodega !== 'all' && { bodega_id: rkBodega })
        }
      });
      setRkData(response.data);
      if (response.data.length === 0) toast.info('No hay stock para esos parámetros.');
    } catch (e) {
      toast.error('Error al generar Retro-Kardex');
    } finally {
      setRkLoading(false);
    }
  };

  const fetchMovimientosLote = async () => {
    if (!mlLoteCodigo) {
      toast.info('Debes ingresar el código del lote.');
      return;
    }
    setMlLoading(true);
    try {
      const response = await apiClient.get(`/inventory/lotes/${mlLoteCodigo}/movimientos/`);
      setMlData(response.data);
    } catch (e) {
      toast.error('Error al consultar lote o no existe.');
      setMlData(null);
    } finally {
      setMlLoading(false);
    }
  };

  return (
    <Card className="flex flex-col h-full min-h-0">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="flex justify-between items-center">
          <span>Reportes Operativos</span>
          <div className="flex bg-slate-100 p-1 rounded-md">
            <Button size="sm" variant={reportType === 'retro-kardex' ? 'default' : 'ghost'} onClick={() => setReportType('retro-kardex')} className="h-7 text-xs">Retro-Kardex</Button>
            <Button size="sm" variant={reportType === 'lote' ? 'default' : 'ghost'} onClick={() => setReportType('lote')} className="h-7 text-xs">Consulta de Lote</Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col pt-0 space-y-4">
        
        {reportType === 'retro-kardex' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end flex-shrink-0 bg-slate-50 p-3 rounded-md border">
              <div className="space-y-1 col-span-1 md:col-span-2">
                <Label className="text-xs font-semibold">Producto</Label>
                <div className="h-8">
                  <ProductSelect productos={productos} value={rkProducto} onValueChange={setRkProducto} />
                </div>
              </div>
              <div className="space-y-1 col-span-1">
                <Label className="text-xs font-semibold">Bodega</Label>
                <Select value={rkBodega} onValueChange={setRkBodega}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Todas" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las Bodegas</SelectItem>
                    {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1 col-span-1">
                <Label className="text-xs font-semibold">Fecha de Corte</Label>
                <Input type="date" className="h-8 text-xs" value={rkFechaCorte} onChange={e => setRkFechaCorte(e.target.value)} />
              </div>
              <div className="flex gap-2 justify-end col-span-1">
                <Button onClick={fetchRetroKardex} disabled={rkLoading} size="sm">
                  {rkLoading ? '...' : 'Generar'}
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-auto rounded-md border bg-white">
              <Table className="text-xs">
                <TableHeader className="sticky top-0 bg-slate-100 shadow-sm">
                  <TableRow className="h-8">
                    <TableHead className="py-1 px-2">Bodega</TableHead>
                    <TableHead className="py-1 px-2 text-right">Stock a la Fecha</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rkData.length > 0 ? (
                    rkData.map((row, i) => (
                      <TableRow key={i} className="h-7">
                        <TableCell className="py-1 px-2 font-mono text-slate-700">{row.bodega}</TableCell>
                        <TableCell className="py-1 px-2 text-right font-bold text-blue-700 font-mono">{Number(row.stock_calculado).toFixed(2)}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow><TableCell colSpan={2} className="text-center py-4 text-slate-500">Sin resultados</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </>
        )}

        {reportType === 'lote' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end flex-shrink-0 bg-slate-50 p-3 rounded-md border">
              <div className="space-y-1 col-span-1 md:col-span-3">
                <Label className="text-xs font-semibold">Código del Lote</Label>
                <Input autoFocus type="text" placeholder="Escanea o escribe el lote..." className="h-8 text-xs" value={mlLoteCodigo} onChange={e => setMlLoteCodigo(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && fetchMovimientosLote()} />
              </div>
              <div className="flex gap-2 justify-end col-span-1">
                <Button onClick={fetchMovimientosLote} disabled={mlLoading} size="sm" className="w-full">
                  {mlLoading ? 'Buscando...' : 'Rastrear Lote'}
                </Button>
              </div>
            </div>

            {mlData && (
              <div className="flex-1 flex flex-col min-h-0 bg-white border rounded-md p-3">
                <h3 className="font-semibold text-sm mb-2 text-slate-800">Trazabilidad: {mlData.lote_codigo} ({mlData.producto})</h3>
                <div className="flex-1 overflow-auto border rounded border-slate-200">
                  <Table className="text-xs">
                    <TableHeader className="sticky top-0 bg-slate-100 shadow-sm">
                      <TableRow className="h-8">
                        <TableHead className="py-1 px-2">Fecha</TableHead>
                        <TableHead className="py-1 px-2">Movimiento</TableHead>
                        <TableHead className="py-1 px-2">Origen → Destino</TableHead>
                        <TableHead className="py-1 px-2 text-right">Cantidad</TableHead>
                        <TableHead className="py-1 px-2">Ref</TableHead>
                        <TableHead className="py-1 px-2">Usuario</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mlData.historial.map((row: any, i: number) => (
                        <TableRow key={i} className="h-7 hover:bg-slate-50">
                          <TableCell className="py-1 px-2 font-mono whitespace-nowrap">{new Date(row.fecha).toLocaleString()}</TableCell>
                          <TableCell className="py-1 px-2 font-semibold text-slate-700">{row.tipo_movimiento}</TableCell>
                          <TableCell className="py-1 px-2 font-mono text-slate-600">{row.bodega_origen} → {row.bodega_destino}</TableCell>
                          <TableCell className="py-1 px-2 text-right font-mono font-medium">{Number(row.cantidad).toFixed(2)}</TableCell>
                          <TableCell className="py-1 px-2 font-mono text-[0.65rem] text-slate-500 max-w-[150px] truncate">{row.documento_ref || '-'}</TableCell>
                          <TableCell className="py-1 px-2">{row.usuario}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};


// 5. Main InventoryDashboard Component (Container)
export function InventoryDashboard({ productos, bodegas, lotesProduccion, onDataRefresh, proveedores }: { productos: Producto[], bodegas: Bodega[], lotesProduccion: LoteProduccion[], proveedores: Proveedor[], onDataRefresh: () => void }) {
  const [stock, setStock] = useState<StockItem[]>([]);
  const [loadingStock, setLoadingStock] = useState(true);

  const fetchStock = async () => {
    setLoadingStock(true);
    try {
      const response = await apiClient.get<StockItem[]>('/inventory/stock/');
      setStock(response.data);
    } catch (error) {
      toast.error('Error al cargar el stock.');
    } finally {
      setLoadingStock(false);
    }
  };

  useEffect(() => {
    fetchStock();
  }, []);

  const handleRefresh = () => {
    fetchStock();
    onDataRefresh(); // Also refresh parent data if needed
  }

  return (
    <Tabs defaultValue="stock" className="space-y-4">
      <TabsList className="grid w-full grid-cols-6">
        <TabsTrigger value="stock"><Package className="w-4 h-4 mr-2" />Stock Actual</TabsTrigger>
        <TabsTrigger value="entrada"><LogIn className="w-4 h-4 mr-2" />Entrada</TabsTrigger>
        <TabsTrigger value="transfer"><Send className="w-4 h-4 mr-2" />Transferencias</TabsTrigger>
        <TabsTrigger value="transform"><Share2 className="w-4 h-4 mr-2" />Transformación</TabsTrigger>
        <TabsTrigger value="kardex"><History className="w-4 h-4 mr-2" />Kardex</TabsTrigger>
        <TabsTrigger value="reportes"><FileText className="w-4 h-4 mr-2" />Reportes</TabsTrigger>
      </TabsList>

      <TabsContent value="stock" className="flex-1 min-h-0">
        <StockView stock={stock} loading={loadingStock} />
      </TabsContent>

      <TabsContent value="entrada" className="flex-1 min-h-0">
        <RegistrarEntradaView productos={productos} bodegas={bodegas} proveedores={proveedores} onDataRefresh={handleRefresh} />
      </TabsContent>

      <TabsContent value="transfer" className="flex-1 min-h-0">
        <TransferView productos={productos} bodegas={bodegas} lotesProduccion={lotesProduccion} />
      </TabsContent>

      <TabsContent value="transform" className="flex-1 min-h-0">
        <TransformationView productos={productos} bodegas={bodegas} lotesProduccion={lotesProduccion} />
      </TabsContent>

      <TabsContent value="kardex" className="flex-1 min-h-0">
        <KardexView productos={productos} bodegas={bodegas} proveedores={proveedores} />
      </TabsContent>
      
      <TabsContent value="reportes" className="flex-1 min-h-0">
        <ReportesView bodegas={bodegas} productos={productos} />
      </TabsContent>
    </Tabs>
  );
}