
import React from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../ui/table';
import { Skeleton } from '../ui/skeleton';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import apiClient from '../../lib/axios';
import { AuditoriaMovimiento } from '../../lib/types';
import { useCargaRemota } from '../../hooks/useCargaRemota';

interface AuditoriaDialogProps {
    movimientoId: number | null;
    open: boolean;
    onClose: () => void;
}

export function AuditoriaDialog({ movimientoId, open, onClose }: AuditoriaDialogProps) {
    // Se pide al abrir; si falla se registra y se muestra el historial vacío.
    const { datos, cargando: loading } = useCargaRemota(
        () => apiClient
            .get<AuditoriaMovimiento[]>(`/inventory/movimientos/${movimientoId}/auditoria/`)
            .then((response) => response.data)
            .catch((error): AuditoriaMovimiento[] => {
                console.error("Error fetching auditoria:", error);
                return [];
            }),
        movimientoId,
        { habilitado: Boolean(movimientoId) && open },
    );
    const auditorias = datos ?? [];

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Historial de Cambios</DialogTitle>
                    <DialogDescription>
                        Registro de modificaciones realizadas a este movimiento.
                    </DialogDescription>
                </DialogHeader>

                <div className="mt-4">
                    {loading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-8 w-full" />
                            <Skeleton className="h-8 w-full" />
                            <Skeleton className="h-8 w-full" />
                        </div>
                    ) : auditorias.length === 0 ? (
                        <p className="text-center text-muted-foreground py-4">No hay historial de cambios registrado.</p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Fecha</TableHead>
                                    <TableHead>Usuario</TableHead>
                                    <TableHead>Campo</TableHead>
                                    <TableHead>Valor Ant.</TableHead>
                                    <TableHead>Valor Nuevo</TableHead>
                                    <TableHead>Razón</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {auditorias.map((log) => (
                                    <TableRow key={log.id}>
                                        <TableCell className="text-xs">
                                            {format(new Date(log.fecha_modificacion), "dd/MM/yy HH:mm", { locale: es })}
                                        </TableCell>
                                        <TableCell className="text-xs">{log.usuario_modificador_nombre}</TableCell>
                                        <TableCell className="text-xs font-medium">{log.campo_modificado}</TableCell>
                                        <TableCell className="text-xs text-muted-foreground line-through decoration-destructive/50">
                                            {log.valor_anterior}
                                        </TableCell>
                                        <TableCell className="text-xs text-green-600 font-medium">
                                            {log.valor_nuevo}
                                        </TableCell>
                                        <TableCell className="text-xs italic max-w-[150px] truncate" title={log.razon_cambio}>
                                            {log.razon_cambio}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
