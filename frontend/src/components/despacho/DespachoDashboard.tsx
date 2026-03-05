import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { PackageCheck, Truck, Loader2, Search, Barcode, X } from 'lucide-react';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { PedidoVenta } from '../../lib/types';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface ScannedItem {
    lote_codigo: string;
    producto_id: number;
    producto_nombre: string;
    peso: number;
}

export function DespachoDashboard() {
    const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
    const [selectedPedidos, setSelectedPedidos] = useState<number[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isDespachoMode, setIsDespachoMode] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");

    // Dispatch/Scanning State
    const [scannedItems, setScannedItems] = useState<ScannedItem[]>([]);
    const [barcodeInput, setBarcodeInput] = useState("");
    const [isValidating, setIsValidating] = useState(false);
    const [processing, setProcessing] = useState(false);

    // Aggregated Requirements
    const [requirements, setRequirements] = useState<{ [key: string]: { required: number, scanned: number } }>({});

    const barcodeInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchPedidos();
    }, []);

    // Focus barcode input when in despacho mode
    useEffect(() => {
        if (isDespachoMode && barcodeInputRef.current) {
            barcodeInputRef.current.focus();
        }
    }, [isDespachoMode, scannedItems]);

    // Recalculate requirements when selected orders change
    useEffect(() => {
        if (selectedPedidos.length === 0) return;

        const reqs: { [key: string]: { required: number, scanned: number } } = {};

        selectedPedidos.forEach(pid => {
            const pedido = pedidos.find(p => p.id === pid);
            if (!pedido) return;

            pedido.detalles?.forEach((det: any) => {
                // Assuming detail has product name/description. If not, fallback to ID.
                // In production, backend serializes 'producto_descripcion' or 'producto_nombre'
                const prodName = det.producto_descripcion || `Producto ${det.producto}`;
                if (!reqs[prodName]) {
                    reqs[prodName] = { required: 0, scanned: 0 };
                }
                reqs[prodName].required += parseFloat(det.peso);
            });
        });

        // Update scanned counts
        scannedItems.forEach(item => {
            if (reqs[item.producto_nombre]) {
                reqs[item.producto_nombre].scanned += item.peso;
            } else {
                // Scanned item not in requirements (extra or wrong item?)
                // Add it to track it anyway
                if (!reqs[item.producto_nombre]) {
                    reqs[item.producto_nombre] = { required: 0, scanned: 0 };
                }
                reqs[item.producto_nombre].scanned += item.peso;
            }
        });

        setRequirements(reqs);

    }, [selectedPedidos, pedidos, scannedItems]);


    const fetchPedidos = async () => {
        try {
            setIsLoading(true);
            const response = await apiClient.get<PedidoVenta[]>('/pedidos-venta/?estado=pendiente&limit=100');
            setPedidos(response.data);
        } catch (error) {
            console.error("Error fetching orders", error);
            toast.error("Error al cargar pedidos pendientes");
        } finally {
            setIsLoading(false);
        }
    };

    const toggleSelection = (id: number) => {
        setSelectedPedidos(prev =>
            prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
        );
    };

    const handleStartDespacho = () => {
        if (selectedPedidos.length === 0) return;

        // Verify all selected orders belong to same client
        const firstOrder = pedidos.find(p => p.id === selectedPedidos[0]);
        // Note: checking client ID or name correctness depends on dataset quality. 
        // Ideally enforce strict check.
        const differentClient = selectedPedidos.some(pid => {
            const p = pedidos.find(o => o.id === pid);
            return p?.cliente !== firstOrder?.cliente;
        });

        if (differentClient) {
            toast.warning("Has seleccionado pedidos de diferentes clientes. Asegúrate de que esto sea intencional.");
        }

        setIsDespachoMode(true);
        setScannedItems([]);
    };

    const handleScan = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!barcodeInput.trim()) return;

        if (scannedItems.some(i => i.lote_codigo === barcodeInput.trim())) {
            toast.warning("Este lote ya fue escaneado.");
            setBarcodeInput("");
            return;
        }

        setIsValidating(true);
        try {
            // Call scanning microservice to validate lote
            const res = await apiClient.post('/scanning/validate', { code: barcodeInput.trim() });

            if (res.data.valid) {
                const newItem: ScannedItem = {
                    lote_codigo: res.data.lote.codigo,
                    producto_id: res.data.lote.producto_id,
                    producto_nombre: res.data.lote.producto_nombre,
                    peso: parseFloat(res.data.lote.peso)
                };

                setScannedItems(prev => [...prev, newItem]);
                toast.success(`Lote ${newItem.lote_codigo} agregado (${newItem.peso}kg)`);
            } else {
                toast.error(res.data.reason || "Lote no válido o no disponible");
            }
        } catch (error) {
            console.error("Scan error", error);
            toast.error("Error al validar el código de barras");
        } finally {
            setIsValidating(false);
            setBarcodeInput("");
            if (barcodeInputRef.current) barcodeInputRef.current.focus();
        }
    };

    const handleRemoveItem = (index: number) => {
        setScannedItems(prev => prev.filter((_, i) => i !== index));
    };

    const handleFinalize = async () => {
        // Validation: Warn if requirements not met
        const incomplete = Object.entries(requirements).some(([_, val]) => val.scanned < val.required);
        if (incomplete) {
            const confirm = window.confirm("La cantidad escaneada es menor a la requerida. ¿Deseas despachar de todas formas?");
            if (!confirm) return;
        }

        setProcessing(true);
        try {
            await apiClient.post('/inventory/process-despacho/', {
                pedidos: selectedPedidos,
                lotes: scannedItems.map(i => i.lote_codigo)
            });

            toast.success("Despacho procesado exitosamente");

            // Auto Print?
            handlePrintDocuments();

            // Refresh and Reset
            setIsDespachoMode(false);
            setSelectedPedidos([]);
            setScannedItems([]);
            fetchPedidos();

        } catch (error) {
            console.error("Dispatch error", error);
            toast.error("Error al procesar el despacho");
        } finally {
            setProcessing(false);
        }
    };

    const handlePrintDocuments = async () => {
        // Generate/Print PDF for each order
        for (const pid of selectedPedidos) {
            try {
                const response = await apiClient.get(`/pedidos-venta/${pid}/download_pdf/`, { responseType: 'blob' });
                const url = window.URL.createObjectURL(new Blob([response.data]));
                // Open in new tab is better for multiple downloads
                window.open(url, '_blank');
            } catch (e) {
                console.error("Print error", e);
                toast.error(`Error al imprimir pedido #${pid}`);
            }
        }
    };

    const filteredPedidos = pedidos.filter(p =>
        p.cliente_nombre?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.guia_remision?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.id.toString().includes(searchTerm)
    );

    if (isLoading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;

    if (isDespachoMode) {
        return (
            <div className="space-y-6 p-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-2xl font-bold">Procesando Despacho</h1>
                        <p className="text-muted-foreground">Escanea los códigos de las etiquetas para confirmar salida.</p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => setIsDespachoMode(false)}>Cancelar</Button>
                        <Button className="bg-green-600 hover:bg-green-700" onClick={handleFinalize} disabled={processing}>
                            {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <><PackageCheck className="w-4 h-4 mr-2" /> Confirmar Salida</>}
                        </Button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Scanning Area */}
                    <Card className="h-fit">
                        <CardHeader>
                            <CardTitle>Pistoleo de Etiquetas</CardTitle>
                            <CardDescription>Escanea el código de barras ZPL/QR del lote.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <form onSubmit={handleScan} className="flex gap-2">
                                <Input
                                    ref={barcodeInputRef}
                                    value={barcodeInput}
                                    onChange={e => setBarcodeInput(e.target.value)}
                                    placeholder="Escanea aquí (Ej: LOTE-1234)"
                                    className="font-mono text-lg"
                                    autoFocus
                                    disabled={isValidating}
                                />
                                <Button type="submit" disabled={isValidating}>
                                    {isValidating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Barcode className="w-6 h-6" />}
                                </Button>
                            </form>

                            <div className="border rounded-md h-[300px] overflow-y-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Lote</TableHead>
                                            <TableHead>Producto</TableHead>
                                            <TableHead className="text-right">Peso</TableHead>
                                            <TableHead></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {scannedItems.length === 0 ? (
                                            <TableRow><TableCell colSpan={4} className="text-center py-4 text-muted-foreground">Esperando escaneo...</TableCell></TableRow>
                                        ) : (
                                            scannedItems.map((item, idx) => (
                                                <TableRow key={idx}>
                                                    <TableCell className="font-mono text-xs">{item.lote_codigo}</TableCell>
                                                    <TableCell className="text-xs truncate max-w-[150px]">{item.producto_nombre}</TableCell>
                                                    <TableCell className="text-right font-bold">{item.peso.toFixed(2)}</TableCell>
                                                    <TableCell>
                                                        <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => handleRemoveItem(idx)}>
                                                            <X className="w-3 h-3" />
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        ).reverse()}
                                    </TableBody>
                                </Table>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Requirements Status */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Estado de la Carga</CardTitle>
                            <CardDescription>Comparativa Teórico vs Físico</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {Object.entries(requirements).map(([prodName, counts], idx) => {
                                const progress = Math.min((counts.scanned / (counts.required || 1)) * 100, 100);
                                const isComplete = counts.scanned >= counts.required;

                                return (
                                    <div key={idx} className="space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="font-semibold truncate max-w-[200px]" title={prodName}>{prodName}</span>
                                            <span className={isComplete ? "text-green-600 font-bold" : "text-orange-500"}>
                                                {counts.scanned.toFixed(2)} / {counts.required.toFixed(2)} kg
                                            </span>
                                        </div>
                                        <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full transition-all duration-500 ${isComplete ? 'bg-green-500' : 'bg-orange-400'}`}
                                                style={{ width: `${progress}%` }}
                                            />
                                        </div>
                                    </div>
                                );
                            })}
                            {Object.keys(requirements).length === 0 && (
                                <p className="text-center text-muted-foreground italic">No hay requerimientos calculados.</p>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        );
    }

    // Default Selection Mode
    return (
        <div className="space-y-6 p-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Panel de Despacho</h1>
                    <p className="text-muted-foreground">Selecciona pedidos para iniciar el proceso de carga.</p>
                </div>
                {selectedPedidos.length > 0 && (
                    <div className="flex gap-2 animate-in fade-in slide-in-from-right-4">
                        <div className="bg-primary text-primary-foreground px-4 py-2 rounded-md font-bold flex items-center shadow-md">
                            {selectedPedidos.length} {selectedPedidos.length === 1 ? 'Pedido' : 'Pedidos'}
                        </div>
                        <Button onClick={handleStartDespacho} className="gap-2 shadow-lg bg-green-600 hover:bg-green-700">
                            <Truck className="w-4 h-4" /> Iniciar Despacho
                        </Button>
                    </div>
                )}
            </div>

            <Card>
                <CardHeader>
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <CardTitle>Pedidos Pendientes</CardTitle>
                            <CardDescription>Marca los pedidos que se van a despachar en el mismo viaje.</CardDescription>
                        </div>
                        <div className="relative w-full md:w-72">
                            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Buscar por cliente, guía..."
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
                                <TableHead className="w-[50px]"></TableHead>
                                <TableHead>Pedido</TableHead>
                                <TableHead>Cliente</TableHead>
                                <TableHead>Items</TableHead>
                                <TableHead>Estado</TableHead>
                                <TableHead className="text-right">Total Peso</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredPedidos.map(pedido => {
                                const totalPeso = pedido.detalles?.reduce((acc: number, d: any) => acc + parseFloat(d.peso), 0) || 0;
                                return (
                                    <TableRow key={pedido.id} className={`cursor-pointer ${selectedPedidos.includes(pedido.id) ? "bg-slate-50" : ""}`} onClick={() => toggleSelection(pedido.id)}>
                                        <TableCell onClick={e => e.stopPropagation()}>
                                            <Checkbox
                                                checked={selectedPedidos.includes(pedido.id)}
                                                onCheckedChange={() => toggleSelection(pedido.id)}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex flex-col">
                                                <span className="font-bold">#{pedido.guia_remision || pedido.id}</span>
                                                <span className="text-xs text-muted-foreground date">{format(new Date(pedido.fecha_pedido), 'dd MMM yyyy', { locale: es })}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>{pedido.cliente_nombre}</TableCell>
                                        <TableCell>{pedido.detalles?.length || 0} prod.</TableCell>
                                        <TableCell>
                                            {pedido.esta_pagado ?
                                                <Badge variant="outline" className="text-green-600 bg-green-50 border-green-200">Pagado</Badge> :
                                                <Badge variant="secondary">Crédito</Badge>
                                            }
                                        </TableCell>
                                        <TableCell className="text-right font-mono font-bold">
                                            {totalPeso.toFixed(2)} kg
                                        </TableCell>
                                    </TableRow>
                                )
                            })}
                            {filteredPedidos.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                                        No hay pedidos pendientes.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
