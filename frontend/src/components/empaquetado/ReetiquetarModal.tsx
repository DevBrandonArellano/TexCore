import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Alert, AlertDescription } from '../ui/alert';
import { Checkbox } from '../ui/checkbox';
import { Loader2, Tag, TriangleAlert, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { LoteProduccion } from '../../lib/types';
import { printLabel } from '../../lib/printing';
import { useAuth } from '../../lib/auth';

const MENSAJE_POR_RESULTADO: Record<string, string> = {
    zebra: 'Enviada a la impresora Zebra.',
    pdf: 'PDF generado — se abrió el diálogo de impresión.',
    clipboard: 'Código ZPL copiado al portapapeles (sin impresora disponible).',
};

const MOTIVOS = [
    { value: 'CORRECCION_PESO', label: 'Corrección de Peso' },
    { value: 'RECLASIFICACION', label: 'Reclasificación de Calidad' },
    { value: 'REEMPAQUE', label: 'Reempaque' },
    { value: 'OTRO', label: 'Otro' },
];

const CALIDAD_OPTIONS = [
    { value: 'primera', label: 'Primera Calidad' },
    { value: 'segunda', label: 'Segunda Calidad' },
    { value: 'saldo', label: 'Saldo / Retazo' },
];

const SUPERVISOR_ROLES = new Set(['jefe_area', 'jefe_planta', 'admin_sistemas', 'admin_sede']);

interface ReetiquetarModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    lote: LoteProduccion | null;
    onReetiquetado?: (zpl: string) => void;
}

export function ReetiquetarModal({ open, onOpenChange, lote, onReetiquetado }: ReetiquetarModalProps) {
    const { profile } = useAuth();
    const [motivo, setMotivo] = useState('');
    const [detalleMotivo, setDetalleMotivo] = useState('');
    const [pesoNeto, setPesoNeto] = useState('');
    const [calidad, setCalidad] = useState('');
    const [supervisorUsername, setSupervisorUsername] = useState('');
    const [supervisorPassword, setSupervisorPassword] = useState('');
    const [confirmTolerancia, setConfirmTolerancia] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const isCurrentSupervisor = Boolean(profile?.role && SUPERVISOR_ROLES.has(profile.role));

    useEffect(() => {
        if (lote) {
            setPesoNeto(String(lote.peso_neto_producido ?? ''));
            setCalidad(lote.clasificacion_calidad ?? '');
            setSupervisorUsername('');
            setSupervisorPassword('');
            setConfirmTolerancia(false);
        }
    }, [lote]);

    const origPeso = Number(lote?.peso_neto_producido ?? 0);
    const newPeso = Number(pesoNeto || 0);
    const desvioRelativo = origPeso > 0 ? Math.abs(newPeso - origPeso) / origPeso : 0;
    const isOutTolerance = origPeso > 0 && desvioRelativo > 0.10;

    const handleClose = (nextOpen: boolean) => {
        if (!isSubmitting) {
            if (!nextOpen) {
                setMotivo('');
                setDetalleMotivo('');
                setSupervisorUsername('');
                setSupervisorPassword('');
                setConfirmTolerancia(false);
            }
            onOpenChange(nextOpen);
        }
    };

    const handleConfirmar = async () => {
        if (!lote) return;
        if (!motivo) {
            toast.error('Selecciona un motivo para reetiquetar.');
            return;
        }

        if (isOutTolerance && !confirmTolerancia) {
            toast.error('El peso difiere más del 10%. Por favor marca la casilla de confirmación.');
            return;
        }

        if (!isCurrentSupervisor && (!supervisorUsername || !supervisorPassword)) {
            toast.error('Ingresa el usuario y contraseña del Jefe de Área o Supervisor.');
            return;
        }

        const cambios: Record<string, number | string> = {};
        if (pesoNeto !== '' && Number(pesoNeto) !== lote.peso_neto_producido) {
            cambios.peso_neto_producido = Number(pesoNeto);
        }
        if (calidad && calidad !== lote.clasificacion_calidad) {
            cambios.clasificacion_calidad = calidad;
        }
        if (Object.keys(cambios).length === 0) {
            toast.error('Debes modificar al menos un dato (peso neto o calidad).');
            return;
        }

        const payload: Record<string, unknown> = {
            cambios,
            motivo,
            detalle_motivo: detalleMotivo,
            formato: 'ZPL',
        };

        if (!isCurrentSupervisor) {
            payload.supervisor_username = supervisorUsername;
            payload.supervisor_password = supervisorPassword;
        }

        setIsSubmitting(true);
        try {
            const res = await apiClient.post<{ zpl: string; evento: { version: number } }>(
                `/lotes-produccion/${lote.id}/reetiquetar/`,
                payload
            );
            const resultado = await printLabel(lote.id, res.data.zpl);
            toast.success(`Lote reetiquetado (v${res.data.evento.version}). Etiqueta anterior anulada. ${MENSAJE_POR_RESULTADO[resultado]}`);
            onReetiquetado?.(res.data.zpl);
            handleClose(false);
        } catch (error: any) {
            const msg = error.response?.data?.error?.message || error.response?.data?.detail || 'Error al reetiquetar el lote.';
            toast.error(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2"><Tag className="h-4 w-4" /> Reetiquetar Lote</DialogTitle>
                    <DialogDescription>
                        {lote ? `Lote ${lote.codigo_lote} — ` : ''}
                        Cambia datos de la etiqueta. La versión anterior queda anulada; el código de lote no cambia.
                    </DialogDescription>
                </DialogHeader>
                <Alert variant="destructive" className="py-2">
                    <TriangleAlert className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                        Esta acción requiere validación de usuario y contraseña de Jefe de Área y queda registrada en auditoría.
                    </AlertDescription>
                </Alert>
                <div className="space-y-4 py-2">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <Label>Peso Neto (kg)</Label>
                            <Input
                                type="number" step="0.001"
                                value={pesoNeto}
                                onChange={(e) => setPesoNeto(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Calidad</Label>
                            <Select value={calidad} onValueChange={setCalidad}>
                                <SelectTrigger><SelectValue placeholder="Sin cambio" /></SelectTrigger>
                                <SelectContent>
                                    {CALIDAD_OPTIONS.map((c) => (
                                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {isOutTolerance && (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-md space-y-2">
                            <div className="flex items-center gap-2 text-amber-800 text-xs font-semibold">
                                <TriangleAlert className="h-4 w-4 text-amber-600" />
                                <span>El nuevo peso ({newPeso} kg) difiere más del 10% del peso original ({origPeso} kg).</span>
                            </div>
                            <div className="flex items-center space-x-2 pt-1">
                                <Checkbox
                                    id="confirmToleranciaReetiquetar"
                                    checked={confirmTolerancia}
                                    onCheckedChange={(c) => setConfirmTolerancia(Boolean(c))}
                                />
                                <label htmlFor="confirmToleranciaReetiquetar" className="text-xs text-amber-900 cursor-pointer">
                                    Confirmar desvío de peso deliberado
                                </label>
                            </div>
                        </div>
                    )}

                    <div className="space-y-2">
                        <Label>Motivo *</Label>
                        <Select value={motivo} onValueChange={setMotivo}>
                            <SelectTrigger><SelectValue placeholder="Selecciona un motivo" /></SelectTrigger>
                            <SelectContent>
                                {MOTIVOS.map((m) => (
                                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-2">
                        <Label>Detalle (opcional)</Label>
                        <Textarea
                            value={detalleMotivo}
                            onChange={(e) => setDetalleMotivo(e.target.value)}
                            placeholder="Ej: re-pesaje en báscula certificada tras reclamo de cliente"
                        />
                    </div>

                    {!isCurrentSupervisor ? (
                        <div className="space-y-3 border-t pt-3 bg-slate-50 p-3 rounded-md border">
                            <Label className="text-xs font-bold text-slate-800 flex items-center gap-1">
                                <ShieldCheck className="h-4 w-4 text-blue-600" /> Validación de Jefe de Área / Supervisor *
                            </Label>
                            <div className="grid grid-cols-2 gap-2">
                                <div className="space-y-1">
                                    <Label className="text-[11px]">Usuario Jefe</Label>
                                    <Input
                                        placeholder="ej: jefe_area1"
                                        value={supervisorUsername}
                                        onChange={(e) => setSupervisorUsername(e.target.value)}
                                        className="h-8 text-xs bg-white"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-[11px]">Contraseña</Label>
                                    <Input
                                        type="password"
                                        placeholder="••••••••"
                                        value={supervisorPassword}
                                        onChange={(e) => setSupervisorPassword(e.target.value)}
                                        className="h-8 text-xs bg-white"
                                    />
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex items-center gap-1.5 text-xs text-green-700 bg-green-50 p-2 rounded border border-green-200">
                            <ShieldCheck className="h-4 w-4" />
                            <span>Autorizando como <strong>{profile?.user.username}</strong> ({profile?.role})</span>
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => handleClose(false)} disabled={isSubmitting}>
                        Cancelar
                    </Button>
                    <Button onClick={handleConfirmar} disabled={isSubmitting || !motivo} variant="destructive">
                        {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Tag className="h-4 w-4 mr-2" />}
                        Reetiquetar Lote
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

