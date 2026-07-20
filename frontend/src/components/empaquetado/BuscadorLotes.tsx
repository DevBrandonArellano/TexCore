import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Search, Printer, Tag, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { LoteProduccion } from '../../lib/types';
import { useAuth } from '../../lib/auth';
import { ReimprimirModal } from './ReimprimirModal';
import { ReetiquetarModal } from './ReetiquetarModal';

const ROLES_SUPERVISOR = ['jefe_area', 'jefe_planta', 'admin_sistemas', 'admin_sede'];

const CALIDAD_OPTIONS = [
    { value: 'primera', label: 'Primera Calidad' },
    { value: 'segunda', label: 'Segunda Calidad' },
    { value: 'saldo', label: 'Saldo / Retazo' },
];

interface Filtros {
    fecha_desde: string;
    fecha_hasta: string;
    turno: string;
    codigo_lote: string;
    clasificacion_calidad: string;
}

const FILTROS_INICIALES: Filtros = {
    fecha_desde: '',
    fecha_hasta: '',
    turno: '',
    codigo_lote: '',
    clasificacion_calidad: '',
};

const PAGE_SIZE = 20;

export function BuscadorLotes() {
    const { profile } = useAuth();
    const esSupervisor = !!profile?.role && ROLES_SUPERVISOR.includes(profile.role);
    const [filtros, setFiltros] = useState<Filtros>(FILTROS_INICIALES);
    const [resultados, setResultados] = useState<LoteProduccion[]>([]);
    const [count, setCount] = useState(0);
    const [page, setPage] = useState(1);
    const [isLoading, setIsLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const [reimprimirTarget, setReimprimirTarget] = useState<LoteProduccion | null>(null);
    const [reetiquetarTarget, setReetiquetarTarget] = useState<LoteProduccion | null>(null);

    const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

    const buscar = async (targetPage: number = 1) => {
        setIsLoading(true);
        try {
            const params: Record<string, string | number> = {
                page: targetPage,
                page_size: PAGE_SIZE,
                ordering: '-hora_final',
            };
            if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde;
            if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta;
            if (filtros.turno) params.turno = filtros.turno;
            if (filtros.codigo_lote) params.codigo_lote = filtros.codigo_lote;
            if (filtros.clasificacion_calidad) params.clasificacion_calidad = filtros.clasificacion_calidad;

            const res = await apiClient.get<{ count: number; results: LoteProduccion[] }>(
                '/lotes-produccion/', { params }
            );
            setResultados(res.data.results);
            setCount(res.data.count);
            setPage(targetPage);
            setHasSearched(true);
        } catch (error: any) {
            const msg = error.response?.data?.fecha_desde || error.response?.data?.fecha_hasta
                || 'Error al buscar lotes.';
            toast.error(Array.isArray(msg) ? msg[0] : msg);
        } finally {
            setIsLoading(false);
        }
    };

    const limpiarFiltros = () => {
        setFiltros(FILTROS_INICIALES);
        setResultados([]);
        setCount(0);
        setPage(1);
        setHasSearched(false);
    };

    const handleReimpreso = async () => {
        // ReimprimirModal ya se encargó de imprimir (Zebra/PDF/portapapeles).
    };

    const handleReetiquetado = async () => {
        // ReetiquetarModal ya se encargó de imprimir; solo refrescamos resultados.
        buscar(page);
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2"><Search className="h-5 w-5" /> Buscador de Lotes</CardTitle>
                <CardDescription>Busca lotes históricos por fecha, turno, código o calidad para reimprimir su etiqueta.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <div className="space-y-1">
                        <Label className="text-xs">Desde</Label>
                        <Input
                            type="date"
                            value={filtros.fecha_desde}
                            onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Hasta</Label>
                        <Input
                            type="date"
                            value={filtros.fecha_hasta}
                            onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Turno</Label>
                        <Input
                            placeholder="Dia, Noche..."
                            value={filtros.turno}
                            onChange={(e) => setFiltros({ ...filtros, turno: e.target.value })}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Código de Lote</Label>
                        <Input
                            placeholder="OP-..."
                            value={filtros.codigo_lote}
                            onChange={(e) => setFiltros({ ...filtros, codigo_lote: e.target.value })}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Calidad</Label>
                        <Select
                            value={filtros.clasificacion_calidad || 'todas'}
                            onValueChange={(v) => setFiltros({ ...filtros, clasificacion_calidad: v === 'todas' ? '' : v })}
                        >
                            <SelectTrigger><SelectValue placeholder="Todas" /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="todas">Todas</SelectItem>
                                {CALIDAD_OPTIONS.map((c) => (
                                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button onClick={() => buscar(1)} disabled={isLoading}>
                        {isLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Search className="h-4 w-4 mr-2" />}
                        Buscar
                    </Button>
                    <Button variant="outline" onClick={limpiarFiltros} disabled={isLoading}>Limpiar</Button>
                </div>

                {hasSearched && (
                    <>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Lote</TableHead>
                                    <TableHead>Fecha</TableHead>
                                    <TableHead>Turno</TableHead>
                                    <TableHead>Peso Neto</TableHead>
                                    <TableHead>Calidad</TableHead>
                                    <TableHead>Acción</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {resultados.map((lote) => (
                                    <TableRow key={lote.id}>
                                        <TableCell className="font-medium">{lote.codigo_lote}</TableCell>
                                        <TableCell>{new Date(lote.hora_final).toLocaleDateString()}</TableCell>
                                        <TableCell>{lote.turno}</TableCell>
                                        <TableCell>{lote.peso_neto_producido} kg</TableCell>
                                        <TableCell>{lote.clasificacion_calidad || '-'}</TableCell>
                                        <TableCell>
                                            <div className="flex gap-1">
                                                <Button variant="ghost" size="sm" onClick={() => setReimprimirTarget(lote)} title="Reimprimir">
                                                    <Printer className="h-4 w-4" />
                                                </Button>
                                                {esSupervisor && (
                                                    <Button variant="ghost" size="sm" onClick={() => setReetiquetarTarget(lote)} title="Reetiquetar">
                                                        <Tag className="h-4 w-4" />
                                                    </Button>
                                                )}
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {resultados.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center text-muted-foreground">
                                            No se encontraron lotes con esos filtros.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                        {count > 0 && (
                            <div className="flex items-center justify-between mt-2">
                                <span className="text-sm text-muted-foreground">
                                    Página {page} de {totalPages} — {count} resultado(s)
                                </span>
                                <div className="flex items-center gap-2">
                                    <Button
                                        size="sm" variant="outline"
                                        onClick={() => buscar(Math.max(1, page - 1))}
                                        disabled={page === 1 || isLoading}
                                    >
                                        <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
                                    </Button>
                                    <Button
                                        size="sm" variant="outline"
                                        onClick={() => buscar(Math.min(totalPages, page + 1))}
                                        disabled={page === totalPages || isLoading}
                                    >
                                        Siguiente <ChevronRight className="w-4 h-4 ml-1" />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </CardContent>
            <ReimprimirModal
                open={reimprimirTarget !== null}
                onOpenChange={(open) => { if (!open) setReimprimirTarget(null); }}
                loteId={reimprimirTarget?.id ?? null}
                codigoLote={reimprimirTarget?.codigo_lote}
                onReimpreso={handleReimpreso}
            />
            {esSupervisor && (
                <ReetiquetarModal
                    open={reetiquetarTarget !== null}
                    onOpenChange={(open) => { if (!open) setReetiquetarTarget(null); }}
                    lote={reetiquetarTarget}
                    onReetiquetado={handleReetiquetado}
                />
            )}
        </Card>
    );
}
