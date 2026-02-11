import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { PackageCheck, Truck, Loader2, Search, CheckCircle2 } from 'lucide-react';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { PedidoVenta } from '../../lib/types';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

export function DespachoDashboard() {
    const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState<number | null>(null);
    const [searchTerm, setSearchTerm] = useState("");

    useEffect(() => {
        fetchPedidos();
    }, []);

    const fetchPedidos = async () => {
        try {
            setIsLoading(true);
            // Fetch pending orders (estado=pendiente)
            const response = await apiClient.get<PedidoVenta[]>('/pedidos-venta/?estado=pendiente&limit=50');
            setPedidos(response.data);
        } catch (error) {
            console.error("Error fetching orders", error);
            toast.error("Error al cargar pedidos pendientes");
        } finally {
            setIsLoading(false);
        }
    };

    const handleDespacho = async (pedidoId: number) => {
        setIsSubmitting(pedidoId);
        try {
            // Update order status to 'despachado'
            await apiClient.patch(`/pedidos-venta/${pedidoId}/`, {
                estado: 'despachado',
                fecha_despacho: new Date().toISOString().split('T')[0]
            });

            toast.success(`Pedido #${pedidoId} despachado correctamente`);

            // Refresh list
            setPedidos(prev => prev.filter(p => p.id !== pedidoId));
        } catch (error) {
            console.error("Error updating order", error);
            toast.error("Error al procesar el despacho");
        } finally {
            setIsSubmitting(null);
        }
    };

    const filteredPedidos = pedidos.filter(p =>
        p.cliente_nombre?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.guia_remision?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.id.toString().includes(searchTerm)
    );

    if (isLoading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;

    return (
        <div className="space-y-6 p-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Panel de Despacho</h1>
                    <p className="text-muted-foreground">Gestión de salida de pedidos y confirmación de guías.</p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <CardTitle>Pedidos Pendientes por Despachar</CardTitle>
                            <CardDescription>Lista de pedidos listos para salir de bodega.</CardDescription>
                        </div>
                        <div className="relative w-full md:w-72">
                            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Buscar cliente o guía..."
                                className="pl-8"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>ID Pedido</TableHead>
                                <TableHead>Fecha Pedido</TableHead>
                                <TableHead>Cliente</TableHead>
                                <TableHead>Guía Remisión</TableHead>
                                <TableHead>Estado Pago</TableHead>
                                <TableHead className="text-right">Acción</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredPedidos.map(pedido => (
                                <TableRow key={pedido.id}>
                                    <TableCell className="font-medium">#{pedido.id}</TableCell>
                                    <TableCell>
                                        {pedido.fecha_pedido ? format(new Date(pedido.fecha_pedido), 'dd MMM, yyyy', { locale: es }) : 'N/A'}
                                    </TableCell>
                                    <TableCell>{pedido.cliente_nombre}</TableCell>
                                    <TableCell>
                                        <Badge variant="outline" className="font-mono">
                                            {pedido.guia_remision}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        {pedido.esta_pagado ? (
                                            <Badge className="bg-green-100 text-green-800 border-green-200">Pagado</Badge>
                                        ) : (
                                            <Badge variant="secondary">Crédito / Pendiente</Badge>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <Button
                                            size="sm"
                                            onClick={() => handleDespacho(pedido.id)}
                                            disabled={isSubmitting === pedido.id}
                                        >
                                            {isSubmitting === pedido.id ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <>
                                                    <Truck className="mr-2 h-4 w-4" />
                                                    Despachar
                                                </>
                                            )}
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                            {filteredPedidos.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                                        <PackageCheck className="mx-auto h-12 w-12 opacity-20 mb-2" />
                                        No se encontraron pedidos pendientes.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-primary/5 border-primary/20">
                    <CardHeader className="pb-2">
                        <CardDescription>Pedidos Hoy</CardDescription>
                        <CardTitle className="text-2xl">{pedidos.length}</CardTitle>
                    </CardHeader>
                </Card>
                <Card className="bg-orange-500/5 border-orange-500/20">
                    <CardHeader className="pb-2">
                        <CardDescription>Por Facturar</CardDescription>
                        <CardTitle className="text-2xl">
                            {pedidos.filter(p => !p.esta_pagado).length}
                        </CardTitle>
                    </CardHeader>
                </Card>
                <Card className="bg-green-500/5 border-green-500/20">
                    <CardHeader className="pb-2">
                        <CardDescription>Completados</CardDescription>
                        <CardTitle className="text-2xl flex items-center gap-2">
                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                            Ver historial
                        </CardTitle>
                    </CardHeader>
                </Card>
            </div>
        </div>
    );
}
