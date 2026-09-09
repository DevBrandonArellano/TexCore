import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Loader2, FileText } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';

const MOTIVOS_TRASLADO = [
  'Venta',
  'Transferencia entre bodegas propias',
  'Consignación',
  'Devolución',
  'Exportación',
  'Importación',
  'Otro',
];

interface GuiaRemisionModalProps {
  despachoId: number | null;
  onOpenChange: (open: boolean) => void;
}

export function GuiaRemisionModal({ despachoId, onOpenChange }: GuiaRemisionModalProps) {
  const [motivoTraslado, setMotivoTraslado] = useState('Venta');
  const [puntoPartida, setPuntoPartida] = useState('');
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [transportePropio, setTransportePropio] = useState(true);
  const [placaVehiculo, setPlacaVehiculo] = useState('');
  const [transportistaNombre, setTransportistaNombre] = useState('');
  const [transportistaRuc, setTransportistaRuc] = useState('');
  const [generando, setGenerando] = useState(false);

  const resetForm = () => {
    setMotivoTraslado('Venta');
    setPuntoPartida('');
    setFechaInicio('');
    setFechaFin('');
    setTransportePropio(true);
    setPlacaVehiculo('');
    setTransportistaNombre('');
    setTransportistaRuc('');
  };

  const handleClose = (open: boolean) => {
    if (!open) resetForm();
    onOpenChange(open);
  };

  const handleGenerar = async () => {
    if (!despachoId) return;
    if (!puntoPartida.trim() || !fechaInicio || !fechaFin) {
      toast.error('Completa punto de partida y fechas de transporte.');
      return;
    }
    if (!transportePropio && !transportistaNombre.trim()) {
      toast.error('Indica el nombre del transportista contratado.');
      return;
    }

    setGenerando(true);
    try {
      const response = await apiClient.post(
        `/inventory/historial-despachos/${despachoId}/guia-remision/`,
        {
          motivo_traslado: motivoTraslado,
          punto_partida: puntoPartida,
          fecha_inicio_transporte: fechaInicio,
          fecha_fin_transporte: fechaFin,
          transporte_propio: transportePropio,
          placa_vehiculo: placaVehiculo || undefined,
          transportista_nombre: transportePropio ? undefined : transportistaNombre,
          transportista_ruc: transportePropio ? undefined : transportistaRuc,
        },
        { responseType: 'blob' },
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      window.open(url, '_blank');
      toast.success('Guía de remisión generada.');
      handleClose(false);
    } catch (error: any) {
      console.error('Error generando guía de remisión', error);
      toast.error(
        error.response?.data?.motivo_traslado ||
        error.response?.data?.punto_partida ||
        error.response?.data?.error ||
        'Error al generar la guía de remisión.',
      );
    } finally {
      setGenerando(false);
    }
  };

  return (
    <Dialog open={despachoId !== null} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            Generar Guía de Remisión
          </DialogTitle>
          <DialogDescription>
            Documento informativo de acompañamiento de mercadería (no es un comprobante
            electrónico autorizado por el SRI).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="motivo-traslado">Motivo del traslado</Label>
            <Select value={motivoTraslado} onValueChange={setMotivoTraslado}>
              <SelectTrigger id="motivo-traslado">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MOTIVOS_TRASLADO.map((m) => (
                  <SelectItem key={m} value={m}>{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="punto-partida">Punto de partida *</Label>
            <Input
              id="punto-partida"
              value={puntoPartida}
              onChange={(e) => setPuntoPartida(e.target.value)}
              placeholder="Ej. Planta Quito, Av. Industrial s/n"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="fecha-inicio-transporte">Inicio de transporte *</Label>
              <Input
                id="fecha-inicio-transporte"
                type="datetime-local"
                value={fechaInicio}
                onChange={(e) => setFechaInicio(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="fecha-fin-transporte">Fin de transporte *</Label>
              <Input
                id="fecha-fin-transporte"
                type="datetime-local"
                value={fechaFin}
                onChange={(e) => setFechaFin(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="transporte-propio"
              checked={transportePropio}
              onCheckedChange={(checked) => setTransportePropio(checked === true)}
            />
            <Label htmlFor="transporte-propio" className="cursor-pointer">Transporte propio</Label>
          </div>

          {!transportePropio && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="transportista-nombre">Transportista (razón social) *</Label>
                <Input
                  id="transportista-nombre"
                  value={transportistaNombre}
                  onChange={(e) => setTransportistaNombre(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="transportista-ruc">RUC transportista</Label>
                <Input
                  id="transportista-ruc"
                  value={transportistaRuc}
                  onChange={(e) => setTransportistaRuc(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="placa-vehiculo">Placa del vehículo</Label>
            <Input
              id="placa-vehiculo"
              value={placaVehiculo}
              onChange={(e) => setPlacaVehiculo(e.target.value)}
              placeholder="Ej. PBX-1234"
              className="font-mono"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)} disabled={generando}>
            Cancelar
          </Button>
          <Button onClick={handleGenerar} disabled={generando} className="gap-2">
            {generando ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
            Generar Guía
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default GuiaRemisionModal;
