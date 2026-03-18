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
const KardexView = ({ productos, bodegas, proveedores }: { productos: Producto[], bodegas: Bodega[], proveedores: Proveedor[] }) => {
  const [selectedBodega, setSelectedBodega] = useState('');
  const [selectedProducto, setSelectedProducto] = useState('');
  const [selectedProveedor, setSelectedProveedor] = useState('all');
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [loteCodigo, setLoteCodigo] = useState('');
  const [kardexData, setKardexData] = useState<Movimiento[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingMovimiento, setEditingMovimiento] = useState<any | null>(null);
  const [showAuditDialog, setShowAuditDialog] = useState(false);
  const [selectedAuditId, setSelectedAuditId] = useState<number | null>(null);

  const handleFetchKardex = async () => {
    if (!selectedBodega || !selectedProducto) {
      toast.info('Selecciona bodega y producto.');
      return;
    }
    setIsLoading(true);
    try {
      const response = await apiClient.get(`/inventory/bodegas/${selectedBodega}/kardex/`, {
        params: { producto_id: selectedProducto, proveedor_id: selectedProveedor !== 'all' ? selectedProveedor : undefined, fecha_inicio: fechaInicio, fecha_fin: fechaFin, lote_codigo: loteCodigo },
      });
      setKardexData(response.data);
    } catch (error) {
      toast.error('Error al consultar Kardex.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportKardex = async () => {
    if (!selectedBodega) {
      toast.info('Selecciona una bodega.');
      return;
    }
    // Si no hay producto, exportamos el stock general
    const esReporteGeneral = !selectedProducto;

    try {
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
    <Card>
      <CardHeader>
        <CardTitle>Consulta de Kardex</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end bg-slate-50 p-4 rounded-lg">
          <div className="space-y-2">
            <Label>Bodega</Label>
            <Select value={selectedBodega} onValueChange={setSelectedBodega}>
              <SelectTrigger>
                <SelectValue placeholder="Bodega" />
              </SelectTrigger>
              <SelectContent>
                {bodegas.map((b) => (
                  <SelectItem key={b.id} value={b.id.toString()}>
                    {b.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Producto</Label>
            <ProductSelect 
              productos={productos} 
              value={selectedProducto} 
              onValueChange={setSelectedProducto} 
            />
          </div>
          <div className="space-y-2">
            <Label>Desde</Label>
            <Input 
              type="date" 
              value={fechaInicio} 
              onChange={(e) => setFechaInicio(e.target.value)} 
            />
          </div>
          <div className="space-y-2">
            <Label>Hasta</Label>
            <Input 
              type="date" 
              value={fechaFin} 
              onChange={(e) => setFechaFin(e.target.value)} 
            />
          </div>
          <Button onClick={handleFetchKardex} disabled={isLoading}>
            {isLoading ? 'Cargando...' : 'Consultar'}
          </Button>
          <Button 
            onClick={handleExportKardex} 
            variant="outline" 
            className="text-green-700 border-green-200"
          >
            Excel
          </Button>
        </div>

        <div className="overflow-auto border rounded-lg">
          <Table className="text-xs">
            <TableHeader className="bg-slate-100">
              <TableRow>
                <TableHead>Fecha</TableHead>
                <TableHead>Operación</TableHead>
                <TableHead>Lote</TableHead>
                <TableHead className="text-right">Entrada</TableHead>
                <TableHead className="text-right">Salida</TableHead>
                <TableHead className="text-right font-bold">Saldo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {kardexData.map((row, i) => (
                <TableRow key={i}>
                  <TableCell>
                    {row.fecha ? new Date(row.fecha).toLocaleString() : '-'}
                  </TableCell>
                  <TableCell>{row.tipo_movimiento}</TableCell>
                  <TableCell>{row.lote || '-'}</TableCell>
                  <TableCell className="text-right text-green-700">
                    {row.entrada || ''}
                  </TableCell>
                  <TableCell className="text-right text-red-600">
                    {row.salida || ''}
                  </TableCell>
                  <TableCell className="text-right font-bold">
                    {row.saldo_resultante}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
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
      <TabsContent value="kardex"><KardexView productos={productos} bodegas={bodegas} proveedores={proveedores} /></TabsContent>
      <TabsContent value="reportes"><ReportesView bodegas={bodegas} productos={productos} sedeId={sedeId} /></TabsContent>
    </Tabs>
  );
}