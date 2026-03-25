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
import { ProductSelect } from '../ui/product-select';
import { Package, ChevronLeft, ChevronRight, LogIn, Send, Share2, History, FileText, ShieldCheck, Download, Edit2, AlertCircle } from 'lucide-react';
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
      
      let data = response.data;

      // Cálculo de Saldo Dinámico si hay Producto + Bodega seleccionado
      if (selectedProducto !== 'all' && selectedBodega !== 'all') {
        // Ordenar por fecha ascendente para calcular saldo
        data.sort((a: any, b: any) => new Date(a.fecha).getTime() - new Date(b.fecha).getTime());
        
        let saldoAcumulado = 0;
        data = data.map((mov: any) => {
          const cant = parseFloat(mov.cantidad);
          if (mov.tipo_movimiento.includes('ENTRADA') || mov.tipo_movimiento === 'COMPRA' || mov.tipo_movimiento === 'PRODUCCION' || (mov.bodega_destino && mov.bodega_destino.id?.toString() === selectedBodega)) {
             // Es una entrada a esta bodega
             // Nota: La lógica de 'tipo' en la API puede variar, ajustamos según el flujo
             // Si es transferencia y el destino es la bodega seleccionada, suma.
             // Pero /inventory/movimientos/ suele traer registros individuales.
          }
          
          // Lógica simplificada: si la cantidad es positiva es entrada, negativa salida? 
          // O usamos el tipo. Por ahora, asumamos que la API devuelve 'cantidad' como impacto neto si es Kardex, 
          // o calculamos basado en si la bodega_destino es la seleccionada.
          
          // Ajuste para el cálculo de saldo basado en la estructura de Movimiento
          const esEntrada = (mov.bodega_destino?.id?.toString() === selectedBodega);
          const esSalida = (mov.bodega_origen?.id?.toString() === selectedBodega);
          
          if (esEntrada) saldoAcumulado += cant;
          if (esSalida) saldoAcumulado -= cant;

          return { ...mov, saldo_acumulado: saldoAcumulado, esEntrada, esSalida };
        });
        
        // Volver a ordenar descendente para mostrar lo más reciente arriba si se desea, 
        // pero el saldo se calculó ascendente.
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
              value={selectedProducto === 'all' ? '' : selectedProducto} 
              onValueChange={(v) => setSelectedProducto(v || 'all')} 
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
                        {(row as any).saldo_acumulado.toFixed(2)}
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
  const [rkFechaCorte, setRkFechaCorte] = useState('');
  const [rkProducto, setRkProducto] = useState('');
  const [rkData, setRkData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchRetroKardex = async () => {
    if (!rkProducto || !rkFechaCorte) return;
    setLoading(true);
    try {
      const resp = await apiClient.get('/inventory/retro-kardex/', { params: { producto_id: rkProducto, fecha_corte: rkFechaCorte, sede_id: sedeId || undefined } });
      setRkData(resp.data);
    } catch (e) {
      toast.error('Error reportes');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader><CardTitle>Retro-Kardex (Stock a Fecha)</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="space-y-2">
            <Label>Producto</Label>
            <ProductSelect productos={productos} value={rkProducto} onValueChange={setRkProducto} />
          </div>
          <div className="space-y-2">
            <Label>Fecha Corte</Label>
            <Input type="date" value={rkFechaCorte} onChange={e => setRkFechaCorte(e.target.value)} />
          </div>
          <Button onClick={fetchRetroKardex} disabled={loading}>Generar</Button>
        </div>
        <Table className="text-xs">
          <TableHeader><TableRow><TableHead>Bodega</TableHead><TableHead className="text-right">Stock</TableHead></TableRow></TableHeader>
          <TableBody>
            {rkData.map((row, i) => (
              <TableRow key={i}><TableCell>{row.bodega}</TableCell><TableCell className="text-right font-bold">{row.stock_calculado}</TableCell></TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

// MAIN DASHBOARD
export function InventoryDashboard({ sedeId, productos, bodegas, lotesProduccion, onDataRefresh, proveedores }: { sedeId?: string, productos: Producto[], bodegas: Bodega[], lotesProduccion: LoteProduccion[], proveedores: Proveedor[], onDataRefresh: () => void }) {
  const [stock, setStock] = useState<StockItem[]>([]);
  const [loadingStock, setLoadingStock] = useState(true);

  const fetchStock = async () => {
    setLoadingStock(true);
    try {
      const response = await apiClient.get<StockItem[]>('/inventory/stock/', { params: sedeId ? { sede_id: sedeId } : {} });
      setStock(response.data);
    } catch (error) {
      toast.error('Error stock');
    } finally {
      setLoadingStock(false);
    }
  };

  useEffect(() => { fetchStock(); }, [sedeId]);

  return (
    <Tabs defaultValue="stock" className="space-y-4">
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