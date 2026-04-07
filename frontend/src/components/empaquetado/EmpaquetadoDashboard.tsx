import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { BadgeCheck, PackageSearch, Printer, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { Progress } from '../ui/progress';
import { Checkbox } from '../ui/checkbox';
import apiClient from '../../lib/axios';
import { OrdenProduccion, Maquina, LoteProduccion } from '../../lib/types';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '../ui/form';

// Schema for packaging validation
const packagingSchema = z.object({
    orden_produccion: z.string().min(1, "Seleccione una orden"),
    maquina: z.string().min(1, "Seleccione una máquina"),
    codigo_lote: z.string().min(3, "Código de lote requerido"),
    presentacion: z.string().min(1, "Presentación requerida"),
    peso_bruto: z.coerce.number().min(0.01, "Peso bruto debe ser mayor a 0"),
    tara: z.coerce.number().min(0, "Tara no puede ser negativa"),
    cantidad_metros: z.coerce.number().optional(),
    unidades_empaque: z.coerce.number().int().min(1, "Mínimo 1 unidad"),
    turno: z.string().default('T1'),
    completar_orden: z.boolean().default(false),
}).refine(data => data.peso_bruto > data.tara, {
    message: "El peso bruto debe ser mayor que la tara",
    path: ["peso_bruto"],
});

type PackagingFormValues = z.infer<typeof packagingSchema>;

export function EmpaquetadoDashboard() {
    const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
    const [maquinas, setMaquinas] = useState<Maquina[]>([]);
    const [recentLotes, setRecentLotes] = useState<LoteProduccion[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [selectedOrden, setSelectedOrden] = useState<OrdenProduccion | null>(null);
    const [isScaleConnected, setIsScaleConnected] = useState(false);
    const [port, setPort] = useState<any>(null); // Guardamos la referencia al puerto Serial
    const [currentRecentPage, setCurrentRecentPage] = useState(1);
    const ITEMS_PER_PAGE = 20;

    const form = useForm<PackagingFormValues>({
        resolver: zodResolver(packagingSchema) as any,
        defaultValues: {
            orden_produccion: "",
            maquina: "",
            codigo_lote: "", // Will be suggested by backend
            presentacion: "Caja",
            peso_bruto: 0,
            tara: 0,
            cantidad_metros: undefined,
            unidades_empaque: 1,
            turno: "T1",
            completar_orden: false
        }
    });

    // Watch presentation to auto-suggest tare
    const presentationWatch = form.watch("presentacion");

    useEffect(() => {
        fetchInitialData();
    }, []);

    useEffect(() => {
        if (presentationWatch === 'Caja') {
            form.setValue('tara', 0.5); // Example default tare for Box
        } else if (presentationWatch === 'Funda') {
            form.setValue('tara', 0.1); // Example default for Bag
        } else if (presentationWatch === 'Cono') {
            form.setValue('tara', 0.05);
        }
    }, [presentationWatch, form]);


    const connectScale = async () => {
        try {
            if (!('serial' in navigator)) {
                toast.error("Tu navegador no soporta Web Serial API (Usa Chrome o Edge)");
                return;
            }

            // Request port
            const selectedPort = await (navigator as any).serial.requestPort();
            await selectedPort.open({ baudRate: 9600 }); // Configuración común de balanzas

            setPort(selectedPort);
            setIsScaleConnected(true);
            toast.success("Balanza conectada correctamente");

            // Iniciar lectura
            readFromScale(selectedPort);
        } catch (error) {
            console.error("Error connecting to scale", error);
            toast.error("No se pudo conectar a la balanza");
        }
    };

    const readFromScale = async (activePort: any) => {
        const textDecoder = new TextDecoderStream();
        const readableStreamClosed = activePort.readable.pipeTo(textDecoder.writable);
        const reader = textDecoder.readable.getReader();

        let buffer = "";

        try {
            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    break;
                }
                if (value) {
                    buffer += value;
                    // Supongamos que la balanza envía datos terminados en \r o \n
                    if (buffer.includes('\n') || buffer.includes('\r')) {
                        const lines = buffer.split(/\r?\n/);
                        buffer = lines.pop() || ""; // keep incomplete part
                        
                        for (const line of lines) {
                            const cleanLine = line.trim();
                            if (cleanLine) {
                                // Intenta extraer un número del string que llega
                                const match = cleanLine.match(/[\d.]+/);
                                if (match) {
                                    const parsedWeight = parseFloat(match[0]);
                                    if (!isNaN(parsedWeight) && parsedWeight > 0) {
                                        form.setValue('peso_bruto', parsedWeight);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Error reading from scale", error);
            setIsScaleConnected(false);
            setPort(null);
            toast.error("Conexión con la balanza perdida");
        } finally {
            reader.releaseLock();
        }
    };

    const fetchInitialData = async () => {
        try {
            setIsLoading(true);
            const [ordenesRes, maquinasRes, lotesRes] = await Promise.all([
                apiClient.get<OrdenProduccion[]>('/ordenes-produccion/?estado=en_proceso'),
                apiClient.get<Maquina[]>('/maquinas/'),
                apiClient.get<LoteProduccion[]>('/lotes-produccion/?ordering=-id&limit=200')
            ]);
            setOrdenes(ordenesRes.data);
            setMaquinas(maquinasRes.data);
            setRecentLotes(lotesRes.data);
        } catch (error) {
            console.error("Error fetching data", error);
            toast.error("Error al cargar datos iniciales");
        } finally {
            setIsLoading(false);
        }
    };

    const onSubmit = async (data: PackagingFormValues) => {
        if (!selectedOrden) {
            toast.error("Seleccione una orden válida");
            return;
        }

        setIsSubmitting(true);
        try {
            // Calculate Net Weight for display/check (Backend validates too)
            const peso_neto = Number((data.peso_bruto - data.tara).toFixed(2));

            const payload = {
                ...data,
                peso_neto_producido: peso_neto, // Backend expects this based on RegistrarLote logic
                hora_inicio: new Date().toISOString(), // Simplified for now
                // hora_final logic simplified
            };

            const res = await apiClient.post(`/ordenes-produccion/${data.orden_produccion}/registrar-lote/`, payload);

            toast.success(`Lote ${res.data.codigo_lote} registrado correctamente. Peso Neto: ${peso_neto}kg`);

            // Auto-trigger Label Print?
            handlePrintLabel(res.data.id);

            // Reset and refresh (keep connection and specific states)
            form.reset({
                orden_produccion: data.orden_produccion, // Mantener la misma orden seleccionada ayuda a la rapidez
                maquina: data.maquina, // Mantener máquina
                codigo_lote: "", // Reset para el siguiente
                presentacion: data.presentacion,
                peso_bruto: 0, // Reset pesos
                cantidad_metros: undefined, 
                tara: data.tara, // Maintain tare assuming same packaging
                unidades_empaque: data.unidades_empaque,
                turno: data.turno,
                completar_orden: false
            });
            fetchInitialData();

        } catch (error: any) {
            console.error("Error registering packaging", error);
            const msg = error.response?.data?.detail || "Error al registrar el empaque.";
            toast.error(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handlePrintLabel = async (loteId: number) => {
        try {
            const res = await apiClient.get<{ zpl: string }>(`/lotes-produccion/${loteId}/generate_zpl/`);
            const zpl = res.data.zpl;

            // Integrate with Zebra Browser Print (or simulate)
            // For now, we simulate sending to a local service or opening a print window
            console.log("Printing ZPL:", zpl);

            // Check if Zebra Browser Print is available (window.BrowserPrint)
            // Assuming wrapper or direct use.
            // Fallback: Copy to clipboard or Download
            await navigator.clipboard.writeText(zpl);
            toast.info("Código ZPL copiado al portapapeles (Simulación de Impresión)");

        } catch (error) {
            console.error("Error generating label", error);
            toast.error("Error al generar la etiqueta");
        }
    };

    if (isLoading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;

    const totalRecentPages = Math.max(1, Math.ceil(recentLotes.length / ITEMS_PER_PAGE));
    const safeRecentPage = Math.min(Math.max(1, currentRecentPage), totalRecentPages);
    const paginatedRecentLotes = recentLotes.slice(
        (safeRecentPage - 1) * ITEMS_PER_PAGE,
        safeRecentPage * ITEMS_PER_PAGE
    );

    return (
        <div className="space-y-6 p-6">
             <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white/50 backdrop-blur-sm p-6 rounded-3xl border border-white/20 shadow-sm">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                        Estación de Empaque
                    </h1>
                    <p className="text-muted-foreground mt-1 text-lg">Control de lotes y etiquetado inteligente.</p>
                </div>
                <div className="flex items-center gap-3">
                    <Button 
                        variant={isScaleConnected ? "outline" : "default"} 
                        onClick={connectScale} 
                        disabled={isScaleConnected}
                        className={isScaleConnected ? "border-green-500 text-green-600 font-bold" : ""}
                    >
                        {isScaleConnected ? 'Balanza Conectada' : 'Conectar Balanza (COM)'}
                    </Button>
                    <div className={`h-3 w-3 rounded-full ${isScaleConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    <span className="text-sm font-medium text-muted-foreground italic">Sistema en Línea</span>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Registration Form */}
                <Card>
                    <CardHeader>
                        <CardTitle>Registrar Nuevo Bulto/Caja</CardTitle>
                        <CardDescription>Seleccione la orden de producción activa.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">

                                <FormField
                                    control={form.control}
                                    name="orden_produccion"
                                    render={({ field }: { field: any }) => (
                                        <FormItem>
                                            <FormLabel>Orden de Producción</FormLabel>
                                            <Select
                                                onValueChange={(val: any) => {
                                                    field.onChange(val);
                                                    const ord = ordenes.find(o => o.id.toString() === val);
                                                    setSelectedOrden(ord || null);
                                                    // Leave empty so backend generates the correct sequential sequence
                                                    form.setValue('codigo_lote', "");
                                                }}
                                                defaultValue={field.value}
                                            >
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Seleccione orden..." />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {ordenes.map(orden => (
                                                        <SelectItem key={orden.id} value={orden.id.toString()}>
                                                            {orden.codigo} - {orden.producto_nombre || 'Producto'} ({orden.sede_nombre})
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                            {selectedOrden && (
                                                <div className="mt-4 p-4 rounded-xl bg-primary/5 border border-primary/10 animate-in fade-in slide-in-from-top-2">
                                                    <div className="flex justify-between text-sm font-semibold mb-2">
                                                        <span className="text-primary">Progreso de Producción</span>
                                                        <span className="text-primary">{Math.round(((selectedOrden.peso_producido || 0) / selectedOrden.peso_neto_requerido) * 100)}%</span>
                                                    </div>
                                                    <Progress value={((selectedOrden.peso_producido || 0) / selectedOrden.peso_neto_requerido) * 100} className="h-2 bg-primary/20" />
                                                    <p className="text-[10px] text-muted-foreground mt-2 uppercase tracking-wider font-bold">
                                                        {selectedOrden.peso_producido || 0}kg de {selectedOrden.peso_neto_requerido}kg requeridos
                                                    </p>
                                                </div>
                                            )}
                                        </FormItem>
                                    )}
                                />

                                <div className="grid grid-cols-2 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="maquina"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Máquina</FormLabel>
                                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                    <FormControl>
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Máquina..." />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        {maquinas.map(m => (
                                                            <SelectItem key={m.id} value={m.id.toString()}>{m.nombre}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="codigo_lote"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Código Lote/Bulto</FormLabel>
                                                <FormControl>
                                                    <Input {...field} placeholder="Ej. L-101" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                <div className="grid grid-cols-3 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="presentacion"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Presentación</FormLabel>
                                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                    <FormControl>
                                                        <SelectTrigger>
                                                            <SelectValue placeholder="Tipo..." />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        <SelectItem value="Caja">Caja</SelectItem>
                                                        <SelectItem value="Funda">Funda</SelectItem>
                                                        <SelectItem value="Cono">Cono</SelectItem>
                                                        <SelectItem value="Rollo">Rollo</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="unidades_empaque"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Unidades</FormLabel>
                                                <FormControl>
                                                    <Input type="number" {...field} onChange={(e: any) => field.onChange(Number(e.target.value))} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="turno"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Turno</FormLabel>
                                                <FormControl>
                                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                                        <FormControl>
                                                            <SelectTrigger>
                                                                <SelectValue />
                                                            </SelectTrigger>
                                                        </FormControl>
                                                        <SelectContent>
                                                            <SelectItem value="T1">Mañana</SelectItem>
                                                            <SelectItem value="T2">Tarde</SelectItem>
                                                            <SelectItem value="T3">Noche</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="peso_bruto"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Peso Bruto (Kg)</FormLabel>
                                                <FormControl>
                                                    <Input type="number" step="0.01" {...field} onChange={(e: any) => field.onChange(Number(e.target.value))} className={`text-lg font-bold ${isScaleConnected ? 'bg-green-50 border-green-500' : ''}`} />
                                                </FormControl>
                                                <FormMessage />
                                                {isScaleConnected && <span className="text-xs text-green-600 font-medium">Auto-actualizando desde balanza...</span>}
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="tara"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Tara (Kg) - Manual</FormLabel>
                                                <FormControl>
                                                    <Input type="number" step="0.01" {...field} onChange={(e: any) => field.onChange(Number(e.target.value))} />
                                                </FormControl>
                                                <FormMessage />
                                                <span className="text-xs text-muted-foreground">Puede modificar la tara según la presentación</span>
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                {selectedOrden?.producto_nombre?.toLowerCase().includes('tela') && (
                                   <FormField
                                        control={form.control}
                                        name="cantidad_metros"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Cantidad de Metros (Opcional)</FormLabel>
                                                <FormControl>
                                                    <Input type="number" step="0.01" {...field} onChange={(e: any) => field.onChange(e.target.value ? Number(e.target.value) : undefined)} value={field.value || ''} placeholder="Metros reenrollados" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                )}

                                {/* Calculated Net Weight Display */}
                                <div className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 rounded-2xl border border-primary/20 flex flex-col items-center justify-center space-y-2 transition-all hover:shadow-md">
                                    <span className="text-xs font-bold uppercase tracking-widest text-primary/70">Peso Neto Calculado</span>
                                    <div className="flex items-baseline space-x-2">
                                        <span className="text-5xl font-black tabular-nums text-primary drop-shadow-sm">
                                            {(form.watch('peso_bruto') - form.watch('tara')).toFixed(2)}
                                        </span>
                                        <span className="text-xl font-bold text-primary/60 italic">kg</span>
                                    </div>
                                </div>

                                <FormField
                                    control={form.control}
                                    name="completar_orden"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                            <FormControl>
                                                <Checkbox
                                                    checked={field.value}
                                                    onCheckedChange={field.onChange}
                                                />
                                            </FormControl>
                                            <div className="space-y-1 leading-none">
                                                <FormLabel>
                                                    Finalizar Orden de Producción
                                                </FormLabel>
                                                <FormDescription>
                                                    Marque esta opción si este es el último lote de la orden.
                                                </FormDescription>
                                            </div>
                                        </FormItem>
                                    )}
                                />

                                <Button type="submit" className="w-full" disabled={isSubmitting}>
                                    {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PackageSearch className="mr-2 h-4 w-4" />}
                                    Registrar e Imprimir Etiqueta
                                </Button>
                            </form>
                        </Form>
                    </CardContent>
                </Card>

                {/* Recent List */}
                <Card>
                    <CardHeader>
                        <CardTitle>Historial Reciente</CardTitle>
                        <CardDescription>Últimos empaques registrados.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Lote</TableHead>
                                    <TableHead>Peso Neto</TableHead>
                                    <TableHead>Acción</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {paginatedRecentLotes.map(lote => (
                                    <TableRow key={lote.id}>
                                        <TableCell className="font-medium">{lote.codigo_lote}</TableCell>
                                        <TableCell>{lote.peso_neto_producido} kg</TableCell>
                                        <TableCell>
                                            <Button variant="ghost" size="sm" onClick={() => handlePrintLabel(lote.id)}>
                                                <Printer className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {recentLotes.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={3} className="text-center text-muted-foreground">No hay registros recientes.</TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                        {recentLotes.length > 0 && (
                            <div className="flex items-center justify-between mt-4">
                                <span className="text-sm text-muted-foreground">
                                    Página {safeRecentPage} de {totalRecentPages}
                                </span>
                                <div className="flex items-center gap-2">
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => setCurrentRecentPage((p) => Math.max(1, p - 1))}
                                        disabled={safeRecentPage === 1}
                                    >
                                        <ChevronLeft className="w-4 h-4 mr-1" />
                                        Anterior
                                    </Button>
                                    <span className="flex items-center gap-1 text-sm">
                                        <span className="text-muted-foreground">Ir a</span>
                                        <Input
                                            type="number"
                                            min={1}
                                            max={totalRecentPages}
                                            defaultValue={safeRecentPage}
                                            key={safeRecentPage}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') {
                                                    const v = parseInt((e.target as HTMLInputElement).value, 10);
                                                    if (!isNaN(v) && v >= 1 && v <= totalRecentPages) setCurrentRecentPage(v);
                                                }
                                            }}
                                            onBlur={(e) => {
                                                const v = parseInt(e.target.value, 10);
                                                if (!isNaN(v) && v >= 1 && v <= totalRecentPages) setCurrentRecentPage(v);
                                            }}
                                            className="w-14 h-8 text-center py-0 px-1"
                                        />
                                    </span>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => setCurrentRecentPage((p) => Math.min(totalRecentPages, p + 1))}
                                        disabled={safeRecentPage === totalRecentPages}
                                    >
                                        Siguiente
                                        <ChevronRight className="w-4 h-4 ml-1" />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
