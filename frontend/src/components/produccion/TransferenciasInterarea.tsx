import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Textarea } from '../ui/textarea';
import { AlertCircle, Plus, Send, CheckCircle2, Clock, ArrowRight } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';

interface Orden {
  id: number;
  codigo: string;
  // El serializer del backend expone `area` como PK (número) y el nombre por separado.
  area: number | null;
  area_nombre?: string;
}

interface Transferencia {
  id: number;
  orden_area_origen: Orden;
  orden_area_destino: Orden;
  cantidad_transferida: number;
  // El serializer expone las FK como PK y el nombre en campos `_nombre`.
  bodega_origen_nombre?: string;
  bodega_destino_nombre?: string;
  fecha_transferencia: string;
  usuario_responsable_nombre?: string;
  observaciones?: string;
}

export function TransferenciasInterarea({ areaId }: { areaId?: number }) {
  const [transferencias, setTransferencias] = useState<Transferencia[]>([]);
  const [ordenesDestino, setOrdenesDestino] = useState<Orden[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    orden_area_origen: '',
    orden_area_destino: '',
    cantidad_transferida: '',
    observaciones: ''
  });
  const [loading, setLoading] = useState(true);
  const [ordenesOrigen, setOrdenesOrigen] = useState<Orden[]>([]);

  useEffect(() => {
    fetchData();
  }, [areaId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [transRes, todasOrdenesRes, ordenesOrigenRes] = await Promise.all([
        apiClient.get('/transferencias-interarea/'),
        apiClient.get('/ordenes-produccion/'),
        areaId ? apiClient.get('/ordenes-produccion/?area=' + areaId) : Promise.resolve({ data: { results: [] } })
      ]);

      const todas = transRes.data.results || transRes.data;
      // Si areaId está definido, filtrar por ese área; si no, mostrar todas (jefe_planta)
      const transferenciasFiltrads = areaId
        ? todas.filter((t: Transferencia) => t.orden_area_origen?.area === areaId)
        : todas;
      setTransferencias(transferenciasFiltrads);

      const todasOrdenes = todasOrdenesRes.data.results || todasOrdenesRes.data;

      if (areaId) {
        // Para jefe_area: solo su área
        const miasOrdenes = ordenesOrigenRes.data.results || ordenesOrigenRes.data;
        setOrdenesOrigen(miasOrdenes);
        const ordenesOtrasAreas = todasOrdenes.filter((o: Orden) => o.area !== areaId);
        setOrdenesDestino(ordenesOtrasAreas);
      } else {
        // Para jefe_planta: todas las órdenes
        setOrdenesOrigen(todasOrdenes);
        setOrdenesDestino(todasOrdenes);
      }
    } catch (error) {
      toast.error('Error al cargar transferencias');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleTransferir = async () => {
    if (!formData.orden_area_destino || !formData.cantidad_transferida) {
      toast.error('Completa todos los campos');
      return;
    }

    const ordenOrigenId = areaId ? ordenesOrigen[0]?.id : parseInt(formData.orden_area_origen);
    const ordenDestinoId = parseInt(formData.orden_area_destino);

    if (!ordenOrigenId) {
      toast.error('No se encontró la orden de origen');
      return;
    }

    try {

      // Fetch the orders to get their bodega details
      const [ordenOrigenRes, ordenDestinoRes] = await Promise.all([
        apiClient.get(`/ordenes-produccion/${ordenOrigenId}/`),
        apiClient.get(`/ordenes-produccion/${ordenDestinoId}/`)
      ]);

      const ordenOrigen = ordenOrigenRes.data;
      const ordenDestino = ordenDestinoRes.data;

      const data = {
        orden_area_origen: ordenOrigenId,
        orden_area_destino: ordenDestinoId,
        bodega_origen: ordenOrigen.bodega_salida,
        bodega_destino: ordenDestino.bodega_entrada,
        cantidad_transferida: parseFloat(formData.cantidad_transferida),
        observaciones: formData.observaciones
      };

      await apiClient.post('/transferencias-interarea/', data);
      toast.success('Transferencia registrada correctamente');
      fetchData();
      setDialogOpen(false);
      setFormData({ orden_area_origen: '', orden_area_destino: '', cantidad_transferida: '', observaciones: '' });
    } catch (error) {
      toast.error('Error al registrar transferencia');
      console.error(error);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Cargando transferencias...</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ArrowRight className="w-5 h-5" />
                Transferencias a Otras Áreas
              </CardTitle>
              <CardDescription>
                Transfiere tu producción final a la siguiente área
              </CardDescription>
            </div>
            <Button onClick={() => setDialogOpen(true)} size="sm">
              <Plus className="w-4 h-4 mr-2" />
              Nueva Transferencia
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {transferencias.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No hay transferencias registradas aún</p>
            </div>
          ) : (
            <div className="space-y-4">
              {transferencias.map((trans) => (
                <div key={trans.id} className="border border-green-200 bg-green-50 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-green-600" />
                      <div>
                        <p className="font-semibold text-gray-900">
                          {trans.orden_area_origen?.codigo} → {trans.orden_area_destino?.codigo}
                        </p>
                        <p className="text-sm text-gray-600">
                          De {trans.bodega_origen_nombre} a {trans.bodega_destino_nombre}
                        </p>
                      </div>
                    </div>
                    <Badge className="bg-green-100 text-green-800">
                      {trans.cantidad_transferida} kg
                    </Badge>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {new Date(trans.fecha_transferencia).toLocaleString('es-ES')}
                    </div>
                    {trans.usuario_responsable_nombre && (
                      <div>
                        Registrado por: {trans.usuario_responsable_nombre}
                      </div>
                    )}
                  </div>

                  {trans.observaciones && (
                    <div className="mt-2 pt-2 border-t border-green-200">
                      <p className="text-sm text-gray-700">
                        <strong>Observaciones:</strong> {trans.observaciones}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog para nueva transferencia */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar Transferencia</DialogTitle>
            <DialogDescription>
              Transfiere la producción final a la siguiente área
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {areaId ? (
              <div>
                <Label>De tu Orden</Label>
                <div className="p-3 bg-gray-50 rounded border">
                  <p className="font-medium">{ordenesOrigen[0]?.codigo}</p>
                  <p className="text-sm text-gray-600">{ordenesOrigen[0]?.area_nombre}</p>
                </div>
              </div>
            ) : (
              <div>
                <Label htmlFor="origen">Orden de Origen</Label>
                <Select value={formData.orden_area_origen} onValueChange={(v) => setFormData({ ...formData, orden_area_origen: v })}>
                  <SelectTrigger id="origen">
                    <SelectValue placeholder="Selecciona la orden de origen" />
                  </SelectTrigger>
                  <SelectContent>
                    {ordenesOrigen.map((ord) => (
                      <SelectItem key={ord.id} value={ord.id.toString()}>
                        {ord.codigo} ({ord.area_nombre})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div>
              <Label htmlFor="destino">Área Destino (Nueva Orden)</Label>
              <Select value={formData.orden_area_destino} onValueChange={(v) => setFormData({ ...formData, orden_area_destino: v })}>
                <SelectTrigger id="destino">
                  <SelectValue placeholder="Selecciona la siguiente orden" />
                </SelectTrigger>
                <SelectContent>
                  {ordenesDestino.map((ord) => (
                    <SelectItem key={ord.id} value={ord.id.toString()}>
                      {ord.codigo} ({ord.area_nombre})
                    </SelectItem>
                  ))}
                  {ordenesDestino.length === 0 && (
                    <SelectItem value="" disabled>
                      No hay órdenes en otras áreas
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="cantidad">Cantidad a Transferir (kg)</Label>
              <Input
                id="cantidad"
                type="number"
                step="0.01"
                placeholder="100.50"
                value={formData.cantidad_transferida}
                onChange={(e) => setFormData({ ...formData, cantidad_transferida: e.target.value })}
              />
            </div>

            <div>
              <Label htmlFor="obs">Observaciones</Label>
              <Textarea
                id="obs"
                placeholder="Ej: Sin defectos, lista para continuar procesamiento"
                value={formData.observaciones}
                onChange={(e) => setFormData({ ...formData, observaciones: e.target.value })}
                className="resize-none"
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleTransferir} className="gap-2">
              <Send className="w-4 h-4" />
              Transferir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
