import React, { useEffect, useMemo, useState, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { PackageCheck, Truck, Loader2, Search, Barcode, X, History, AlertTriangle } from 'lucide-react';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { abrirPdfEnPestana } from '../../lib/abrirPdf';
import { PedidoVenta } from '../../lib/types';
import { usePagination } from '../../hooks/usePagination';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { ControlesPaginacion } from '../ui/controles-paginacion';
import { datosDeError, estadoHttp } from '../../lib/apiError';
import { toArray } from '../../lib/collections';
import { useCargaRemota } from '../../hooks/useCargaRemota';

interface ItemIncompleto {
    requerido: number;
    escaneado: number;
    faltante: number;
}

interface LineaLote {
    producto_id: number;
    producto_nombre: string;
    peso: number;
}

interface ScannedItem {
    lote_codigo: string;
    producto_id: number;
    producto_nombre: string;
    peso: number;
    /** Filas vendibles del lote: la de su producto primero y las agregadas a mano. */
    lineas: LineaLote[];
    /** Motivo por el que el backend rechazó este lote al confirmar (p. ej., otro despachador ya se lo llevó). */
    rechazo?: string;
}

/** Rechazos de un lote concreto en process-despacho: el lote se marca en la lista. */
const CODIGOS_LOTE_RECHAZADO = ['lote_ya_despachado', 'lote_sin_stock'];

/**
 * Líneas del lote que salen con estos pedidos (misma regla que process-despacho): la del
 * producto del lote siempre; las de productos agregados a mano solo si alguien las pide.
 */
function lineasQueSalen(item: ScannedItem, productosPedidos: Set<number>): LineaLote[] {
    return item.lineas.filter((linea, idx) => idx === 0 || productosPedidos.has(linea.producto_id));
}

const ITEMS_PER_PAGE = 20;
const SIN_PEDIDOS: PedidoVenta[] = [];

/** Productos que piden los pedidos seleccionados. */
function idsProductosPedidos(selectedPedidos: number[], pedidos: PedidoVenta[]): Set<number> {
    const ids = new Set<number>();
    pedidos
        .filter(p => selectedPedidos.includes(p.id))
        .forEach(p => p.detalles?.forEach(det => ids.add(Number(det.producto))));
    return ids;
}

export function DespachoDashboard() {
    const [selectedPedidos, setSelectedPedidos] = useState<number[]>([]);
    // despachado_parcial: pedidos con un despacho previo incompleto siguen
    // en la cola hasta que se termine de despachar lo que falta.
    const cargaPedidos = useCargaRemota(
        () =>
            apiClient
                .get<PedidoVenta[]>('/pedidos-venta/?estado=pendiente,despachado_parcial&limit=100')
                .then((response) => toArray<PedidoVenta>(response.data))
                .catch((error: unknown) => {
                    console.error("Error fetching orders", error);
                    toast.error("Error al cargar pedidos pendientes");
                    throw error;
                }),
        'pedidos-por-despachar',
    );
    const pedidos = cargaPedidos.datos ?? SIN_PEDIDOS;
    const isLoading = cargaPedidos.cargando;
    const { recargar: fetchPedidos } = cargaPedidos;
    const [isDespachoMode, setIsDespachoMode] = useState(false);
    const [searchParams, setSearchParams] = useSearchParams();
    const navigate = useNavigate();
    const searchTerm = searchParams.get('search') || '';

    // Estado de despacho/escaneo
    const [scannedItems, setScannedItems] = useState<ScannedItem[]>([]);
    const [barcodeInput, setBarcodeInput] = useState("");
    const [isValidating, setIsValidating] = useState(false);
    const [processing, setProcessing] = useState(false);

    // Modal de confirmación de despacho incompleto
    const [showIncompleteModal, setShowIncompleteModal] = useState(false);
    const [itemsIncompletos, setItemsIncompletos] = useState<Record<string, ItemIncompleto>>({});

    const barcodeInputRef = useRef<HTMLInputElement>(null);

    // Enfoca el input del código de barras en modo despacho
    useEffect(() => {
        if (isDespachoMode && barcodeInputRef.current) {
            barcodeInputRef.current.focus();
        }
    }, [isDespachoMode, scannedItems]);

    // Requerimientos agregados de los pedidos seleccionados frente a lo escaneado.
    const requirements = useMemo(() => {
        const reqs: { [key: string]: { required: number, scanned: number } } = {};

        selectedPedidos.forEach(pid => {
            const pedido = pedidos.find(p => p.id === pid);
            if (!pedido) return;

            pedido.detalles?.forEach((det) => {
                // En producción, el backend serializa 'producto_descripcion' o 'producto_nombre'
                const prodName = det.producto_descripcion || `Producto ${det.producto}`;
                if (!reqs[prodName]) {
                    reqs[prodName] = { required: 0, scanned: 0 };
                }
                reqs[prodName].required += parseFloat(String(det.peso));
            });
        });

        // Update scanned counts: cada línea del lote suma a su producto; un producto que
        // nadie pidió igual aparece (excedente) para que el despachador lo vea.
        const productosPedidos = idsProductosPedidos(selectedPedidos, pedidos);
        scannedItems.forEach(item => {
            lineasQueSalen(item, productosPedidos).forEach(linea => {
                if (!reqs[linea.producto_nombre]) {
                    reqs[linea.producto_nombre] = { required: 0, scanned: 0 };
                }
                reqs[linea.producto_nombre].scanned += linea.peso;
            });
        });

        return reqs;
    }, [selectedPedidos, pedidos, scannedItems]);

    const toggleSelection = (id: number) => {
        setSelectedPedidos(prev =>
            prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
        );
    };

    const handleStartDespacho = () => {
        if (selectedPedidos.length === 0) return;

        // Verifica que todas las órdenes seleccionadas pertenezcan al mismo cliente
        const firstOrder = pedidos.find(p => p.id === selectedPedidos[0]);
        // Nota: la verificación del ID o nombre del cliente depende de la calidad de los datos. 
        // Idealmente, aplicar una verificación estricta.
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
        const codigoEscaneado = barcodeInput.trim();
        if (!codigoEscaneado) return;

        if (scannedItems.some(i => i.lote_codigo === codigoEscaneado)) {
            toast.warning("Este lote ya fue escaneado.");
            setBarcodeInput("");
            return;
        }

        setIsValidating(true);
        try {
            // Llama al microservicio de escaneo para validar el lote
            const res = await apiClient.post('/scanning/validate', { code: codigoEscaneado });

            if (res.data.valid) {
                const lote = res.data.lote;
                const principal: LineaLote = {
                    producto_id: lote.producto_id,
                    producto_nombre: lote.producto_nombre,
                    peso: parseFloat(lote.peso),
                };
                const newItem: ScannedItem = {
                    lote_codigo: lote.codigo,
                    ...principal,
                    lineas: lote.productos?.length
                        ? lote.productos.map((p: LineaLote & { peso: string }) => ({
                            producto_id: p.producto_id,
                            producto_nombre: p.producto_nombre,
                            peso: parseFloat(p.peso),
                        }))
                        : [principal],
                };

                setScannedItems(prev => [...prev, newItem]);
                const pesoQueSale = lineasQueSalen(newItem, idsProductosPedidos(selectedPedidos, pedidos))
                    .reduce((total, linea) => total + linea.peso, 0);
                toast.success(`Lote ${newItem.lote_codigo} agregado (${pesoQueSale}kg)`);
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

    const submitDespacho = async (confirmarIncompleto: boolean) => {
        setProcessing(true);
        try {
            const { data } = await apiClient.post('/inventory/process-despacho/', {
                pedidos: selectedPedidos,
                lotes: scannedItems.map(i => i.lote_codigo),
                confirmar_incompleto: confirmarIncompleto,
            });

            toast.success("Despacho procesado exitosamente");
            handlePrintDocuments(data?.despacho_id);

            setShowIncompleteModal(false);
            setIsDespachoMode(false);
            setSelectedPedidos([]);
            setScannedItems([]);
            setItemsIncompletos({});
            fetchPedidos();

        } catch (error) {
            const datos = datosDeError(error) as {
                items_incompletos?: typeof itemsIncompletos;
                error?: string;
                codigo?: string;
                lote?: string;
            } | undefined;
            if (estadoHttp(error) === 409 && datos?.items_incompletos) {
                setItemsIncompletos(datos.items_incompletos);
                setShowIncompleteModal(true);
            } else if (datos?.lote && datos.error && CODIGOS_LOTE_RECHAZADO.includes(datos.codigo ?? '')) {
                // Otro despachador se llevó el lote (o ya no tiene stock): se dice quién y cuándo
                // y se marca el lote para que lo quite antes de volver a confirmar.
                const motivo = datos.error;
                setScannedItems(prev => prev.map(i => (i.lote_codigo === datos.lote ? { ...i, rechazo: motivo } : i)));
                toast.error("Despacho rechazado", { description: motivo, duration: 10000 });
            } else {
                console.error("Dispatch error", error);
                toast.error(datos?.error ?? "Error al procesar el despacho");
            }
        } finally {
            setProcessing(false);
        }
    };

    const hayLotesRechazados = scannedItems.some(i => i.rechazo);

    const handleFinalize = () => submitDespacho(false);
    const handleConfirmIncomplete = () => submitDespacho(true);

    const handlePrintDocuments = async (despachoId?: number) => {
        // Nota de venta acotada a lo despachado en ESTE evento (historial_id) —
        // si el despacho fue parcial, no debe imprimir el pedido completo.
        const query = despachoId ? `?historial_id=${despachoId}` : '';
        for (const pid of selectedPedidos) {
            try {
                const response = await apiClient.get(`/pedidos-venta/${pid}/download_pdf/${query}`, { responseType: 'blob' });
                // Se abre en pestaña nueva para permitir varias descargas
                abrirPdfEnPestana(response.data);
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

    const {
        currentPage: safePage,
        setCurrentPage,
        totalPages,
        paginatedItems: paginatedPedidos,
    } = usePagination(filteredPedidos, ITEMS_PER_PAGE, { resetKey: searchTerm });

    if (isLoading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;

    if (isDespachoMode) {
        return (
            <>
            <div className="space-y-6 p-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-2xl font-bold">Procesando Despacho</h1>
                        <p className="text-muted-foreground">Escanea los códigos de las etiquetas para confirmar salida.</p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => setIsDespachoMode(false)}>Cancelar</Button>
                        <Button className="bg-green-600 hover:bg-green-700" onClick={handleFinalize} disabled={processing || hayLotesRechazados}>
                            {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <><PackageCheck className="w-4 h-4 mr-2" /> Confirmar Salida</>}
                        </Button>
                    </div>
                </div>
                {hayLotesRechazados && (
                    <p className="text-sm text-destructive text-right">Quite los lotes marcados en rojo para continuar.</p>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Área de escaneo */}
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
                                                <React.Fragment key={item.lote_codigo}>
                                                <TableRow className={item.rechazo ? 'bg-destructive/10' : undefined}>
                                                    <TableCell className="font-mono text-xs">{item.lote_codigo}</TableCell>
                                                    <TableCell className="text-xs truncate max-w-[150px]">
                                                        {item.producto_nombre}
                                                        {lineasQueSalen(item, idsProductosPedidos(selectedPedidos, pedidos)).slice(1).map(linea => (
                                                            <div key={linea.producto_id} className="text-muted-foreground">
                                                                {`+ ${linea.producto_nombre} (${linea.peso.toFixed(2)})`}
                                                            </div>
                                                        ))}
                                                    </TableCell>
                                                    <TableCell className="text-right font-bold">{item.peso.toFixed(2)}</TableCell>
                                                    <TableCell>
                                                        <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive" onClick={() => handleRemoveItem(idx)} aria-label={`Quitar lote ${item.lote_codigo}`}>
                                                            <X className="w-3 h-3" />
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                                {item.rechazo && (
                                                    <TableRow className="bg-destructive/10">
                                                        <TableCell colSpan={4} role="alert" className="text-xs text-destructive whitespace-normal">
                                                            <AlertTriangle className="inline w-3 h-3 mr-1" aria-hidden="true" />
                                                            {item.rechazo}
                                                        </TableCell>
                                                    </TableRow>
                                                )}
                                                </React.Fragment>
                                            ))
                                        ).reverse()}
                                    </TableBody>
                                </Table>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Estado de requisitos */}
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

            {/* Modal de confirmación — despacho incompleto */}
            <Dialog open={showIncompleteModal} onOpenChange={setShowIncompleteModal}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-amber-600">
                            <AlertTriangle className="w-5 h-5" />
                            Despacho incompleto
                        </DialogTitle>
                        <DialogDescription>
                            Los siguientes productos tienen una cantidad escaneada menor a la requerida por los pedidos seleccionados.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="border rounded-md overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Producto</TableHead>
                                    <TableHead className="text-right">Requerido</TableHead>
                                    <TableHead className="text-right">Escaneado</TableHead>
                                    <TableHead className="text-right text-amber-600">Faltante</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {Object.entries(itemsIncompletos).map(([nombre, vals]) => (
                                    <TableRow key={nombre}>
                                        <TableCell className="font-medium text-sm">{nombre}</TableCell>
                                        <TableCell className="text-right font-mono text-sm">{vals.requerido.toFixed(2)} kg</TableCell>
                                        <TableCell className="text-right font-mono text-sm">{vals.escaneado.toFixed(2)} kg</TableCell>
                                        <TableCell className="text-right font-mono text-sm font-bold text-amber-600">
                                            -{vals.faltante.toFixed(2)} kg
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>

                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button
                            variant="outline"
                            onClick={() => setShowIncompleteModal(false)}
                            disabled={processing}
                        >
                            Cancelar — seguir escaneando
                        </Button>
                        <Button
                            className="bg-amber-600 hover:bg-amber-700 text-white"
                            onClick={handleConfirmIncomplete}
                            disabled={processing}
                        >
                            {processing
                                ? <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                : <PackageCheck className="w-4 h-4 mr-2" />
                            }
                            Despachar de todas formas
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
            </>
        );
    }

    // Modo de selección por defecto
    return (
        <div className="space-y-6 p-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Panel de Despacho</h1>
                    <p className="text-muted-foreground">Selecciona pedidos para iniciar el proceso de carga.</p>
                </div>
                {selectedPedidos.length > 0 ? (
                    <div className="flex gap-2 animate-in fade-in slide-in-from-right-4">
                        <div className="bg-primary text-primary-foreground px-4 py-2 rounded-md font-bold flex items-center shadow-md">
                            {selectedPedidos.length} {selectedPedidos.length === 1 ? 'Pedido' : 'Pedidos'}
                        </div>
                        <Button onClick={handleStartDespacho} className="gap-2 shadow-lg bg-green-600 hover:bg-green-700">
                            <Truck className="w-4 h-4" /> Iniciar Despacho
                        </Button>
                    </div>
                ) : (
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => navigate('/despacho/historial')} className="gap-2">
                            <History className="w-4 h-4" /> Ver Historial
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
                                onChange={(e) => {
                                    const val = e.target.value;
                                    setSearchParams(prev => {
                                        if (val) prev.set('search', val);
                                        else prev.delete('search');
                                        return prev;
                                    }, { replace: true });
                                }}
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
                            {paginatedPedidos.map(pedido => {
                                const totalPeso = pedido.detalles?.reduce((acc: number, d) => acc + parseFloat(String(d.peso)), 0) || 0;
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
                                                <div className="flex items-center gap-2">
                                                    <span className="font-bold">#{pedido.guia_remision || pedido.id}</span>
                                                    {pedido.estado === 'despachado_parcial' && (
                                                        <Badge variant="outline" className="text-amber-700 bg-amber-50 border-amber-200">
                                                            Parcial
                                                        </Badge>
                                                    )}
                                                </div>
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
                    {filteredPedidos.length > 0 && (
                        <ControlesPaginacion
                          currentPage={safePage}
                          totalPages={totalPages}
                          setCurrentPage={setCurrentPage}
                          className="mt-4"
                        />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
