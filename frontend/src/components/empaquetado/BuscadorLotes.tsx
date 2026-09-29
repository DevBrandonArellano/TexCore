import React, { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { Search, Printer, Tag, Loader2, History, Eye } from 'lucide-react';
import { toast } from 'sonner';
import { LoteProduccion } from '../../lib/types';
import { useAuth } from '../../lib/auth';
import { lotesApi } from '../../lib/api/lotesApi';
import type { FiltrosLotes } from '../../types/lotes';
import { usePaginacionIncremental } from '../../hooks/usePaginacionIncremental';
import { ControlesPaginacion } from '../ui/controles-paginacion';
import { FichaLoteDialog } from '../lotes/FichaLoteDialog';
import { ReimprimirModal } from './ReimprimirModal';
import { ReetiquetarModal } from './ReetiquetarModal';
import { HistorialEtiquetasModal } from './HistorialEtiquetasModal';

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

/** Solo los filtros con valor; el backend ignora los ausentes. */
function aParametros(filtros: Filtros): FiltrosLotes {
    const parametros: FiltrosLotes = { ordering: '-hora_final' };
    (Object.keys(filtros) as (keyof Filtros)[]).forEach((clave) => {
        if (filtros[clave]) parametros[clave] = filtros[clave];
    });
    return parametros;
}

export function BuscadorLotes() {
    const { profile } = useAuth();
    const esSupervisor = !!profile?.role && ROLES_SUPERVISOR.includes(profile.role);

    const [filtros, setFiltros] = useState<Filtros>(FILTROS_INICIALES);
    // Filtros de la última búsqueda: cambiar de objeto reinicia la paginación.
    const [filtrosAplicados, setFiltrosAplicados] = useState<Filtros | null>(null);
    const [reimprimirTarget, setReimprimirTarget] = useState<LoteProduccion | null>(null);
    const [reetiquetarTarget, setReetiquetarTarget] = useState<LoteProduccion | null>(null);
    const [historialTarget, setHistorialTarget] = useState<LoteProduccion | null>(null);
    const [fichaTarget, setFichaTarget] = useState<LoteProduccion | null>(null);

    const obtenerBloque = useCallback(
        (bloque: number, tamano: number) => lotesApi.listar(bloque, tamano, aParametros(filtrosAplicados ?? FILTROS_INICIALES)),
        [filtrosAplicados],
    );
    const resultados = usePaginacionIncremental<LoteProduccion>({
        obtenerBloque,
        resetKey: filtrosAplicados,
        habilitado: filtrosAplicados !== null,
    });
    const hasSearched = filtrosAplicados !== null;

    useEffect(() => {
        if (resultados.error) toast.error(resultados.error);
    }, [resultados.error]);

    const buscar = () => setFiltrosAplicados({ ...filtros });

    const limpiarFiltros = () => {
        setFiltros(FILTROS_INICIALES);
        setFiltrosAplicados(null);
    };

    // ReetiquetarModal ya imprimió; solo se refresca la página visible.
    const handleReetiquetado = () => resultados.recargar();

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
                    <Button onClick={buscar} disabled={resultados.cargando}>
                        {resultados.cargando ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Search className="h-4 w-4 mr-2" />}
                        Buscar
                    </Button>
                    <Button variant="outline" onClick={limpiarFiltros} disabled={resultados.cargando}>Limpiar</Button>
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
                                {resultados.paginatedItems.map((lote) => (
                                    <TableRow key={lote.id}>
                                        <TableCell className="font-medium">
                                            <div className="flex flex-col gap-0.5">
                                                <span className="font-mono">{lote.codigo_lote}</span>
                                                {lote.pedido_venta_reserva && (
                                                    <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-[10px] w-fit px-1.5 py-0">
                                                        MTO: Pedido #{lote.pedido_venta_reserva}
                                                    </Badge>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell>{new Date(lote.hora_final).toLocaleDateString()}</TableCell>
                                        <TableCell>{lote.turno}</TableCell>
                                        <TableCell>{lote.peso_neto_producido} kg</TableCell>
                                        <TableCell>{lote.clasificacion_calidad || '-'}</TableCell>
                                        <TableCell>
                                            <div className="flex gap-1">
                                                <Button variant="ghost" size="sm" onClick={() => setFichaTarget(lote)} title="Ver ficha del lote" aria-label="Ver ficha">
                                                    <Eye className="h-4 w-4" />
                                                </Button>
                                                <Button variant="ghost" size="sm" onClick={() => setReimprimirTarget(lote)} title="Reimprimir">
                                                    <Printer className="h-4 w-4" />
                                                </Button>
                                                <Button variant="ghost" size="sm" onClick={() => setHistorialTarget(lote)} title="Ver historial de etiquetas">
                                                    <History className="h-4 w-4" />
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
                                {resultados.count === 0 && !resultados.cargando && (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center text-muted-foreground">
                                            No se encontraron lotes con esos filtros.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                        {resultados.count > 0 && (
                            <ControlesPaginacion
                                currentPage={resultados.currentPage}
                                totalPages={resultados.totalPages}
                                setCurrentPage={resultados.setCurrentPage}
                                total={resultados.count}
                                cargando={resultados.cargando}
                            />
                        )}
                    </>
                )}
            </CardContent>
            <ReimprimirModal
                open={reimprimirTarget !== null}
                onOpenChange={(open) => { if (!open) setReimprimirTarget(null); }}
                loteId={reimprimirTarget?.id ?? null}
                codigoLote={reimprimirTarget?.codigo_lote}
            />
            {esSupervisor && (
                <ReetiquetarModal
                    open={reetiquetarTarget !== null}
                    onOpenChange={(open) => { if (!open) setReetiquetarTarget(null); }}
                    lote={reetiquetarTarget}
                    onReetiquetado={handleReetiquetado}
                />
            )}
            <FichaLoteDialog lote={fichaTarget} onClose={() => setFichaTarget(null)} />
            <HistorialEtiquetasModal
                open={historialTarget !== null}
                onOpenChange={(open) => { if (!open) setHistorialTarget(null); }}
                loteId={historialTarget?.id ?? null}
                codigoLote={historialTarget?.codigo_lote}
            />
        </Card>
    );
}
