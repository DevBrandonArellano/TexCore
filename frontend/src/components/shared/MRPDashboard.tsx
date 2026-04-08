import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Play, Package, ShoppingCart, Loader2, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { RequerimientoMaterial, OrdenCompraSugerida } from '../../lib/types';
import { format } from 'date-fns';

const ITEMS_PER_PAGE = 20;

export function MRPDashboard() {
  const [requerimientos, setRequerimientos] = useState<RequerimientoMaterial[]>([]);
  const [sugerencias, setSugerencias] = useState<OrdenCompraSugerida[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningMRP, setRunningMRP] = useState(false);
  const [currentSugerenciasPage, setCurrentSugerenciasPage] = useState(1);
  const [currentRequerimientosPage, setCurrentRequerimientosPage] = useState(1);

  const totalSugerenciasPages = Math.max(1, Math.ceil(sugerencias.length / ITEMS_PER_PAGE));
  const safeSugerenciasPage = Math.min(Math.max(1, currentSugerenciasPage), totalSugerenciasPages);
  const paginatedSugerencias = sugerencias.slice(
    (safeSugerenciasPage - 1) * ITEMS_PER_PAGE,
    safeSugerenciasPage * ITEMS_PER_PAGE
  );

  const totalRequerimientosPages = Math.max(1, Math.ceil(requerimientos.length / ITEMS_PER_PAGE));
  const safeRequerimientosPage = Math.min(Math.max(1, currentRequerimientosPage), totalRequerimientosPages);
  const paginatedRequerimientos = requerimientos.slice(
    (safeRequerimientosPage - 1) * ITEMS_PER_PAGE,
    safeRequerimientosPage * ITEMS_PER_PAGE
  );

  const fetchData = async () => {
    setLoading(true);
    try {
      const [reqRes, sugRes] = await Promise.all([
        apiClient.get('/inventory/requerimientos-material/'),
        apiClient.get('/inventory/sugerencias-compra/')
      ]);
      setRequerimientos(Array.isArray(reqRes.data) ? reqRes.data : (reqRes.data.results ?? []));
      setSugerencias(Array.isArray(sugRes.data) ? sugRes.data : (sugRes.data.results ?? []));
      setCurrentSugerenciasPage(1);
      setCurrentRequerimientosPage(1);
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
      await apiClient.post('/inventory/sugerencias-compra/ejecutar-mrp/');
      toast.success('Motor MRP ejecutado con éxito');
      await fetchData();
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
                  {paginatedSugerencias.map((sug) => (
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
            {sugerencias.length > 0 && (
              <div className="flex items-center justify-between mt-4">
                <span className="text-sm text-muted-foreground">
                  Página {safeSugerenciasPage} de {totalSugerenciasPages}
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentSugerenciasPage((p) => Math.max(1, p - 1))}
                    disabled={safeSugerenciasPage === 1}
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Anterior
                  </Button>
                  <span className="flex items-center gap-1 text-sm">
                    <span className="text-muted-foreground">Ir a</span>
                    <Input
                      type="number"
                      min={1}
                      max={totalSugerenciasPages}
                      defaultValue={safeSugerenciasPage}
                      key={safeSugerenciasPage}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          const v = parseInt((e.target as HTMLInputElement).value, 10);
                          if (!isNaN(v) && v >= 1 && v <= totalSugerenciasPages) setCurrentSugerenciasPage(v);
                        }
                      }}
                      onBlur={(e) => {
                        const v = parseInt(e.target.value, 10);
                        if (!isNaN(v) && v >= 1 && v <= totalSugerenciasPages) setCurrentSugerenciasPage(v);
                      }}
                      className="w-14 h-8 text-center py-0 px-1"
                    />
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentSugerenciasPage((p) => Math.min(totalSugerenciasPages, p + 1))}
                    disabled={safeSugerenciasPage === totalSugerenciasPages}
                  >
                    Siguiente
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
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
                {paginatedRequerimientos.map((req) => (
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
            {requerimientos.length > 0 && (
              <div className="flex items-center justify-between mt-4">
                <span className="text-sm text-muted-foreground">
                  Página {safeRequerimientosPage} de {totalRequerimientosPages}
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentRequerimientosPage((p) => Math.max(1, p - 1))}
                    disabled={safeRequerimientosPage === 1}
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Anterior
                  </Button>
                  <span className="flex items-center gap-1 text-sm">
                    <span className="text-muted-foreground">Ir a</span>
                    <Input
                      type="number"
                      min={1}
                      max={totalRequerimientosPages}
                      defaultValue={safeRequerimientosPage}
                      key={safeRequerimientosPage}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          const v = parseInt((e.target as HTMLInputElement).value, 10);
                          if (!isNaN(v) && v >= 1 && v <= totalRequerimientosPages) setCurrentRequerimientosPage(v);
                        }
                      }}
                      onBlur={(e) => {
                        const v = parseInt(e.target.value, 10);
                        if (!isNaN(v) && v >= 1 && v <= totalRequerimientosPages) setCurrentRequerimientosPage(v);
                      }}
                      className="w-14 h-8 text-center py-0 px-1"
                    />
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setCurrentRequerimientosPage((p) => Math.min(totalRequerimientosPages, p + 1))}
                    disabled={safeRequerimientosPage === totalRequerimientosPages}
                  >
                    Siguiente
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
