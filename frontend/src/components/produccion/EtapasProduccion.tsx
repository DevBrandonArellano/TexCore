import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { AlertCircle, Plus, Edit2, Trash2, ChevronRight, Clock, Box } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';

interface Etapa {
  id: number;
  area: number;
  nombre: string;
  orden: number;
  maquina: {
    id?: number;
    nombre: string;
  };
  bodega_entrada: {
    id?: number;
    nombre: string;
  };
  bodega_salida: {
    id?: number;
    nombre: string;
  };
  tiempo_procesamiento_minutos?: number;
}

interface Maquina {
  id: number;
  nombre: string;
}

interface Bodega {
  id: number;
  nombre: string;
}

export function EtapasProduccion({ areaId }: { areaId: number }) {
  const [etapas, setEtapas] = useState<Etapa[]>([]);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEtapa, setEditingEtapa] = useState<Etapa | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    orden: '',
    maquina: '',
    bodega_entrada: '',
    bodega_salida: '',
    tiempo_procesamiento_minutos: ''
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [areaId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [etapasRes, maquinasRes, bodegasRes] = await Promise.all([
        apiClient.get(`/etapas-produccion/?area=${areaId}`),
        apiClient.get('/maquinas/?area=' + areaId),
        apiClient.get('/bodegas/')
      ]);

      setEtapas(etapasRes.data.results || etapasRes.data);
      setMaquinas(maquinasRes.data.results || maquinasRes.data);
      setBodegas(bodegasRes.data.results || bodegasRes.data);
    } catch (error) {
      toast.error('Error al cargar etapas de producción');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (etapa?: Etapa) => {
    if (etapa) {
      setEditingEtapa(etapa);
      setFormData({
        nombre: etapa.nombre,
        orden: etapa.orden.toString(),
        maquina: etapa.maquina.id?.toString() ?? '',
        bodega_entrada: etapa.bodega_entrada.id?.toString() ?? '',
        bodega_salida: etapa.bodega_salida.id?.toString() ?? '',
        tiempo_procesamiento_minutos: etapa.tiempo_procesamiento_minutos?.toString() || ''
      });
    } else {
      setEditingEtapa(null);
      setFormData({
        nombre: '',
        orden: (Math.max(...etapas.map(e => e.orden), 0) + 1).toString(),
        maquina: '',
        bodega_entrada: '',
        bodega_salida: '',
        tiempo_procesamiento_minutos: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      const data = {
        area: areaId,
        nombre: formData.nombre,
        orden: parseInt(formData.orden),
        maquina: parseInt(formData.maquina),
        bodega_entrada: parseInt(formData.bodega_entrada),
        bodega_salida: parseInt(formData.bodega_salida),
        tiempo_procesamiento_minutos: formData.tiempo_procesamiento_minutos ?
          parseInt(formData.tiempo_procesamiento_minutos) : null
      };

      if (editingEtapa?.id) {
        await apiClient.patch(`/etapas-produccion/${editingEtapa.id}/`, data);
        toast.success('Etapa actualizada correctamente');
      } else {
        await apiClient.post('/etapas-produccion/', data);
        toast.success('Etapa creada correctamente');
      }

      fetchData();
      setDialogOpen(false);
    } catch (error) {
      toast.error('Error al guardar la etapa');
      console.error(error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('¿Deseas eliminar esta etapa?')) return;

    try {
      await apiClient.delete(`/etapas-produccion/${id}/`);
      toast.success('Etapa eliminada correctamente');
      fetchData();
    } catch (error) {
      toast.error('Error al eliminar la etapa');
      console.error(error);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Cargando etapas...</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Box className="w-5 h-5" />
                Etapas de Producción
              </CardTitle>
              <CardDescription>
                Configura los procesos secuenciales de tu área
              </CardDescription>
            </div>
            <Button onClick={() => handleOpenDialog()} size="sm">
              <Plus className="w-4 h-4 mr-2" />
              Nueva Etapa
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {etapas.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No hay etapas configuradas. Crea la primera etapa para comenzar.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {etapas.map((etapa, idx) => (
                <div key={etapa.id} className="relative">
                  <div className="bg-gradient-to-r from-blue-50 to-transparent border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <Badge className="bg-blue-100 text-blue-800">
                          Etapa {etapa.orden}
                        </Badge>
                        <h3 className="font-semibold text-gray-900">{etapa.nombre}</h3>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleOpenDialog(etapa)}
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600 hover:text-red-800"
                          onClick={() => handleDelete(etapa.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-gray-600 mb-1">Máquina</p>
                        <p className="font-medium">{etapa.maquina.nombre}</p>
                      </div>
                      <div>
                        <p className="text-gray-600 mb-1">Bodega Entrada</p>
                        <p className="font-medium text-green-700">{etapa.bodega_entrada.nombre}</p>
                      </div>
                      <div>
                        <p className="text-gray-600 mb-1">Bodega Salida</p>
                        <p className="font-medium text-orange-700">{etapa.bodega_salida.nombre}</p>
                      </div>
                    </div>

                    {etapa.tiempo_procesamiento_minutos && (
                      <div className="mt-3 flex items-center gap-2 text-sm">
                        <Clock className="w-4 h-4 text-gray-500" />
                        <span className="text-gray-700">
                          {etapa.tiempo_procesamiento_minutos} minutos
                        </span>
                      </div>
                    )}
                  </div>

                  {idx < etapas.length - 1 && (
                    <div className="flex justify-center -my-2">
                      <ChevronRight className="w-5 h-5 text-gray-400 rotate-90" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog para crear/editar etapa */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingEtapa ? 'Editar Etapa' : 'Nueva Etapa de Producción'}
            </DialogTitle>
            <DialogDescription>
              Configura los detalles de esta etapa de producción
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="nombre">Nombre de la Etapa</Label>
              <Input
                id="nombre"
                placeholder="ej. Teñido, Secado, Empaque"
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              />
            </div>

            <div>
              <Label htmlFor="orden">Orden Secuencial</Label>
              <Input
                id="orden"
                type="number"
                min="1"
                value={formData.orden}
                onChange={(e) => setFormData({ ...formData, orden: e.target.value })}
              />
            </div>

            <div>
              <Label htmlFor="maquina">Máquina</Label>
              <Select value={formData.maquina} onValueChange={(v) => setFormData({ ...formData, maquina: v })}>
                <SelectTrigger id="maquina">
                  <SelectValue placeholder="Selecciona una máquina" />
                </SelectTrigger>
                <SelectContent>
                  {maquinas.map((m) => (
                    <SelectItem key={m.id} value={m.id.toString()}>
                      {m.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="bodega_entrada">Bodega Entrada (MP)</Label>
              <Select value={formData.bodega_entrada} onValueChange={(v) => setFormData({ ...formData, bodega_entrada: v })}>
                <SelectTrigger id="bodega_entrada">
                  <SelectValue placeholder="Selecciona bodega" />
                </SelectTrigger>
                <SelectContent>
                  {bodegas.map((b) => (
                    <SelectItem key={b.id} value={b.id.toString()}>
                      {b.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="bodega_salida">Bodega Salida (PT)</Label>
              <Select value={formData.bodega_salida} onValueChange={(v) => setFormData({ ...formData, bodega_salida: v })}>
                <SelectTrigger id="bodega_salida">
                  <SelectValue placeholder="Selecciona bodega" />
                </SelectTrigger>
                <SelectContent>
                  {bodegas.map((b) => (
                    <SelectItem key={b.id} value={b.id.toString()}>
                      {b.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="tiempo">Tiempo Estimado (minutos)</Label>
              <Input
                id="tiempo"
                type="number"
                placeholder="120"
                value={formData.tiempo_procesamiento_minutos}
                onChange={(e) => setFormData({ ...formData, tiempo_procesamiento_minutos: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave}>
              {editingEtapa ? 'Actualizar' : 'Crear'} Etapa
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
