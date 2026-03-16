import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Loader2, Search, Calendar, ChevronLeft, ChevronRight, Eye, Package } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';

// Interfaces basadas en los serializers del backend
interface DetalleHistorial {
    id: number;
    codigo_lote: string;
    producto_nombre: string;
    peso: string;
    es_devolucion: boolean;
}

interface PedidoDetalle {
    id: number;
    guia_remision: string;
    cliente_nombre: string;
    cantidad_despachada: string;
}

interface HistorialDespacho {
    id: number;
    fecha_despacho: string;
    usuario_nombre: string;
    total_bultos: number;
    total_peso: string;
    observaciones: string;
    pedidos_detalle: PedidoDetalle[];
    detalles: DetalleHistorial[];
}

interface PaginatedResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: HistorialDespacho[];
}

export function HistorialDespachos() {
    const [searchParams, setSearchParams] = useSearchParams();
    
    // Estado UI manejado por URL (Navegación Híbrida)
    const page = parseInt(searchParams.get('page') || '1', 10);
    const fechaDesde = searchParams.get('fecha_desde') || '';
    const fechaHasta = searchParams.get('fecha_hasta') || '';
    
    // Estado local
    const [data, setData] = useState<PaginatedResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDespacho, setSelectedDespacho] = useState<HistorialDespacho | null>(null);
    
    // Inputs locales para filtros de fecha antes de aplicar a URL
    const [localFechaDesde, setLocalFechaDesde] = useState(fechaDesde);
    const [localFechaHasta, setLocalFechaHasta] = useState(fechaHasta);

    useEffect(() => {
        fetchHistorial();
    }, [page, fechaDesde, fechaHasta]); // Dependencias a la URL

    const fetchHistorial = async () => {
        setIsLoading(true);
        try {
            // Construir params para axios
            const params = new URLSearchParams();
            params.append('page', page.toString());
            if (fechaDesde) params.append('fecha_desde', fechaDesde);
            if (fechaHasta) params.append('fecha_hasta', fechaHasta);
            
            const response = await apiClient.get<PaginatedResponse>(`/inventory/historial-despachos/?${params.toString()}`);
            setData(response.data);
        } catch (error) {
            console.error("Error fetching historial", error);
            toast.error("Error al cargar el historial de despachos");
        } finally {
            setIsLoading(false);
        }
    };

    const handleApplyFilters = () => {
        setSearchParams(prev => {
            if (localFechaDesde) {
                prev.set('fecha_desde', localFechaDesde);
            } else {
                prev.delete('fecha_desde');
            }
            
            if (localFechaHasta) {
                prev.set('fecha_hasta', localFechaHasta);
            } else {
                prev.delete('fecha_hasta');
            }
            
            prev.set('page', '1'); // Reset to page 1 on filter
            return prev;
        }, { replace: true });
    };

    const handleClearFilters = () => {
        setLocalFechaDesde('');
        setLocalFechaHasta('');
        
        setSearchParams(prev => {
            prev.delete('fecha_desde');
            prev.delete('fecha_hasta');
            prev.set('page', '1');
            return prev;
        }, { replace: true });
    };

    const changePage = (newPage: number) => {
        if (newPage < 1) return;
        setSearchParams(prev => {
            prev.set('page', newPage.toString());
            return prev;
        });
    };

    return (
        <div className="space-y-6 p-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Historial de Despachos</h1>
                    <p className="text-muted-foreground">Consulta los registros de mercadería despachada.</p>
                </div>
            </div>

            <Card>
                <CardHeader className="pb-3 border-b">
                    <div className="flex flex-col sm:flex-row items-end gap-4">
                        <div className="space-y-1 w-full sm:w-auto">
                            <label className="text-sm font-medium">Desde</label>
                            <div className="relative">
                                <Calendar className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                <Input 
                                    type="date" 
                                    className="pl-9" 
                                    value={localFechaDesde}
                                    onChange={(e) => setLocalFechaDesde(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="space-y-1 w-full sm:w-auto">
                            <label className="text-sm font-medium">Hasta</label>
                            <div className="relative">
                                <Calendar className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                <Input 
                                    type="date" 
                                    className="pl-9" 
                                    value={localFechaHasta}
                                    onChange={(e) => setLocalFechaHasta(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="flex gap-2 w-full sm:w-auto mt-4 sm:mt-0">
                            <Button onClick={handleApplyFilters} className="bg-primary group transition-all">
                                <Search className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" /> Buscar
                            </Button>
                            {(fechaDesde || fechaHasta) && (
                                <Button variant="outline" onClick={handleClearFilters}>
                                    Limpiar
                                </Button>
                            )}
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="pl-6">ID</TableHead>
                                <TableHead>Fecha</TableHead>
                                <TableHead>Responsable</TableHead>
                                <TableHead>Pedidos / Clientes</TableHead>
                                <TableHead className="text-right">Bultos</TableHead>
                                <TableHead className="text-right">Peso Total</TableHead>
                                <TableHead className="text-center">Detalles</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="h-24 text-center">
                                        <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                                    </TableCell>
                                </TableRow>
                            ) : data?.results.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                                        No se encontraron despachos para los filtros actuales.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                data?.results.map((item) => (
                                    <TableRow key={item.id} className="group hover:bg-slate-50 transition-colors">
                                        <TableCell className="pl-6 font-medium text-slate-700">#{item.id}</TableCell>
                                        <TableCell>
                                            <div className="flex flex-col">
                                                <span>{format(new Date(item.fecha_despacho), 'dd MMM yyyy', { locale: es })}</span>
                                                <span className="text-xs text-muted-foreground">
                                                    {format(new Date(item.fecha_despacho), 'HH:mm')}
                                                </span>
                                            </div>
                                        </TableCell>
                                        <TableCell>{item.usuario_nombre}</TableCell>
                                        <TableCell>
                                            {item.pedidos_detalle.length === 1 ? (
                                                <div className="flex flex-col">
                                                    <span className="font-semibold">{item.pedidos_detalle[0].cliente_nombre}</span>
                                                    <span className="text-xs text-muted-foreground">Guía: {item.pedidos_detalle[0].guia_remision}</span>
                                                </div>
                                            ) : (
                                                <Badge variant="secondary" className="px-2 py-1">
                                                    {item.pedidos_detalle.length} Pedidos Múltiples
                                                </Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">{item.total_bultos}</TableCell>
                                        <TableCell className="text-right font-mono font-bold bg-slate-50/50">
                                            {parseFloat(item.total_peso).toFixed(2)} kg
                                        </TableCell>
                                        <TableCell className="text-center pr-4">
                                            <Button 
                                                variant="ghost" 
                                                size="sm" 
                                                className="opacity-60 group-hover:opacity-100 transition-opacity"
                                                onClick={() => setSelectedDespacho(item)}
                                            >
                                                <Eye className="w-4 h-4 mr-2" />
                                                Ver
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>

                    {/* Pagination Controls */}
                    {data && data.count > 0 && (
                        <div className="flex items-center justify-between px-6 py-4 border-t">
                            <span className="text-sm text-muted-foreground">
                                Mostrando página <span className="font-medium text-slate-900">{page}</span> 
                                {/* Assuming standard limit calculation if needed, else simple display */}
                            </span>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={!data.previous}
                                    onClick={() => changePage(page - 1)}
                                >
                                    <ChevronLeft className="h-4 w-4" /> Anterior
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={!data.next}
                                    onClick={() => changePage(page + 1)}
                                >
                                    Siguiente <ChevronRight className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Modal de Detalles del Despacho */}
            <Dialog open={!!selectedDespacho} onOpenChange={(open) => !open && setSelectedDespacho(null)}>
                <DialogContent className="max-w-3xl">
                    <DialogHeader>
                        <DialogTitle className="text-xl flex items-center gap-2">
                            <Package className="w-5 h-5 text-primary" />
                            Detalle de Despacho #{selectedDespacho?.id}
                        </DialogTitle>
                        <DialogDescription>
                            Fecha: {selectedDespacho && format(new Date(selectedDespacho.fecha_despacho), 'dd MMMM yyyy HH:mm', { locale: es })}
                            <br />
                            Responsable: <span className="font-medium text-slate-900">{selectedDespacho?.usuario_nombre}</span>
                        </DialogDescription>
                    </DialogHeader>

                    {selectedDespacho && (
                        <div className="space-y-6">
                            {/* Summary Cards */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <Card className="bg-slate-50 border-none shadow-none">
                                    <CardContent className="p-4 flex flex-col items-center justify-center">
                                        <span className="text-sm text-muted-foreground">Pedidos Totales</span>
                                        <span className="text-2xl font-bold">{selectedDespacho.pedidos_detalle.length}</span>
                                    </CardContent>
                                </Card>
                                <Card className="bg-slate-50 border-none shadow-none">
                                    <CardContent className="p-4 flex flex-col items-center justify-center">
                                        <span className="text-sm text-muted-foreground">Bultos Totales</span>
                                        <span className="text-2xl font-bold">{selectedDespacho.total_bultos}</span>
                                    </CardContent>
                                </Card>
                                <Card className="bg-slate-50 border-none shadow-none md:col-span-2">
                                    <CardContent className="p-4 flex flex-col items-center justify-center">
                                        <span className="text-sm text-muted-foreground">Peso Total Despachado</span>
                                        <span className="text-2xl font-mono font-bold text-primary">{parseFloat(selectedDespacho.total_peso).toFixed(2)} kg</span>
                                    </CardContent>
                                </Card>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Pedidos List */}
                                <div className="space-y-3">
                                    <h3 className="font-medium text-sm text-slate-500 uppercase flex items-center gap-2 border-b pb-1">
                                        Pedidos Abarcados
                                    </h3>
                                    <div className="space-y-2">
                                        {selectedDespacho.pedidos_detalle.map(p => (
                                            <div key={p.id} className="flex justify-between items-center bg-white border p-3 rounded-md shadow-sm">
                                                <div className="flex flex-col">
                                                    <span className="font-semibold text-sm">{p.cliente_nombre}</span>
                                                    <span className="text-xs text-muted-foreground font-mono">Guía: {p.guia_remision}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Lotes List */}
                                <div className="space-y-3">
                                    <h3 className="font-medium text-sm text-slate-500 uppercase flex items-center gap-2 border-b pb-1">
                                        Lotes Escaneados
                                    </h3>
                                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
                                        {selectedDespacho.detalles.map(d => (
                                            <div key={d.id} className="flex justify-between items-center bg-white border p-3 rounded-md shadow-sm hover:border-slate-300 transition-colors">
                                                <div className="flex flex-col">
                                                    <span className="text-xs truncate max-w-[200px]" title={d.producto_nombre}>{d.producto_nombre}</span>
                                                    <span className="font-mono text-sm font-semibold">{d.codigo_lote}</span>
                                                </div>
                                                <div className="flex flex-col items-end">
                                                    <span className="font-bold text-sm bg-slate-100 px-2 py-0.5 rounded text-slate-700">
                                                        {parseFloat(d.peso).toFixed(2)} kg
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
