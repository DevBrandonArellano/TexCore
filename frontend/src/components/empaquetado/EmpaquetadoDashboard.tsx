import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { BadgeCheck, PackageSearch, Printer, Loader2 } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
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
} from '@/components/ui/form';

// Schema for packaging validation
const packagingSchema = z.object({
    orden_produccion: z.string().min(1, "Seleccione una orden"),
    maquina: z.string().min(1, "Seleccione una máquina"),
    codigo_lote: z.string().min(3, "Código de lote requerido"),
    presentacion: z.string().min(1, "Presentación requerida"),
    peso_bruto: z.coerce.number().min(0.01, "Peso bruto debe ser mayor a 0"),
    tara: z.coerce.number().min(0, "Tara no puede ser negativa"),
    unidades_empaque: z.coerce.number().int().min(1, "Mínimo 1 unidad"),
    turno: z.string().default('T1'),
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

    const form = useForm<PackagingFormValues>({
        resolver: zodResolver(packagingSchema) as any,
        defaultValues: {
            orden_produccion: "",
            maquina: "",
            codigo_lote: "",
            presentacion: "Caja",
            peso_bruto: 0,
            tara: 0,
            unidades_empaque: 1,
            turno: "T1"
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


    const fetchInitialData = async () => {
        try {
            setIsLoading(true);
            const [ordenesRes, maquinasRes, lotesRes] = await Promise.all([
                apiClient.get<OrdenProduccion[]>('/ordenes-produccion/?estado=en_proceso'),
                apiClient.get<Maquina[]>('/maquinas/'),
                apiClient.get<LoteProduccion[]>('/lotes-produccion/?ordering=-id&limit=5')
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

            // Reset and refresh
            form.reset({
                orden_produccion: "",
                maquina: "",
                codigo_lote: "",
                presentacion: "Caja",
                peso_bruto: 0,
                tara: 0,
                unidades_empaque: 1,
                turno: "T1"
            });
            setSelectedOrden(null);
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

    return (
        <div className="space-y-6 p-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Estación de Empaque</h1>
                    <p className="text-muted-foreground">Registro de peso, tara y etiquetado de producto final.</p>
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
                                                    // Auto-generate generic batch code based on order
                                                    if (ord) form.setValue('codigo_lote', `${ord.codigo}-L${Math.floor(Math.random() * 1000)}`);
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
                                                    <Input type="number" step="0.01" {...field} onChange={(e: any) => field.onChange(Number(e.target.value))} className="text-lg font-bold" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="tara"
                                        render={({ field }: { field: any }) => (
                                            <FormItem>
                                                <FormLabel>Tara (Kg)</FormLabel>
                                                <FormControl>
                                                    <Input type="number" step="0.01" {...field} onChange={(e: any) => field.onChange(Number(e.target.value))} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                {/* Calculated Net Weight Display */}
                                <div className="p-4 bg-muted rounded-lg flex justify-between items-center">
                                    <span className="font-medium">Peso Neto Calculado:</span>
                                    <span className="text-2xl font-bold">
                                        {(form.watch('peso_bruto') - form.watch('tara')).toFixed(2)} kg
                                    </span>
                                </div>

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
                                {recentLotes.map(lote => (
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
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
