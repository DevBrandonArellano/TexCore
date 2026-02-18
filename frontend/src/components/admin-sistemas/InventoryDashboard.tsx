import React, { useState, useEffect, useMemo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Package, Send, History, ChevronLeft, ChevronRight, LogIn, Share2 } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Producto, Bodega, LoteProduccion } from '../../lib/types';
import { TransformationView } from './TransformationView';
import { EditarMovimientoDialog } from '../bodeguero/EditarMovimientoDialog';
import { AuditoriaDialog } from '../bodeguero/AuditoriaDialog';
import { Edit2, FileText, AlertCircle } from 'lucide-react';
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
      <CardContent>
        <Table>
          <TableHeader>
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
        <div className="flex items-center justify-between mt-4">
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
const RegistrarEntradaView = ({ productos, bodegas, onDataRefresh }: { productos: Producto[], bodegas: Bodega[], onDataRefresh: () => void }) => {
  const [formData, setFormData] = useState({ producto_id: '', bodega_destino_id: '', cantidad: '', documento_ref: '', lote_codigo: '' });
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
      });
      toast.success("Entrada de materia prima registrada con éxito.");
      onDataRefresh();
      setFormData({ producto_id: '', bodega_destino_id: '', cantidad: '', documento_ref: '', lote_codigo: '' });
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
              <Select value={formData.producto_id} onValueChange={v => setFormData(f => ({ ...f, producto_id: v }))}><SelectTrigger id="entrada-producto"><SelectValue placeholder="Selecciona un producto" /></SelectTrigger><SelectContent>{productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)}</SelectContent></Select>
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
      };
      await apiClient.post('/inventory/transferencias/', payload);
      toast.success('Transferencia realizada con éxito');
      setFormData({
        producto_id: '',
        bodega_origen_id: '',
        bodega_destino_id: '',
        cantidad: '',
        lote_id: '',
      });
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Ocurrió un error inesperado.';
      toast.error('Error en la transferencia', { description: errorMsg });
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
              <Select value={formData.producto_id} onValueChange={(value) => setFormData(prev => ({ ...prev, producto_id: value, lote_id: '' }))}>
                <SelectTrigger id="producto_id"><SelectValue placeholder="Selecciona un producto" /></SelectTrigger>
                <SelectContent>{productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)}</SelectContent>
              </Select>
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
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Transfiriendo...' : 'Realizar Transferencia'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

const KardexView = ({ productos, bodegas }: { productos: Producto[], bodegas: Bodega[] }) => {
  const [selectedBodega, setSelectedBodega] = useState('');
  const [selectedProducto, setSelectedProducto] = useState('');
  const [kardexData, setKardexData] = useState<any[]>([]);
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
        params: { producto_id: selectedProducto },
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Consultar Kardex</CardTitle>
        <CardDescription>Consulta el historial de movimientos de un producto en una bodega.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="space-y-2">
            <Label htmlFor="kardex-bodega">Bodega</Label>
            <Select value={selectedBodega} onValueChange={setSelectedBodega}>
              <SelectTrigger id="kardex-bodega"><SelectValue placeholder="Selecciona una bodega" /></SelectTrigger>
              <SelectContent>{bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="kardex-producto">Producto</Label>
            <Select value={selectedProducto} onValueChange={setSelectedProducto}>
              <SelectTrigger id="kardex-producto"><SelectValue placeholder="Selecciona un producto" /></SelectTrigger>
              <SelectContent>{productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <Button onClick={handleFetchKardex} disabled={isLoading}>
            {isLoading ? 'Consultando...' : 'Consultar'}
          </Button>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Tipo de Movimiento</TableHead>
              <TableHead>Ref.</TableHead>
              <TableHead className="text-right">Entrada</TableHead>
              <TableHead className="text-right">Salida</TableHead>
              <TableHead className="text-right">Saldo</TableHead>
              <TableHead className="text-center">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={7} className="text-center">Cargando...</TableCell></TableRow>
            ) : kardexData.length > 0 ? (
              kardexData.map((row, index) => (
                <TableRow key={index} className={row.editado ? "bg-amber-50/30" : ""}>
                  <TableCell>
                    <div className="flex flex-col">
                      <span>{new Date(row.fecha).toLocaleString()}</span>
                      {row.editado && (
                        <Badge variant="outline" className="w-fit mt-1 text-[0.6rem] h-4 px-1 gap-1 border-amber-200 text-amber-700">
                          <AlertCircle className="w-2 h-2" />
                          Editado
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{row.tipo_movimiento}</TableCell>
                  <TableCell>
                    {row.documento_ref || '-'}
                  </TableCell>
                  <TableCell className="text-right text-green-600 font-mono">
                    {row.entrada ? Number(row.entrada).toFixed(2) : '-'}
                  </TableCell>
                  <TableCell className="text-right text-red-600 font-mono">
                    {row.salida ? Number(row.salida).toFixed(2) : '-'}
                  </TableCell>
                  <TableCell className="text-right font-medium font-mono">
                    {Number(row.saldo_resultante).toFixed(2)}
                  </TableCell>
                  <TableCell className="text-center">
                    <TooltipProvider>
                      <div className="flex items-center justify-center gap-2">
                        {/* Botón Editar: Solo para Entradas (COMPRA) aprobadas */}
                        {row.tipo_movimiento === 'Compra de Material' && row.estado === 'APROBADO' && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => handleEditClick(row)}
                              >
                                <Edit2 className="h-4 w-4 text-blue-600" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Editar entrada</TooltipContent>
                          </Tooltip>
                        )}

                        {/* Botón Auditoría: Visible si ha sido editado */}
                        {(row.editado || row.has_audit) && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => handleAuditClick(row.id || row.movimiento_id)}
                              >
                                <FileText className="h-4 w-4 text-amber-600" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Ver historial de cambios</TooltipContent>
                          </Tooltip>
                        )}
                      </div>
                    </TooltipProvider>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow><TableCell colSpan={7} className="text-center">Selecciona y consulta para ver datos.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>

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


// 3. Main InventoryDashboard Component (Container)
interface InventoryDashboardProps {

  productos: Producto[];
  bodegas: Bodega[];
  lotesProduccion: LoteProduccion[];
  onDataRefresh: () => void;
}


export function InventoryDashboard({ productos, bodegas, lotesProduccion, onDataRefresh }: InventoryDashboardProps) {
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
      <TabsList className="grid w-full grid-cols-5">
        <TabsTrigger value="stock"><Package className="w-4 h-4 mr-2" />Stock Actual</TabsTrigger>
        <TabsTrigger value="entrada"><LogIn className="w-4 h-4 mr-2" />Entrada</TabsTrigger>
        <TabsTrigger value="transfer"><Send className="w-4 h-4 mr-2" />Transferencias</TabsTrigger>
        <TabsTrigger value="transform"><Share2 className="w-4 h-4 mr-2" />Transformación</TabsTrigger>
        <TabsTrigger value="kardex"><History className="w-4 h-4 mr-2" />Kardex</TabsTrigger>
      </TabsList>

      <TabsContent value="stock">
        <StockView stock={stock} loading={loadingStock} />
      </TabsContent>

      <TabsContent value="entrada">
        <RegistrarEntradaView productos={productos} bodegas={bodegas} onDataRefresh={handleRefresh} />
      </TabsContent>

      <TabsContent value="transfer">
        <TransferView productos={productos} bodegas={bodegas} lotesProduccion={lotesProduccion} />
      </TabsContent>

      <TabsContent value="transform">
        <TransformationView productos={productos} bodegas={bodegas} lotesProduccion={lotesProduccion} />
      </TabsContent>

      <TabsContent value="kardex">
        <KardexView productos={productos} bodegas={bodegas} />
      </TabsContent>
    </Tabs>
  );
}