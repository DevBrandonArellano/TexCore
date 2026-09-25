import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { DescargaQuimicoOP, StockQuimico } from '../../lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { RefreshCw, FlaskConical } from 'lucide-react';

export function DescargasQuimicosTintoreria() {
  const { profile } = useAuth();
  const sede_id = profile?.user.sede;

  const [quimicos, setQuimicos] = useState<StockQuimico[]>([]);
  const [productoId, setProductoId] = useState<string>('');
  const [descargas, setDescargas] = useState<DescargaQuimicoOP[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sede_id) return;
    apiClient.get<StockQuimico[]>(`/ordenes-produccion/stock-quimicos/?sede_id=${sede_id}`)
      .then((res) => setQuimicos(res.data))
      .catch(() => toast.error('No se pudo cargar el catálogo de químicos.'));
  }, [sede_id]);

  const cargarDescargas = useCallback(async () => {
    if (!productoId) return;
    try {
      setLoading(true);
      const { data } = await apiClient.get<DescargaQuimicoOP[]>(
        `/ordenes-produccion/descargas-quimico/?producto_id=${productoId}&sede_id=${sede_id}&limit=100`
      );
      setDescargas(data);
    } catch (error) {
      console.error('Error al cargar descargas de químicos', error);
      toast.error('No se pudieron cargar las descargas.');
    } finally {
      setLoading(false);
    }
  }, [productoId, sede_id]);

  useEffect(() => {
    cargarDescargas();
  }, [cargarDescargas]);

  return (
    <div className="flex flex-col h-full space-y-4 p-4">
      <div className="flex-shrink-0">
        <h1 className="text-3xl font-bold tracking-tight">Descargas de Químicos</h1>
        <p className="text-muted-foreground">
          Consulta las descargas aplicadas de un químico específico y su origen por orden de producción.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Químico</CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={productoId} onValueChange={setProductoId}>
            <SelectTrigger className="h-9 max-w-sm">
              <SelectValue placeholder="Selecciona un químico" />
            </SelectTrigger>
            <SelectContent>
              {quimicos.map((q) => (
                <SelectItem key={q.producto_id} value={String(q.producto_id)}>
                  {q.producto_codigo} — {q.producto_descripcion}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card className="flex-1 min-h-0 flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm">
            {productoId ? `${descargas.length} descarga(s) aplicada(s)` : 'Selecciona un químico para ver su historial'}
          </CardTitle>
          <Button size="sm" variant="outline" onClick={cargarDescargas} disabled={loading || !productoId}>
            <RefreshCw className="w-4 h-4 mr-2" /> Actualizar
          </Button>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto min-h-0">
          {!productoId ? (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
              <FlaskConical className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">Elige un químico arriba para consultar sus descargas.</p>
            </div>
          ) : loading ? (
            <div className="text-center py-8 text-muted-foreground">Cargando...</div>
          ) : descargas.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">Sin descargas registradas para este químico</div>
          ) : (
            <div className="rounded-lg border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Orden</TableHead>
                    <TableHead>Bodega</TableHead>
                    <TableHead className="text-right">Cantidad (kg)</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {descargas.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell className="text-sm">{new Date(d.fecha_descarga).toLocaleDateString()}</TableCell>
                      <TableCell className="font-mono">{d.orden_produccion}</TableCell>
                      <TableCell className="text-sm">{d.bodega_nombre}</TableCell>
                      <TableCell className="text-right font-mono">{Number(d.cantidad_calculada_kg).toFixed(3)}</TableCell>
                      <TableCell>
                        <Badge variant={d.estado === 'aplicada' ? 'default' : 'secondary'}>{d.estado}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
