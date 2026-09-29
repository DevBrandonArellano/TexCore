import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { OrdenProduccion, Maquina, FormulaColor, DescargaQuimicoOP } from '../../lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { ChevronLeft, ChevronRight, Eye, RefreshCw, History } from 'lucide-react';

const ESTADO_LABEL: Record<string, string> = {
  pendiente: 'Pendiente',
  en_proceso: 'En Proceso',
  finalizada: 'Finalizada',
};

interface FiltrosHistorial {
  fecha_desde: string;
  fecha_hasta: string;
  maquina_asignada: string;
  formula_color: string;
  estado: string;
}

const FILTROS_VACIOS: FiltrosHistorial = {
  fecha_desde: '', fecha_hasta: '', maquina_asignada: '', formula_color: '', estado: '',
};

export function HistorialOrdenesTintoreria() {
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState<FiltrosHistorial>(FILTROS_VACIOS);
  const [url, setUrl] = useState<string | null>(null);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [count, setCount] = useState(0);

  const [ordenDetalle, setOrdenDetalle] = useState<OrdenProduccion | null>(null);
  const [descargas, setDescargas] = useState<DescargaQuimicoOP[]>([]);
  const [cargandoDescargas, setCargandoDescargas] = useState(false);

  const construirUrl = useCallback(() => {
    const params = new URLSearchParams();
    if (filtros.fecha_desde) params.append('fecha_desde', filtros.fecha_desde);
    if (filtros.fecha_hasta) params.append('fecha_hasta', filtros.fecha_hasta);
    if (filtros.maquina_asignada) params.append('maquina_asignada', filtros.maquina_asignada);
    if (filtros.formula_color) params.append('formula_color', filtros.formula_color);
    if (filtros.estado) params.append('estado', filtros.estado);
    return `/ordenes-produccion/historial/?${params.toString()}`;
  }, [filtros]);

  const cargarPagina = useCallback(async (paginaUrl: string) => {
    try {
      setLoading(true);
      const { data } = await apiClient.get(paginaUrl);
      const resultados = Array.isArray(data) ? data : data.results || [];
      setOrdenes(resultados);
      setNext(Array.isArray(data) ? null : data.next);
      setPrevious(Array.isArray(data) ? null : data.previous);
      setCount(Array.isArray(data) ? resultados.length : data.count ?? resultados.length);
    } catch (error) {
      console.error('Error al cargar historial de órdenes', error);
      toast.error('No se pudo cargar el historial de órdenes.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    apiClient.get('/maquinas/').then((res) => setMaquinas(res.data.results || res.data)).catch(() => {});
    apiClient.get('/formula-colors/').then((res) => setFormulas(res.data.results || res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const nuevaUrl = construirUrl();
    setUrl(nuevaUrl);
    cargarPagina(nuevaUrl);
  }, [construirUrl, cargarPagina]);

  const verDescargas = async (orden: OrdenProduccion) => {
    setOrdenDetalle(orden);
    setCargandoDescargas(true);
    try {
      const { data } = await apiClient.get<DescargaQuimicoOP[]>(
        `/ordenes-produccion/${orden.id}/descargas-quimico/`
      );
      setDescargas(data);
    } catch (error) {
      toast.error('No se pudieron cargar las descargas de la orden.');
    } finally {
      setCargandoDescargas(false);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4 p-4">
      <div className="flex-shrink-0">
        <h1 className="text-3xl font-bold tracking-tight">Historial de Órdenes</h1>
        <p className="text-muted-foreground">
          Consulta las órdenes de tintorería: peso, litros de baño, relación y versión de fórmula usada.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Filtros</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Desde</label>
              <Input
                type="date" className="h-9" value={filtros.fecha_desde}
                onChange={(e) => setFiltros((p) => ({ ...p, fecha_desde: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Hasta</label>
              <Input
                type="date" className="h-9" value={filtros.fecha_hasta}
                onChange={(e) => setFiltros((p) => ({ ...p, fecha_hasta: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Máquina</label>
              <Select
                value={filtros.maquina_asignada || 'todas'}
                onValueChange={(v) => setFiltros((p) => ({ ...p, maquina_asignada: v === 'todas' ? '' : v }))}
              >
                <SelectTrigger className="h-9"><SelectValue placeholder="Todas" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todas">Todas</SelectItem>
                  {maquinas.map((m) => <SelectItem key={m.id} value={String(m.id)}>{m.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Fórmula</label>
              <Select
                value={filtros.formula_color || 'todas'}
                onValueChange={(v) => setFiltros((p) => ({ ...p, formula_color: v === 'todas' ? '' : v }))}
              >
                <SelectTrigger className="h-9"><SelectValue placeholder="Todas" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todas">Todas</SelectItem>
                  {formulas.map((f) => <SelectItem key={f.id} value={String(f.id)}>{f.codigo}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Estado</label>
              <Select
                value={filtros.estado || 'todos'}
                onValueChange={(v) => setFiltros((p) => ({ ...p, estado: v === 'todos' ? '' : v }))}
              >
                <SelectTrigger className="h-9"><SelectValue placeholder="Todos" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos</SelectItem>
                  <SelectItem value="pendiente">Pendiente</SelectItem>
                  <SelectItem value="en_proceso">En Proceso</SelectItem>
                  <SelectItem value="finalizada">Finalizada</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="flex-1 min-h-0 flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm">{count} orden(es)</CardTitle>
          <Button size="sm" variant="outline" onClick={() => url && cargarPagina(url)} disabled={loading}>
            <RefreshCw className="w-4 h-4 mr-2" /> Actualizar
          </Button>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto min-h-0">
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Cargando...</div>
          ) : ordenes.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">Sin órdenes para los filtros seleccionados</div>
          ) : (
            <div className="rounded-lg border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fórmula</TableHead>
                    <TableHead className="text-right">Peso (kg)</TableHead>
                    <TableHead className="text-right">Litros baño</TableHead>
                    <TableHead className="text-right">Relación</TableHead>
                    <TableHead>Versión</TableHead>
                    <TableHead className="text-center">Descargas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ordenes.map((orden) => (
                    <TableRow key={orden.id}>
                      <TableCell className="font-mono text-xs font-bold">{orden.codigo}</TableCell>
                      <TableCell><Badge variant="outline">{ESTADO_LABEL[orden.estado] ?? orden.estado}</Badge></TableCell>
                      <TableCell className="text-sm">{orden.formula_color_nombre ?? '—'}</TableCell>
                      <TableCell className="text-right font-mono">{orden.peso_neto_requerido ?? '—'}</TableCell>
                      <TableCell className="text-right font-mono">{orden.litros_bano ?? '—'}</TableCell>
                      <TableCell className="text-right font-mono">
                        {orden.relacion_bano ? `1:${Number(orden.relacion_bano).toFixed(2)}` : '—'}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{orden.version_formula ? `v${orden.version_formula}` : '—'}</TableCell>
                      <TableCell className="text-center">
                        <Button
                          size="sm" variant="ghost" aria-label={`Ver descargas de ${orden.codigo}`}
                          onClick={() => verDescargas(orden)}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
        <div className="flex items-center justify-end gap-2 p-3 border-t flex-shrink-0">
          <Button size="sm" variant="outline" disabled={!previous} onClick={() => previous && cargarPagina(previous)}>
            <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
          </Button>
          <Button size="sm" variant="outline" disabled={!next} onClick={() => next && cargarPagina(next)}>
            Siguiente <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </Card>

      <Dialog open={!!ordenDetalle} onOpenChange={(open) => !open && setOrdenDetalle(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              <DialogTitle>Descargas de la orden {ordenDetalle?.codigo}</DialogTitle>
            </div>
            <DialogDescription>
              Peso {ordenDetalle?.peso_neto_requerido ?? '—'} kg · Litros {ordenDetalle?.litros_bano ?? '—'} ·
              {' '}Relación {ordenDetalle?.relacion_bano ? `1:${Number(ordenDetalle.relacion_bano).toFixed(2)}` : '—'}
            </DialogDescription>
          </DialogHeader>
          {cargandoDescargas ? (
            <div className="text-center py-8 text-muted-foreground">Cargando...</div>
          ) : descargas.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">Sin descargas registradas</div>
          ) : (
            <div className="rounded-lg border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Producto</TableHead>
                    <TableHead className="text-right">Cantidad (kg)</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {descargas.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell className="text-sm">{new Date(d.fecha_descarga).toLocaleDateString()}</TableCell>
                      <TableCell className="text-sm">{d.producto_descripcion}</TableCell>
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
        </DialogContent>
      </Dialog>
    </div>
  );
}
