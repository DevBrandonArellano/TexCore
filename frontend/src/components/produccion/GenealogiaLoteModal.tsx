import React, { useCallback, useEffect, useState } from 'react';
import apiClient from '../../lib/axios';
import { GenealogiaResponse, GenealogiaNodoLote } from '../../types/produccion';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import {
  GitFork,
  ArrowRight,
  ArrowLeftRight,
  Layers,
  Package,
  Truck,
  Factory,
  Users,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  FileText,
  Calendar,
  ShieldAlert,
} from 'lucide-react';

interface GenealogiaLoteModalProps {
  loteCodigo: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GenealogiaLoteModal({
  loteCodigo,
  open,
  onOpenChange,
}: GenealogiaLoteModalProps) {
  const [direccion, setDireccion] = useState<'atras' | 'adelante'>('atras');
  const [datos, setDatos] = useState<GenealogiaResponse | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargarGenealogia = useCallback(
    async (codigo: string, dir: 'atras' | 'adelante') => {
      setCargando(true);
      setError(null);
      try {
        const res = await apiClient.get<GenealogiaResponse>(
          '/corridas-produccion/trazabilidad-lote/',
          {
            params: { codigo, direccion: dir },
          }
        );
        setDatos(res.data);
      } catch (err: any) {
        const msg =
          err?.response?.data?.error ||
          'No se pudo cargar el grafo de genealogía del lote.';
        setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      } finally {
        setCargando(false);
      }
    },
    []
  );

  useEffect(() => {
    if (open && loteCodigo) {
      cargarGenealogia(loteCodigo, direccion);
    } else if (!open) {
      setDatos(null);
      setError(null);
    }
  }, [open, loteCodigo, direccion, cargarGenealogia]);

  const renderLoteCard = (lote: GenealogiaNodoLote, esRaiz = false) => (
    <div
      key={lote.id}
      className={`rounded-lg border p-3 text-sm transition-all ${
        esRaiz
          ? 'border-primary/60 bg-primary/5 shadow-sm ring-1 ring-primary/20'
          : 'bg-card'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 font-mono font-bold">
          <Package className="h-4 w-4 text-primary" />
          <span>{lote.codigo_lote}</span>
          {esRaiz && (
            <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20">
              Lote Consultado
            </Badge>
          )}
        </div>
        {lote.clasificacion_calidad && (
          <Badge
            variant={
              lote.clasificacion_calidad.toUpperCase() === 'PRIMERA'
                ? 'default'
                : 'secondary'
            }
            className="text-[10px]"
          >
            {lote.clasificacion_calidad}
          </Badge>
        )}
      </div>

      <div className="mt-1.5 text-xs text-muted-foreground">
        <span className="font-semibold text-foreground">
          {lote.producto_codigo}
        </span>
        {lote.producto_descripcion && ` - ${lote.producto_descripcion}`}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <div>
          <span className="text-muted-foreground">Peso Neto: </span>
          <span className="font-mono font-semibold">
            {lote.peso_neto_producido} kg
          </span>
        </div>
        {lote.orden_produccion_codigo && (
          <div>
            <span className="text-muted-foreground">OP: </span>
            <span className="font-mono font-semibold">
              {lote.orden_produccion_codigo}
            </span>
          </div>
        )}
        {lote.producto_tipo && (
          <div>
            <Badge variant="outline" className="text-[10px] uppercase">
              {lote.producto_tipo.replace('_', ' ')}
            </Badge>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <GitFork className="h-5 w-5 text-primary" />
            <DialogTitle>Genealogía de Lote (Grafo DAG)</DialogTitle>
          </div>
          <DialogDescription>
            Análisis multidireccional de trazabilidad, transformaciones continuas y recall del lote{' '}
            <span className="font-mono font-bold text-foreground">{loteCodigo}</span>.
          </DialogDescription>
        </DialogHeader>

        {/* Selector de Dirección Trace-back / Trace-forward */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3">
          <Tabs
            value={direccion}
            onValueChange={(val) => setDireccion(val as 'atras' | 'adelante')}
          >
            <TabsList className="grid grid-cols-2 w-full sm:w-[360px]">
              <TabsTrigger value="atras" className="flex items-center gap-1.5 text-xs">
                <ArrowLeftRight className="h-3.5 w-3.5" />
                Trace-Back (Hacia Atrás)
              </TabsTrigger>
              <TabsTrigger value="adelante" className="flex items-center gap-1.5 text-xs">
                <ShieldAlert className="h-3.5 w-3.5" />
                Trace-Forward (Recall)
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <Button
            variant="outline"
            size="sm"
            onClick={() => loteCodigo && cargarGenealogia(loteCodigo, direccion)}
            disabled={cargando}
            className="self-end sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${cargando ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>

        {/* Estado de Carga o Error */}
        {cargando && (
          <div className="py-12 text-center text-sm text-muted-foreground">
            <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
            Cargando grafo de genealogía...
          </div>
        )}

        {error && !cargando && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              Error en la consulta de trazabilidad
            </div>
            <p className="mt-1">{error}</p>
          </div>
        )}

        {/* Contenido Principal */}
        {!cargando && !error && datos && (
          <div className="space-y-6">
            {/* Tarjetas de Métricas de Genealogía */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Card className="bg-muted/40">
                <CardHeader className="pb-2 pt-3">
                  <CardTitle className="text-xs text-muted-foreground flex items-center gap-1.5 font-normal">
                    <Package className="h-3.5 w-3.5" />
                    Lote Raíz
                  </CardTitle>
                </CardHeader>
                <CardContent className="pb-3">
                  <div className="font-mono font-bold text-base">
                    {datos.nodo_raiz?.codigo_lote}
                  </div>
                  <div className="text-xs text-muted-foreground truncate">
                    {datos.nodo_raiz?.producto_codigo} · {datos.nodo_raiz?.peso_neto_producido} kg
                  </div>
                </CardContent>
              </Card>

              {direccion === 'atras' ? (
                <>
                  <Card className="bg-muted/40">
                    <CardHeader className="pb-2 pt-3">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-1.5 font-normal">
                        <Layers className="h-3.5 w-3.5" />
                        Lotes Ancestros
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="font-bold text-xl">
                        {datos.total_ancestros ?? datos.ancestros?.length ?? 0}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Nivel de transformaciones previas
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="bg-muted/40">
                    <CardHeader className="pb-2 pt-3">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-1.5 font-normal">
                        <Truck className="h-3.5 w-3.5" />
                        Materias Primas de Origen
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="font-bold text-xl">
                        {datos.total_materias_primas ?? datos.materias_primas_origen?.length ?? 0}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Lotes de proveedores involucrados
                      </div>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <>
                  <Card className="bg-muted/40">
                    <CardHeader className="pb-2 pt-3">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-1.5 font-normal">
                        <Layers className="h-3.5 w-3.5" />
                        Lotes Derivados
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div className="font-bold text-xl">
                        {datos.total_descendientes ?? datos.descendientes?.length ?? 0}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Productos o subprocesos generados
                      </div>
                    </CardContent>
                  </Card>

                  <Card
                    className={
                      (datos.total_clientes_afectados ?? 0) > 0
                        ? 'border-destructive/40 bg-destructive/10'
                        : 'bg-muted/40'
                    }
                  >
                    <CardHeader className="pb-2 pt-3">
                      <CardTitle className="text-xs text-muted-foreground flex items-center gap-1.5 font-normal">
                        <Users className="h-3.5 w-3.5" />
                        Clientes Impactados (Recall)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pb-3">
                      <div
                        className={`font-bold text-xl ${
                          (datos.total_clientes_afectados ?? 0) > 0
                            ? 'text-destructive'
                            : ''
                        }`}
                      >
                        {datos.total_clientes_afectados ?? 0}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {(datos.total_clientes_afectados ?? 0) > 0
                          ? 'Despachos despachados a clientes'
                          : 'Sin despachos comerciales'}
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </div>

            {/* SECCIÓN TRACE-BACK */}
            {direccion === 'atras' && (
              <div className="space-y-4">
                {/* 1. Materias Primas de Proveedor */}
                {datos.materias_primas_origen && datos.materias_primas_origen.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                      <Truck className="h-4 w-4 text-primary" />
                      Materias Primas y Proveedores Originales
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {datos.materias_primas_origen.map((mp) => (
                        <div
                          key={mp.id}
                          className="rounded-lg border bg-amber-500/5 border-amber-500/30 p-3 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-amber-900 dark:text-amber-200">
                              {mp.proveedor_nombre}
                            </span>
                            <Badge variant="outline" className="text-[10px]">
                              Doc: {mp.numero_documento_entrada || 'S/D'}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2 font-mono">
                            <span>Lote Prov: {mp.lote_proveedor}</span>
                            <span>·</span>
                            <span>Producto: {mp.producto_codigo}</span>
                          </div>
                          <div className="flex items-center justify-between text-muted-foreground pt-1">
                            <span>Recepción: {mp.fecha_recepcion}</span>
                            <span>En lote: {mp.asociado_a_lote_codigo}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 2. Árbol de Transformaciones (Aristas) */}
                <div>
                  <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                    <Factory className="h-4 w-4 text-primary" />
                    Operaciones de Mezcla y Transformación (DAG)
                  </h4>
                  {datos.aristas && datos.aristas.length > 0 ? (
                    <div className="space-y-2">
                      {datos.aristas.map((arista, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border p-3 text-xs bg-muted/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                        >
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="font-mono">
                              {arista.padre_codigo}
                            </Badge>
                            <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                            <Badge variant="default" className="font-mono">
                              {arista.hijo_codigo}
                            </Badge>
                          </div>

                          <div className="flex flex-wrap items-center gap-3 text-muted-foreground">
                            {arista.maquina && (
                              <span>
                                Máquina: <strong className="text-foreground">{arista.maquina}</strong>
                              </span>
                            )}
                            {arista.corrida_codigo && (
                              <span>
                                Corrida: <strong className="text-foreground">{arista.corrida_codigo}</strong>
                              </span>
                            )}
                            <span>
                              Consumo: <strong className="text-foreground font-mono">{arista.cantidad_usada} kg</strong>
                            </span>
                            {arista.operario && <span>Op: {arista.operario}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground italic">
                      Este lote no registra transformaciones intermedias o fue originado directamente de materia prima.
                    </p>
                  )}
                </div>

                {/* 3. Lotes Ancestros */}
                {datos.ancestros && datos.ancestros.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                      <Layers className="h-4 w-4 text-primary" />
                      Lotes Ancestros Identificados ({datos.ancestros.length})
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {datos.ancestros.map((ancestro) => renderLoteCard(ancestro))}
                    </div>
                  </div>
                )}

                {/* 4. Nodo Raíz Destacado */}
                <div>
                  <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                    Lote Actual (Producto Terminado / Salida)
                  </h4>
                  {datos.nodo_raiz && renderLoteCard(datos.nodo_raiz, true)}
                </div>
              </div>
            )}

            {/* SECCIÓN TRACE-FORWARD */}
            {direccion === 'adelante' && (
              <div className="space-y-4">
                {/* 1. Lote de Origen Raíz */}
                <div>
                  <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                    <Package className="h-4 w-4 text-primary" />
                    Lote Origen del Análisis
                  </h4>
                  {datos.nodo_raiz && renderLoteCard(datos.nodo_raiz, true)}
                </div>

                {/* 2. Impacto en Despachos a Clientes (Recall) */}
                <div>
                  <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                    <ShieldAlert
                      className={`h-4 w-4 ${
                        (datos.despachos_clientes?.length ?? 0) > 0
                          ? 'text-destructive'
                          : 'text-primary'
                      }`}
                    />
                    Despachos y Clientes Afectados (Recall)
                  </h4>

                  {datos.despachos_clientes && datos.despachos_clientes.length > 0 ? (
                    <div className="space-y-3">
                      <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <span>
                          <strong>Atención Recall:</strong> Se han despachado productos originados de este lote
                          a los siguientes clientes. Proceda según el protocolo de calidad.
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {datos.despachos_clientes.map((desp, idx) => (
                          <div
                            key={idx}
                            className="rounded-lg border border-destructive/30 bg-card p-3 text-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-foreground">
                                {desp.cliente_nombre || 'Cliente Final'}
                              </span>
                              {desp.cliente_ruc && (
                                <Badge variant="outline" className="text-[10px]">
                                  RUC: {desp.cliente_ruc}
                                </Badge>
                              )}
                            </div>

                            <div className="flex items-center justify-between text-muted-foreground font-mono">
                              <span>Lote: {desp.lote_codigo}</span>
                              {desp.pedido_codigo && <span>Pedido: {desp.pedido_codigo}</span>}
                            </div>

                            <div className="flex items-center justify-between pt-1 border-t text-muted-foreground">
                              <span>
                                Despachado:{' '}
                                <strong className="text-foreground">
                                  {desp.peso_despachado || desp.cantidad_vendida || '0'} kg
                                </strong>
                              </span>
                              {desp.fecha_despacho && (
                                <span>{new Date(desp.fecha_despacho).toLocaleDateString()}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-xs text-green-800 dark:text-green-300 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
                      <span>
                        <strong>Sin impacto externo:</strong> Ningún derivado de este lote ha sido despachado
                        a clientes finales ni vendido por Kardex.
                      </span>
                    </div>
                  )}
                </div>

                {/* 3. Lotes Hijos / Derivados Producidos */}
                {datos.descendientes && datos.descendientes.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                      <Layers className="h-4 w-4 text-primary" />
                      Lotes Derivados Generados ({datos.descendientes.length})
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {datos.descendientes.map((desc) => renderLoteCard(desc))}
                    </div>
                  </div>
                )}

                {/* 4. Aristas de Transformación Derivadas */}
                {datos.aristas && datos.aristas.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold flex items-center gap-2 mb-2">
                      <Factory className="h-4 w-4 text-primary" />
                      Operaciones de Transformación Posteriores
                    </h4>
                    <div className="space-y-2">
                      {datos.aristas.map((arista, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border p-3 text-xs bg-muted/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                        >
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="font-mono">
                              {arista.padre_codigo}
                            </Badge>
                            <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                            <Badge variant="default" className="font-mono">
                              {arista.hijo_codigo}
                            </Badge>
                          </div>

                          <div className="flex flex-wrap items-center gap-3 text-muted-foreground">
                            {arista.maquina && (
                              <span>
                                Máquina: <strong className="text-foreground">{arista.maquina}</strong>
                              </span>
                            )}
                            {arista.corrida_codigo && (
                              <span>
                                Corrida: <strong className="text-foreground">{arista.corrida_codigo}</strong>
                              </span>
                            )}
                            <span>
                              Consumo: <strong className="text-foreground font-mono">{arista.cantidad_usada} kg</strong>
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default GenealogiaLoteModal;
