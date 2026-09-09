import React, { useEffect, useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Loader2, Printer, History } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { ReimprimirModal } from './ReimprimirModal';

interface EventoEtiqueta {
    id: number;
    tipo_evento: 'ORIGINAL' | 'REIMPRESION' | 'REETIQUETADO';
    secuencia: number;
    version: number;
    motivo: string | null;
    detalle_motivo: string;
    usuario: string | null;
    timestamp: string;
    formato: 'ZPL' | 'PDF';
    anulada: boolean;
    anula_a: number | null;
}

const TIPO_LABEL: Record<EventoEtiqueta['tipo_evento'], string> = {
    ORIGINAL: 'Original',
    REIMPRESION: 'Reimpresión',
    REETIQUETADO: 'Reetiquetado',
};

interface HistorialEtiquetasModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    loteId: number | null;
    codigoLote?: string;
}

export function HistorialEtiquetasModal({ open, onOpenChange, loteId, codigoLote }: HistorialEtiquetasModalProps) {
    const [eventos, setEventos] = useState<EventoEtiqueta[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [reimprimirOpen, setReimprimirOpen] = useState(false);

    useEffect(() => {
        if (!open || !loteId) return;
        cargarHistorial();
    }, [open, loteId]);

    const cargarHistorial = async () => {
        if (!loteId) return;
        setIsLoading(true);
        try {
            const res = await apiClient.get<EventoEtiqueta[]>(`/lotes-produccion/${loteId}/etiquetas/`);
            setEventos(res.data);
        } catch (error) {
            console.error('Error cargando historial de etiquetas', error);
            toast.error('Error al cargar el historial de etiquetas.');
        } finally {
            setIsLoading(false);
        }
    };

    const vigente = eventos.find((e) => !e.anulada);

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <History className="w-5 h-5 text-primary" />
                            Historial de Etiquetas
                        </DialogTitle>
                        <DialogDescription>
                            {codigoLote ? `Lote ${codigoLote} — ` : ''}
                            Cada impresión física queda registrada aquí (original, reimpresiones y reetiquetados).
                        </DialogDescription>
                    </DialogHeader>

                    {isLoading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Secuencia</TableHead>
                                    <TableHead>Tipo</TableHead>
                                    <TableHead>Versión</TableHead>
                                    <TableHead>Motivo</TableHead>
                                    <TableHead>Usuario</TableHead>
                                    <TableHead>Fecha</TableHead>
                                    <TableHead>Estado</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {eventos.map((e) => (
                                    <TableRow key={e.id}>
                                        <TableCell className="font-mono">{e.secuencia}</TableCell>
                                        <TableCell>{TIPO_LABEL[e.tipo_evento]}</TableCell>
                                        <TableCell className="font-mono">v{e.version}</TableCell>
                                        <TableCell>{e.motivo || '—'}</TableCell>
                                        <TableCell>{e.usuario || '—'}</TableCell>
                                        <TableCell className="text-xs text-muted-foreground">
                                            {format(new Date(e.timestamp), 'dd MMM yyyy HH:mm', { locale: es })}
                                        </TableCell>
                                        <TableCell>
                                            {e.anulada ? (
                                                <Badge variant="outline" className="text-slate-500">Anulada</Badge>
                                            ) : (
                                                <Badge variant="outline" className="text-green-600 bg-green-50 border-green-200">
                                                    Vigente
                                                </Badge>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {eventos.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={7} className="text-center text-muted-foreground">
                                            Sin eventos de etiqueta registrados.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => onOpenChange(false)}>
                            Cerrar
                        </Button>
                        <Button
                            onClick={() => setReimprimirOpen(true)}
                            disabled={!vigente}
                            className="gap-2"
                            title={vigente ? undefined : 'No hay una etiqueta vigente para reimprimir'}
                        >
                            <Printer className="w-4 h-4" />
                            Reimprimir etiqueta vigente
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <ReimprimirModal
                open={reimprimirOpen}
                onOpenChange={setReimprimirOpen}
                loteId={loteId}
                codigoLote={codigoLote}
                onReimpreso={cargarHistorial}
            />
        </>
    );
}

export default HistorialEtiquetasModal;
