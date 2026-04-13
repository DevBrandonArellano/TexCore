import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Play, Package, ShoppingCart, Loader2, AlertCircle } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { RequerimientoMaterial, OrdenCompraSugerida } from '../../lib/types';
import { format } from 'date-fns';

export function MRPDashboard() {
  const [requerimientos, setRequerimientos] = useState<RequerimientoMaterial[]>([]);
  const [sugerencias, setSugerencias] = useState<OrdenCompraSugerida[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningMRP, setRunningMRP] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [reqRes, sugRes] = await Promise.all([
        apiClient.get('/inventory/requerimientos-material/'),
        apiClient.get('/inventory/sugerencias-compra/')
      ]);
      setRequerimientos(Array.isArray(reqRes.data) ? reqRes.data : (reqRes.data.results ?? []));
      setSugerencias(Array.isArray(sugRes.data) ? sugRes.data : (sugRes.data.results ?? []));
    } catch (error) {
      console.error('Error fetching MRP data:', error);
      toast.error('Error al cargar datos del MRP');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const runMRPEngine = async () => {
    setRunningMRP(true);
    try {
      const response = await apiClient.post('/inventory/sugerencias-compra/ejecutar-mrp/');
      if (response.status === 202) {
        toast.info('Motor MRP iniciado en segundo plano. Los resultados aparecerán en unos instantes.');
        // Esperar un poco antes de refrescar para que dé tiempo a procesar algo
        setTimeout(() => fetchData(), 3000);
      } else {
        toast.success('Motor MRP ejecutado con éxito');
        await fetchData();
      }
    } catch (error) {
      console.error('Error running MRP:', error);
      toast.error('Error al ejecutar el motor MRP');
    } finally {
      setRunningMRP(false);
    }
  };

  if (loading && requerimientos.length === 0) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-2 text-lg">Cargando planificación...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Planificación de Materiales (MRP)</h2>
          <p className="text-sm text-muted-foreground">
            Sugerencias automáticas basadas en pedidos y stock actual.
          </p>
        </div>
        <Button 
          onClick={runMRPEngine} 
          disabled={runningMRP}
          className="gap-2"
        >
          {runningMRP ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          Ejecutar Motor MRP
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Sugerencias de Compra */}
        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-primary" />
              <CardTitle>Órdenes de Compra Sugeridas</CardTitle>
            </div>
            <CardDescription>
              Materiales faltantes para cumplir con la demanda proyectada.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {sugerencias.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Package className="w-12 h-12 mx-auto mb-2 opacity-20" />
                <p>No hay sugerencias de compra pendientes.</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Sede</TableHead>
                    <TableHead className="text-right">Cantidad</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Generado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sugerencias.map((sug) => (
                    <TableRow key={sug.id}>
                      <TableCell>
                        <div className="font-medium">{sug.producto_nombre}</div>
                        <div className="text-xs text-muted-foreground">{sug.producto_codigo}</div>
                      </TableCell>
                      <TableCell>{sug.sede_nombre}</TableCell>
                      <TableCell className="text-right font-bold text-primary">
                        {Number(sug.cantidad_sugerida).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge variant={sug.estado === 'PENDIENTE' ? 'outline' : 'default'}>
                          {sug.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {format(new Date(sug.fecha_generacion), 'dd/MM/yyyy HH:mm')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Requerimientos Detallados */}
        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-orange-500" />
              <CardTitle>Cálculo de Requerimientos</CardTitle>
            </div>
            <CardDescription>
              Desglose de origen (Pedidos/OP) que generan la demanda.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Origen</TableHead>
                  <TableHead>Producto Requerido</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead>Sede</TableHead>
                  <TableHead>Fecha Requerida</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requerimientos.map((req) => (
                  <TableRow key={req.id}>
                    <TableCell>
                      <Badge variant="secondary">
                        {req.origen_tipo} #{req.origen_id}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div>{req.producto_nombre}</div>
                      <div className="text-xs text-muted-foreground">{req.producto_codigo}</div>
                    </TableCell>
                    <TableCell className="text-right">{Number(req.cantidad_necesaria).toLocaleString()}</TableCell>
                    <TableCell>{req.sede_nombre}</TableCell>
                    <TableCell className="text-xs">
                      {req.fecha_requerida ? format(new Date(req.fecha_requerida), 'dd/MM/yyyy') : '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
