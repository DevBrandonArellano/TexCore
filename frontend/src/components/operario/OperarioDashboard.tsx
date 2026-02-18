import React, { useState, useEffect } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { OrdenProduccion, LoteProduccion } from '../../lib/types';
import { Package, Scale, ClipboardList, Timer } from 'lucide-react';
import { Badge } from '../ui/badge';

export function OperarioDashboard() {
  const { profile } = useAuth();
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrden, setSelectedOrden] = useState<OrdenProduccion | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form State for Lote
  const [pesoNeto, setPesoNeto] = useState('');
  const [bobinas, setBobinas] = useState('1');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchOrdenes();
  }, []);

  const fetchOrdenes = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get<OrdenProduccion[]>('/ordenes-produccion/');
      // Filter locally just in case, but backend should handle it
      // We only care about active orders for the operator
      const active = res.data.filter(o => o.estado === 'en_proceso');
      setOrdenes(active);
    } catch (error) {
      console.error('Error al cargar órdenes', error);
      toast.error('No se pudieron cargar tus asignaciones.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenRegistro = (orden: OrdenProduccion) => {
    setSelectedOrden(orden);
    setPesoNeto('');
    setBobinas('1');
    setIsDialogOpen(true);
  };

  const handleRegistrarLote = async () => {
    if (!selectedOrden || !pesoNeto) return;

    setIsSubmitting(true);
    try {
      const now = new Date();
      // Simple logic: Start time is now - 1 hour (approx) or just now for logging
      // In a real app, the operator would "Start" then "Stop".
      // Assuming straightforward registration here.

      const payload = {
        codigo_lote: `${selectedOrden.codigo}-L${Math.floor(Math.random() * 1000)}`, // Backend or simple generation
        peso_neto_producido: parseFloat(pesoNeto),
        unidades_empaque: parseInt(bobinas),
        maquina: selectedOrden.maquina_asignada, // Auto-assign to the machine of the order
        operario: profile?.id,
        turno: 'Dia', // Default or selector
        hora_inicio: new Date(now.getTime() - 60 * 60 * 1000).toISOString(), // 1 hour ago
        hora_final: now.toISOString(),
      };

      await apiClient.post(`/ordenes-produccion/${selectedOrden.id}/registrar-lote/`, payload);
      toast.success('Lote registrado exitosamente');
      setIsDialogOpen(false);
      fetchOrdenes(); // Refresh to see if status changes
    } catch (error: any) {
      console.error(error);
      toast.error('Error al registrar la producción');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="p-6">Cargando asignaciones...</div>;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Panel de Operario</h1>
        <p className="text-muted-foreground">
          Bienvenido, {profile?.username}. Aquí están tus órdenes de producción activas.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {ordenes.length > 0 ? (
          ordenes.map((orden) => (
            <Card key={orden.id} className="border-l-4 border-l-blue-500 shadow-sm hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Package className="h-5 w-5 text-blue-600" />
                      {orden.producto_nombre}
                    </CardTitle>
                    <CardDescription className="font-mono text-xs mt-1">
                      OP: {orden.codigo}
                    </CardDescription>
                  </div>
                  <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                    En Proceso
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex flex-col">
                    <span className="text-muted-foreground text-xs">Fórmula</span>
                    <span className="font-medium truncate" title={orden.formula_color_nombre}>{orden.formula_color_nombre}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-muted-foreground text-xs">Meta</span>
                    <span className="font-medium">{orden.peso_neto_requerido} Kg</span>
                  </div>
                </div>

                {orden.observaciones && (
                  <div className="bg-amber-50 p-2 rounded text-xs text-amber-800 border border-amber-100 flex gap-2">
                    <ClipboardList className="h-4 w-4 shrink-0" />
                    <span className="italic">"{orden.observaciones}"</span>
                  </div>
                )}

                <Button className="w-full mt-2" onClick={() => handleOpenRegistro(orden)}>
                  <Scale className="mr-2 h-4 w-4" /> Registrar Avance
                </Button>
              </CardContent>
            </Card>
          ))
        ) : (
          <div className="col-span-full flex flex-col items-center justify-center p-12 bg-slate-50 border border-dashed rounded-lg text-muted-foreground">
            <Timer className="h-10 w-10 mb-2 opacity-20" />
            <p>No tienes órdenes de producción asignadas en este momento.</p>
            <p className="text-sm">Contacta a tu Jefe de Área si crees que es un error.</p>
          </div>
        )}
      </div>

      {/* Dialogo de Registro */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Registrar Producción</DialogTitle>
            <DialogDescription>
              Ingresa los detalles del lote producido para la orden <strong>{selectedOrden?.codigo}</strong>.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="peso" className="text-right">
                Peso Neto (Kg)
              </Label>
              <Input
                id="peso"
                type="number"
                step="0.01"
                value={pesoNeto}
                onChange={(e) => setPesoNeto(e.target.value)}
                className="col-span-3 font-mono text-lg"
                autoFocus
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="bobinas" className="text-right">
                Unidades/Bobinas
              </Label>
              <Input
                id="bobinas"
                type="number"
                value={bobinas}
                onChange={(e) => setBobinas(e.target.value)}
                className="col-span-3"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSubmitting}>Cancelar</Button>
            <Button onClick={handleRegistrarLote} disabled={!pesoNeto || isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Confirmar Registro'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}