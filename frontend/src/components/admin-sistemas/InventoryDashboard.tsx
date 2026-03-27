import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { ProductSelect } from '../ui/product-select';
import { Package, ChevronLeft, ChevronRight, LogIn, Send, Share2, History, FileText, ShieldCheck, Download, Edit2, AlertCircle, Warehouse } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Producto, Bodega, LoteProduccion, Proveedor, Movimiento } from '../../lib/types';
import { TransformationView } from './TransformationView';
import { EditarMovimientoDialog } from '../bodeguero/EditarMovimientoDialog';
import { AuditoriaDialog } from '../bodeguero/AuditoriaDialog';

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
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

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
          onChange={(e) => {
            const val = e.target.value;
            setSearchParams(prev => {
              if (val) prev.set('search', val);
              else prev.delete('search');
              prev.set('page', '1');
              return prev;
            }, { replace: true });
          }}
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
            <Button size="sm" variant="outline" onClick={() => setSearchParams(prev => { prev.set('page', Math.max(1, currentPage - 1).toString()); return prev; })} disabled={currentPage === 1 || loading}><ChevronLeft className="w-4 h-4 mr-1" />Anterior</Button>
            <Button size="sm" variant="outline" onClick={() => setSearchParams(prev => { prev.set('page', Math.min(totalPages, currentPage + 1).toString()); return prev; })} disabled={currentPage === totalPages || loading}>Siguiente<ChevronRight className="w-4 h-4 ml-1" /></Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// 2. RegistrarEntradaView Component
const RegistrarEntradaView = ({ productos, bodegas, proveedores, onDataRefresh }: { productos: Producto[], bodegas: Bodega[], proveedores: Proveedor[], onDataRefresh: () => void }) => {
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
};

// 3. TransferView Component
const TransferView = ({ productos, bodegas, lotesProduccion }: { productos: Producto[], bodegas: Bodega[], lotesProduccion: LoteProduccion[] }) => {
  const [formData, setFormData] = useState({ producto_id: '', bodega_origen_id: '', bodega_destino_id: '', cantidad: '', lote_id: '', observaciones: '', _justificacion_auditoria: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.producto_id) newErrors.producto_id = 'Producto es requerido.';
    if (!formData.bodega_origen_id) newErrors.bodega_origen_id = 'Bodega origen requerida.';
    if (!formData.bodega_destino_id) newErrors.bodega_destino_id = 'Bodega destino requerida.';
    if (!formData.cantidad || parseFloat(formData.cantidad) <= 0) newErrors.cantidad = 'Cantidad inválida.';
    if (!formData._justificacion_auditoria) newErrors._justificacion_auditoria = 'Justificación requerida.';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setIsSubmitting(true);
    try {
      await apiClient.post('/inventory/transferencias/', {
        producto_id: parseInt(formData.producto_id),
        bodega_origen_id: parseInt(formData.bodega_origen_id),
        bodega_destino_id: parseInt(formData.bodega_destino_id),
        cantidad: parseFloat(formData.cantidad),
        lote_id: formData.lote_id ? parseInt(formData.lote_id) : null,
        observaciones: formData.observaciones,
        _justificacion_auditoria: formData._justificacion_auditoria,
      });
      toast.success('Transferencia exitosa');
      setFormData({ producto_id: '', bodega_origen_id: '', bodega_destino_id: '', cantidad: '', lote_id: '', observaciones: '', _justificacion_auditoria: '' });
    } catch (error: any) {
      toast.error('Error', { description: error.response?.data?.error || 'Error en transferencia' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transferencia de Stock</CardTitle>
        <CardDescription>Mover materiales entre bodegas.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Producto</Label>
              <ProductSelect productos={productos} value={formData.producto_id} onValueChange={v => setFormData(p => ({ ...p, producto_id: v, lote_id: '' }))} />
            </div>
            <div className="space-y-2">
              <Label>Cantidad</Label>
              <Input type="number" value={formData.cantidad} onChange={e => setFormData(p => ({ ...p, cantidad: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>Bodega Origen</Label>
              <Select value={formData.bodega_origen_id} onValueChange={v => setFormData(p => ({ ...p, bodega_origen_id: v }))}>
                <SelectTrigger><SelectValue placeholder="Origen" /></SelectTrigger>
                <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Bodega Destino</Label>
              <Select value={formData.bodega_destino_id} onValueChange={v => setFormData(p => ({ ...p, bodega_destino_id: v }))}>
                <SelectTrigger><SelectValue placeholder="Destino" /></SelectTrigger>
                <SelectContent>{bodegas.filter(b => b.id.toString() !== formData.bodega_origen_id).map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>Observaciones</Label>
              <Input value={formData.observaciones} onChange={e => setFormData(p => ({ ...p, observaciones: e.target.value }))} />
            </div>
            <div className="space-y-2 md:col-span-2 p-3 bg-primary/5 rounded-lg border border-primary/20">
              <Label className="flex items-center gap-2 font-bold text-primary">
                <ShieldCheck className="w-4 h-4" /> Justificación Obligatoria <span className="text-destructive">*</span>
              </Label>
              <Input value={formData._justificacion_auditoria} onChange={e => setFormData(p => ({ ...p, _justificacion_auditoria: e.target.value }))} placeholder="Motivo del traslado..." className="bg-background" />
              {errors._justificacion_auditoria && <p className="text-sm text-destructive">{errors._justificacion_auditoria}</p>}
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting}>Transferir</Button>
        </form>
      </CardContent>
    </Card>
  );
};

// 4. KardexView Component
const KardexView = ({ productos, bodegas, proveedores, onDataRefresh }: { productos: Producto[], bodegas: Bodega[], proveedores: Proveedor[], onDataRefresh?: () => void }) => {
  const [selectedBodega, setSelectedBodega] = useState('all');
  const [selectedProducto, setSelectedProducto] = useState('all');
  const [tipoOperacion, setTipoOperacion] = useState('all'); // all, entrada, salida
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [kardexData, setKardexData] = useState<Movimiento[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const [editingMovimiento, setEditingMovimiento] = useState<Movimiento | null>(null);
  const [showAuditDialog, setShowAuditDialog] = useState(false);
  const [selectedAuditId, setSelectedAuditId] = useState<number | null>(null);

  const handleFetchKardex = async () => {
    setIsLoading(true);
    try {
      const params: any = {};
      if (selectedBodega !== 'all') params.bodega_id = selectedBodega;
      if (selectedProducto !== 'all') params.producto_id = selectedProducto;
      if (tipoOperacion !== 'all') params.tipo = tipoOperacion;
      if (fechaInicio) params.fecha_desde = fechaInicio;
      if (fechaFin) params.fecha_hasta = fechaFin;

      const response = await apiClient.get('/inventory/movimientos/', { params });
      
      const respData = response.data;
      let data: any[] = [];
      if (respData && typeof respData === 'object' && Array.isArray(respData.results)) {
        data = respData.results;
      } else if (Array.isArray(respData)) {
        data = respData;
      }

      // Cálculo de Saldo Dinámico si hay Producto + Bodega seleccionado
      if (selectedProducto !== 'all' && selectedBodega !== 'all' && data.length > 0) {
        // Ordenar por fecha ascendente para calcular saldo
        data.sort((a: any, b: any) => new Date(a.fecha).getTime() - new Date(b.fecha).getTime());
        
        let saldoAcumulado = 0;
        data = data.map((mov: any) => {
          const cant = parseFloat(mov.cantidad);
          
          const esEntrada = (mov.bodega_destino?.id?.toString() === selectedBodega);
          const esSalida = (mov.bodega_origen?.id?.toString() === selectedBodega);
          
          if (esEntrada) saldoAcumulado += cant;
          if (esSalida) saldoAcumulado -= cant;

          return { ...mov, saldo_acumulado: saldoAcumulado, esEntrada, esSalida };
        });
        
        data.reverse();
      }

      setKardexData(data);
    } catch (error) {
      toast.error('Error al consultar movimientos.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearFilters = () => {
    setSelectedBodega('all');
    setSelectedProducto('all');
    setTipoOperacion('all');
    setFechaInicio('');
    setFechaFin('');
    setKardexData([]);
  };

  const exportToCSV = () => {
    if (kardexData.length === 0) {
      toast.error("No hay datos para exportar");
      return;
    }

    const headers = ["Fecha", "Producto", "Bodega Origen", "Bodega Destino", "Tipo", "Cantidad", "Referencia"];
    if (selectedProducto !== 'all' && selectedBodega !== 'all') headers.push("Saldo");

    const csvContent = [
      headers.join(","),
      ...kardexData.map(row => [
        new Date(row.fecha).toLocaleString(),
        row.producto,
        row.bodega_origen || "-",
        row.bodega_destino || "-",
        row.tipo_movimiento,
        row.cantidad,
        `"${row.documento_ref || ''}"`,
        (row as any).saldo_acumulado || ""
      ].join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `kardex_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Kardex de Inventario Profesional</CardTitle>
            <CardDescription>Filtros cruzados y seguimiento de saldos por bodega.</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClearFilters}>Limpiar</Button>
            <Button onClick={handleFetchKardex} disabled={isLoading}>
              {isLoading ? 'Consultando...' : 'Consultar'}
            </Button>
            <Button variant="secondary" onClick={exportToCSV} className="gap-2">
              <Download className="w-4 h-4" /> Exportar CSV
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Panel de Filtros */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Bodega</Label>
            <Select value={selectedBodega} onValueChange={setSelectedBodega}>
              <SelectTrigger className="bg-white">
                <SelectValue placeholder="Todas las bodegas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las Bodegas</SelectItem>
                {bodegas.map((b) => (
                  <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Producto</Label>
            <ProductSelect 
              productos={productos} 
              value={selectedProducto} 
              onValueChange={setSelectedProducto} 
              showAllOption={true}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Operación</Label>
            <Select value={tipoOperacion} onValueChange={setTipoOperacion}>
              <SelectTrigger className="bg-white">
                <SelectValue placeholder="Tipo de operación" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los movimientos</SelectItem>
                <SelectItem value="entrada">Entradas (Ingresos)</SelectItem>
                <SelectItem value="salida">Salidas (Egresos)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Desde</Label>
            <Input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} className="bg-white" />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Hasta</Label>
            <Input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} className="bg-white" />
          </div>
        </div>

        {/* Tabla de Resultados */}
        <div className="rounded-md border overflow-hidden">
          <Table>
            <TableHeader className="bg-slate-50">
              <TableRow>
                <TableHead className="w-[180px]">Fecha</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
                {selectedProducto !== 'all' && selectedBodega !== 'all' && (
                  <TableHead className="text-right font-bold text-primary">Saldo</TableHead>
                )}
                <TableHead>Referencia</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {kardexData.length > 0 ? (
                kardexData.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="text-xs">
                      {new Date(row.fecha).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{row.producto}</div>
                      <div className="text-[10px] text-muted-foreground">
                        {row.bodega_origen || 'Origen'} → {row.bodega_destino || 'Destino'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        (row as any).esEntrada ? 'bg-green-100 text-green-700' : 
                        (row as any).esSalida ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {row.tipo_movimiento}
                      </span>
                    </TableCell>
                    <TableCell className={`text-right font-mono ${(row as any).esEntrada ? 'text-green-600' : (row as any).esSalida ? 'text-red-600' : ''}`}>
                      {(row as any).esSalida ? `-${row.cantidad}` : `+${row.cantidad}`}
                    </TableCell>
                    {selectedProducto !== 'all' && selectedBodega !== 'all' && (
                      <TableCell className="text-right font-bold font-mono text-primary">
                        {(row as any).saldo_acumulado !== undefined ? Number((row as any).saldo_acumulado).toFixed(2) : '-'}
                      </TableCell>
                    )}
                    <TableCell className="max-w-[150px] truncate text-xs text-muted-foreground">
                      {row.documento_ref || '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8" 
                          onClick={() => {
                            setSelectedAuditId(row.id);
                            setShowAuditDialog(true);
                          }}
                        >
                          <ShieldCheck className="w-4 h-4 text-slate-500" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8"
                          onClick={() => setEditingMovimiento(row)}
                        >
                          <Edit2 className="w-4 h-4 text-slate-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={selectedProducto !== 'all' && selectedBodega !== 'all' ? 7 : 6} className="text-center py-10 text-muted-foreground">
                    {isLoading ? 'Cargando movimientos...' : 'No se encontraron movimientos con los filtros seleccionados.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>

      {/* Diálogos de Integración */}
      {editingMovimiento && (
        <EditarMovimientoDialog
          open={true}
          movimiento={editingMovimiento}
          onClose={() => setEditingMovimiento(null)}
          onSuccess={() => {
            setEditingMovimiento(null);
            handleFetchKardex();
            if (onDataRefresh) onDataRefresh();
          }}
        />
      )}

      {showAuditDialog && selectedAuditId && (
        <AuditoriaDialog
          open={true}
          movimientoId={selectedAuditId}
          onClose={() => {
            setShowAuditDialog(false);
            setSelectedAuditId(null);
          }}
        />
      )}
    </Card>
  );
};

// 5. ReportesView Component
const ReportesView = ({ bodegas, productos, sedeId }: { bodegas: Bodega[], productos: Producto[], sedeId?: string }) => {
  const [rkFechaInicio, setRkFechaInicio] = useState('');
  const [rkFechaFin, setRkFechaFin] = useState('');
  const [rkProducto, setRkProducto] = useState('');
  const [rkBodega, setRkBodega] = useState('');
  const [agingDias, setAgingDias] = useState('30');
  
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const downloadBlob = (data: Blob, headers: any, fallbackName: string) => {
    const disposition = headers['content-disposition'];
    let filename = fallbackName;
    if (disposition) {
      const match = disposition.match(/filename=([^;]+)/);
      if (match?.[1]) filename = match[1].trim().replace(/\"/g, '');
    }
    const url = URL.createObjectURL(data);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExport = async (reportType: string, params: any = {}) => {
    if (['kardex', 'stock-actual', 'valorizacion', 'aging', 'rotacion', 'resumen-movimientos'].includes(reportType) && !rkBodega) {
      toast.error('Debe seleccionar una bodega para este reporte.');
      return;
    }

    setLoading(prev => ({ ...prev, [reportType]: true }));
    try {
      const queryParams = { ...params, bodega_id: rkBodega };
      const endpoint = `/reporting/export/${reportType}`;
      
      const resp = await apiClient.get(endpoint, {
        params: queryParams,
        responseType: 'blob',
      });
      
      downloadBlob(resp.data, resp.headers, `${reportType}_report.xlsx`);
      toast.success('Reporte generado exitosamente.');
    } catch (e: any) {
      if (e.response?.status === 404) {
        toast.error('No se encontraron datos para los filtros seleccionados.');
      } else if (e.response?.status === 403) {
        toast.error('No tiene permisos para acceder a este reporte o bodega.');
      } else {
        toast.error('Error al generar el reporte. Intente de nuevo.');
      }
    } finally {
      setLoading(prev => ({ ...prev, [reportType]: false }));
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-10">
      {/* Selector de Bodega Global para reportes */}
      <Card className="xl:col-span-2 bg-muted/30 border-dashed">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-center gap-4">
            <div className="flex-1 w-full space-y-2">
              <Label className="text-primary font-bold">Bodega Principal para Reportes <span className="text-destructive">*</span></Label>
              <Select value={rkBodega} onValueChange={setRkBodega}>
                <SelectTrigger className="bg-background"><SelectValue placeholder="Selecciona una bodega para habilitar los reportes" /></SelectTrigger>
                <SelectContent>
                  {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {sedeId && (
              <Badge variant="outline" className="h-10 px-4 gap-2">
                <Warehouse className="w-4 h-4" />
                Sede ID: {sedeId}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 1. Kardex de Bodega */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg dark:bg-blue-900/30">
              <History className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <CardTitle>Kardex de Movimientos</CardTitle>
              <CardDescription>Movimientos detallados con saldo progresivo.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Producto (Opcional)</Label>
              <ProductSelect productos={productos} value={rkProducto} onValueChange={setRkProducto} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Desde</Label>
              <Input type="date" value={rkFechaInicio} onChange={e => setRkFechaInicio(e.target.value)} size={30} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hasta</Label>
              <Input type="date" value={rkFechaFin} onChange={e => setRkFechaFin(e.target.value)} />
            </div>
            <Button 
              className="mt-auto gap-2" 
              onClick={() => handleExport('kardex', { producto_id: rkProducto, fecha_inicio: rkFechaInicio, fecha_fin: rkFechaFin })}
              disabled={loading['kardex'] || !rkBodega}
            >
              <Download className="w-4 h-4" />
              {loading['kardex'] ? 'Generando...' : 'Exportar Kardex'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 2. Stock Actual */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-green-100 rounded-lg dark:bg-green-900/30">
              <Package className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <CardTitle>Snapshot de Stock Actual</CardTitle>
              <CardDescription>Resumen de existencias por lote en esta bodega.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Button 
            variant="outline" 
            className="w-full gap-2 border-green-200 hover:bg-green-50 dark:border-green-800"
            onClick={() => handleExport('stock-actual')}
            disabled={loading['stock-actual'] || !rkBodega}
          >
            <Download className="w-4 h-4" />
            {loading['stock-actual'] ? 'Descargando...' : 'Descargar Stock Actual'}
          </Button>
        </CardContent>
      </Card>

      {/* 3. Valorización */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-amber-100 rounded-lg dark:bg-amber-900/30">
              <span className="font-bold text-amber-600">$</span>
            </div>
            <div>
              <CardTitle>Valorización de Inventario</CardTitle>
              <CardDescription>Costo total del inventario (Stock × Precio Base).</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Button 
            variant="outline" 
            className="w-full gap-2 border-amber-200 hover:bg-amber-50 dark:border-amber-800"
            onClick={() => handleExport('valorizacion')}
            disabled={loading['valorizacion'] || !rkBodega}
          >
            <Download className="w-4 h-4" />
            {loading['valorizacion'] ? 'Calculando...' : 'Generar Reporte de Valorización'}
          </Button>
        </CardContent>
      </Card>

      {/* 4. Aging */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-purple-100 rounded-lg dark:bg-purple-900/30">
              <AlertCircle className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <CardTitle>Antigüedad de Stock (Aging)</CardTitle>
              <CardDescription>Identifica productos sin movimiento (Stock Muerto).</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <Label className="text-xs">Días mínimos de inactividad</Label>
              <Select value={agingDias} onValueChange={setAgingDias}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 días</SelectItem>
                  <SelectItem value="60">60 días</SelectItem>
                  <SelectItem value="90">90 días</SelectItem>
                  <SelectItem value="180">180 días (Crítico)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button 
              className="mt-auto gap-2" 
              variant="outline"
              onClick={() => handleExport('aging', { dias: agingDias })}
              disabled={loading['aging'] || !rkBodega}
            >
              <Download className="w-4 h-4" />
              {loading['aging'] ? 'Analizando...' : 'Exportar Aging'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 5. Rotación y Resumen */}
      <Card className={!rkBodega ? "opacity-60" : "xl:col-span-2"}>
        <CardHeader>
          <CardTitle>Análisis de Movimientos y Rotación</CardTitle>
          <CardDescription>Compara entradas vs salidas y mide la velocidad del inventario en un período.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
             <div className="space-y-1">
                <Label className="text-xs">Fecha Inicio (Requerido)</Label>
                <Input type="date" value={rkFechaInicio} onChange={e => setRkFechaInicio(e.target.value)} />
             </div>
             <div className="space-y-1">
                <Label className="text-xs">Fecha Fin (Requerido)</Label>
                <Input type="date" value={rkFechaFin} onChange={e => setRkFechaFin(e.target.value)} />
             </div>
             <div className="flex gap-2">
                <Button 
                  className="flex-1 gap-1" 
                  variant="secondary"
                  onClick={() => handleExport('rotacion', { fecha_inicio: rkFechaInicio, fecha_fin: rkFechaFin })}
                  disabled={loading['rotacion'] || !rkBodega || !rkFechaInicio || !rkFechaFin}
                >
                  <Download className="w-3 h-3" />
                  Rotación
                </Button>
                <Button 
                  className="flex-1 gap-1" 
                  variant="secondary"
                  onClick={() => handleExport('resumen-movimientos', { fecha_inicio: rkFechaInicio, fecha_fin: rkFechaFin })}
                  disabled={loading['resumen-movimientos'] || !rkBodega || !rkFechaInicio || !rkFechaFin}
                >
                  <Download className="w-3 h-3" />
                  Resumen
                </Button>
             </div>
          </div>
        </CardContent>
      </Card>

      {/* Catálogo de Productos */}
      <Card className="xl:col-span-2 border-primary/20 bg-primary/5">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-base">Catálogo maestro de Productos</CardTitle>
            <CardDescription>Base de datos completa de productos y códigos.</CardDescription>
          </div>
          <Button variant="ghost" onClick={() => handleExport('productos')} disabled={loading['productos']} className="gap-2">
            <Download className="w-4 h-4" />
            {loading['productos'] ? 'Exportando...' : 'Descargar Catálogo'}
          </Button>
        </CardHeader>
      </Card>
    </div>
  );
};

// MAIN DASHBOARD
export function InventoryDashboard({ sedeId, productos, bodegas, lotesProduccion, onDataRefresh, proveedores }: { sedeId?: string, productos: Producto[], bodegas: Bodega[], lotesProduccion: LoteProduccion[], proveedores: Proveedor[], onDataRefresh: () => void }) {
  const [stock, setStock] = useState<StockItem[]>([]);
  const [loadingStock, setLoadingStock] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();

  const fetchStock = async () => {
    setLoadingStock(true);
    try {
      const response = await apiClient.get<any>('/inventory/stock/', { params: sedeId ? { sede_id: sedeId } : {} });
      const data = response.data;
      if (data && typeof data === 'object' && Array.isArray(data.results)) {
        setStock(data.results);
      } else if (Array.isArray(data)) {
        setStock(data);
      } else {
        setStock([]);
      }
    } catch (error) {
      toast.error('Error stock');
      setStock([]);
    } finally {
      setLoadingStock(false);
    }
  };

  useEffect(() => { fetchStock(); }, [sedeId]);

  return (
    <Tabs
      defaultValue="stock"
      onValueChange={() => {
        setSearchParams(prev => {
          prev.set('page', '1');
          return prev;
        }, { replace: true });
      }}
      className="space-y-4"
    >
      <TabsList className="grid w-full grid-cols-6">
        <TabsTrigger value="stock"><Package className="w-4 h-4 mr-2" />Stock</TabsTrigger>
        <TabsTrigger value="entrada"><LogIn className="w-4 h-4 mr-2" />Entrada</TabsTrigger>
        <TabsTrigger value="transfer"><Send className="w-4 h-4 mr-2" />Transfer</TabsTrigger>
        <TabsTrigger value="transform"><Share2 className="w-4 h-4 mr-2" />Transform</TabsTrigger>
        <TabsTrigger value="kardex"><History className="w-4 h-4 mr-2" />Kardex</TabsTrigger>
        <TabsTrigger value="reportes"><FileText className="w-4 h-4 mr-2" />Reportes</TabsTrigger>
      </TabsList>
      <TabsContent value="stock"><StockView stock={stock} loading={loadingStock} /></TabsContent>
      <TabsContent value="entrada"><RegistrarEntradaView productos={productos} bodegas={bodegas} proveedores={proveedores} onDataRefresh={fetchStock} /></TabsContent>
      <TabsContent value="transfer"><TransferView productos={productos} bodegas={bodegas} lotesProduccion={lotesProduccion} /></TabsContent>
      <TabsContent value="transform"><TransformationView productos={productos} bodegas={bodegas} lotesProduccion={lotesProduccion} /></TabsContent>
      <TabsContent value="kardex"><KardexView productos={productos} bodegas={bodegas} proveedores={proveedores} onDataRefresh={onDataRefresh} /></TabsContent>
      <TabsContent value="reportes"><ReportesView bodegas={bodegas} productos={productos} sedeId={sedeId} /></TabsContent>
    </Tabs>
  );
}