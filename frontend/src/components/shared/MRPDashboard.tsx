import React, { useCallback, useState } from 'react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { AlertTriangle, Factory, Loader2, Package, Play, ShoppingCart } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { ControlesPaginacion } from '../ui/controles-paginacion';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { usePagination } from '../../hooks/usePagination';
import { usePaginacionIncremental } from '../../hooks/usePaginacionIncremental';
import { mrpApi, type AlcanceMRP } from '../../lib/api/mrpApi';
import { getApiErrorMessage } from '../../lib/apiError';
import type { MRPEjecucion, NecesidadReposicion, OrdenCompraSugerida, RequerimientoMaterial } from '../../lib/types';

const FILAS_POR_PAGINA = 20;

/** Cantidad en kg en formato de Ecuador, sin ceros de relleno: '60.000' → '60', '1.600' → '1,6'. */
const kg = (valor: string | number) => Number(valor).toLocaleString('es-EC', { maximumFractionDigits: 3 });

/** Fecha ISO sin hora (YYYY-MM-DD) a dd/MM/yyyy, sin pasar por la zona horaria. */
const fechaCorta = (iso: string | null) => (iso ? iso.split('-').reverse().join('/') : '—');

const plural = (n: number, singular: string, varios: string) => `${n} ${n === 1 ? singular : varios}`;

interface MRPDashboardProps {
  /** Sede elegida en un panel con todas las sedes: 'todas' o su id. Sin ella, la sede del
   * usuario (el backend acota al bodeguero y al administrador de sede). */
  sedeId?: string;
}

/**
 * MRP por sede (ADR-012): ejecuta el cálculo, muestra la última ejecución con sus
 * advertencias, las sugerencias de compra (informativas), los requerimientos por orden
 * y la necesidad de producción que alimenta el Plan Maestro (MTS).
 */
export function MRPDashboard({ sedeId }: MRPDashboardProps) {
  const todas = sedeId === 'todas';
  const sede = sedeId && !todas ? sedeId : undefined;
  const [recarga, setRecarga] = useState(0);
  const [ejecutando, setEjecutando] = useState(false);
  const clave = `${sedeId ?? ''}|${recarga}`;

  const ultimas = useCargaRemota(() => mrpApi.ultimaEjecucion(sede), clave, {
    mensajeDeError: () => 'No se pudo cargar la información del MRP.',
  });
  const necesidades = useCargaRemota(() => mrpApi.necesidadesProduccion(sede), clave);

  const obtenerSugerencias = useCallback(
    (bloque: number, tamano: number) => mrpApi.listarSugerencias(bloque, tamano, sede),
    [sede],
  );
  const obtenerRequerimientos = useCallback(
    (bloque: number, tamano: number) => mrpApi.listarRequerimientos(bloque, tamano, sede),
    [sede],
  );
  const sugerencias = usePaginacionIncremental<OrdenCompraSugerida>({
    obtenerBloque: obtenerSugerencias, tamanoPagina: FILAS_POR_PAGINA, resetKey: clave,
  });
  const requerimientos = usePaginacionIncremental<RequerimientoMaterial>({
    obtenerBloque: obtenerRequerimientos, tamanoPagina: FILAS_POR_PAGINA, resetKey: clave,
  });
  const paginaNecesidades = usePagination<NecesidadReposicion>(
    necesidades.datos ?? [], FILAS_POR_PAGINA, { resetKey: clave },
  );

  const ejecutar = async () => {
    const alcance: AlcanceMRP = todas ? { todas: true } : sede ? { sede_id: Number(sede) } : {};
    setEjecutando(true);
    try {
      const ejecuciones = await mrpApi.ejecutar(alcance);
      avisarResultado(ejecuciones);
      setRecarga((n) => n + 1);
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'No se pudo ejecutar el MRP.'));
    } finally {
      setEjecutando(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold">Planificación de Materiales (MRP)</h2>
          <p className="text-sm text-muted-foreground">
            Calculado por sede con las órdenes abiertas, los pedidos pendientes y el stock mínimo.
          </p>
        </div>
        <Button onClick={ejecutar} disabled={ejecutando} className="gap-2">
          {ejecutando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {todas ? 'Ejecutar MRP (todas las sedes)' : 'Ejecutar MRP'}
        </Button>
      </div>

      <UltimasEjecuciones cargando={ultimas.cargando} error={ultimas.error} ejecuciones={ultimas.datos ?? []} />

      <Tabs defaultValue="sugerencias">
        <TabsList>
          <TabsTrigger value="sugerencias" className="gap-1"><ShoppingCart className="w-4 h-4" />Sugerencias de compra</TabsTrigger>
          <TabsTrigger value="requerimientos" className="gap-1"><Package className="w-4 h-4" />Requerimientos por orden</TabsTrigger>
          <TabsTrigger value="produccion" className="gap-1"><Factory className="w-4 h-4" />Necesidad de producción</TabsTrigger>
        </TabsList>

        <TabsContent value="sugerencias">
          <Card>
            <CardHeader>
              <CardTitle>Sugerencias de compra</CardTitle>
              <CardDescription>
                Informativas: lo que piden las órdenes abiertas más el stock mínimo, menos lo disponible
                (stock libre de la sede). La compra se gestiona fuera del sistema.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {sugerencias.cargando && sugerencias.paginatedItems.length === 0 ? <Cargando /> :
                sugerencias.paginatedItems.length === 0 ? (
                  <Vacio texto="No hay sugerencias de compra: el stock cubre lo que piden las órdenes y el stock mínimo." />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead>Sede</TableHead>
                        <TableHead className="text-right">Requerido (kg)</TableHead>
                        <TableHead className="text-right">Stock mín. (kg)</TableHead>
                        <TableHead className="text-right">Disponible (kg)</TableHead>
                        <TableHead className="text-right">A comprar (kg)</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sugerencias.paginatedItems.map((s) => (
                        <TableRow key={s.id}>
                          <TableCell>
                            <div className="font-medium">{s.producto_nombre}</div>
                            <div className="text-xs text-muted-foreground">{s.producto_codigo}</div>
                          </TableCell>
                          <TableCell>{s.sede_nombre}</TableCell>
                          <TableCell className="text-right font-mono">{kg(s.requerido)}</TableCell>
                          <TableCell className="text-right font-mono">{kg(s.stock_minimo)}</TableCell>
                          <TableCell className="text-right font-mono">{kg(s.stock_disponible)}</TableCell>
                          <TableCell className="text-right font-mono font-bold text-primary">{kg(s.cantidad_sugerida)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              <Paginacion {...sugerencias} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="requerimientos">
          <Card>
            <CardHeader>
              <CardTitle>Requerimientos por orden</CardTitle>
              <CardDescription>
                Material comprado que necesita cada orden abierta: lo que falta de su producto de entrada y
                los químicos que todavía no se descargaron.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {requerimientos.cargando && requerimientos.paginatedItems.length === 0 ? <Cargando /> :
                requerimientos.paginatedItems.length === 0 ? (
                  <Vacio texto="Ninguna orden abierta necesita material comprado." />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Orden</TableHead>
                        <TableHead>Producto</TableHead>
                        <TableHead className="text-right">Cantidad (kg)</TableHead>
                        <TableHead>Sede</TableHead>
                        <TableHead>Fecha requerida</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {requerimientos.paginatedItems.map((r) => (
                        <TableRow key={r.id}>
                          <TableCell><Badge variant="secondary">{r.orden_codigo}</Badge></TableCell>
                          <TableCell>
                            <div>{r.producto_nombre}</div>
                            <div className="text-xs text-muted-foreground">{r.producto_codigo}</div>
                          </TableCell>
                          <TableCell className="text-right font-mono">{kg(r.cantidad_necesaria)}</TableCell>
                          <TableCell>{r.sede_nombre}</TableCell>
                          <TableCell className="text-xs">{fechaCorta(r.fecha_requerida)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              <Paginacion {...requerimientos} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="produccion">
          <Card>
            <CardHeader>
              <CardTitle>Necesidad de producción</CardTitle>
              <CardDescription>
                Productos fabricados que hay que producir: pedidos pendientes + demanda interna + stock mínimo,
                menos lo disponible y lo que ya está en producción. Se planifica desde el Plan Maestro (MTS).
              </CardDescription>
            </CardHeader>
            <CardContent>
              {necesidades.cargando ? <Cargando /> : paginaNecesidades.paginatedItems.length === 0 ? (
                <Vacio texto="No hay productos por producir: los pedidos y el stock mínimo están cubiertos." />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead>Sede</TableHead>
                      <TableHead className="text-right">Pedidos</TableHead>
                      <TableHead className="text-right">Interna</TableHead>
                      <TableHead className="text-right">Stock mín.</TableHead>
                      <TableHead className="text-right">Disponible</TableHead>
                      <TableHead className="text-right">En producción</TableHead>
                      <TableHead className="text-right">A producir (kg)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginaNecesidades.paginatedItems.map((n) => (
                      <TableRow key={`${n.sede_id}-${n.producto_id}`}>
                        <TableCell>
                          <div className="font-medium">{n.producto_descripcion}</div>
                          <div className="text-xs text-muted-foreground">{n.producto_codigo}</div>
                        </TableCell>
                        <TableCell>{n.sede_nombre}</TableCell>
                        <TableCell className="text-right font-mono">{kg(n.demanda_pedidos)}</TableCell>
                        <TableCell className="text-right font-mono">{kg(n.demanda_interna)}</TableCell>
                        <TableCell className="text-right font-mono">{kg(n.stock_minimo)}</TableCell>
                        <TableCell className="text-right font-mono">{kg(n.stock_actual)}</TableCell>
                        <TableCell className="text-right font-mono">{kg(n.en_produccion)}</TableCell>
                        <TableCell className="text-right font-mono font-bold text-primary">{kg(n.deficit)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
              <ControlesPaginacion
                currentPage={paginaNecesidades.currentPage}
                totalPages={paginaNecesidades.totalPages}
                setCurrentPage={paginaNecesidades.setCurrentPage}
                className="mt-4"
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

/** Avisa el resultado de cada sede: error si falló, conteos y advertencias si terminó. */
function avisarResultado(ejecuciones: MRPEjecucion[]) {
  ejecuciones
    .filter((e) => e.estado === 'fallida')
    .forEach((e) => toast.error(`${e.sede_nombre}: ${e.mensaje_error}`));
  const completadas = ejecuciones.filter((e) => e.estado === 'completada');
  if (completadas.length === 0) return;
  const sugeridas = completadas.reduce((t, e) => t + e.sugerencias_compra, 0);
  const aProducir = completadas.reduce((t, e) => t + e.productos_a_producir, 0);
  const advertencias = completadas.reduce((t, e) => t + e.advertencias.length, 0);
  toast.success(`MRP calculado: ${plural(sugeridas, 'sugerencia de compra', 'sugerencias de compra')} y `
    + `${plural(aProducir, 'producto a producir', 'productos a producir')}.`);
  if (advertencias > 0) {
    toast.warning(advertencias === 1
      ? 'El cálculo dejó 1 advertencia: revísela en la última ejecución.'
      : `El cálculo dejó ${advertencias} advertencias: revíselas en la última ejecución.`);
  }
}

function UltimasEjecuciones({ cargando, error, ejecuciones }: {
  cargando: boolean; error: string | null; ejecuciones: MRPEjecucion[];
}) {
  if (cargando) return <Cargando />;
  if (error) return <p className="text-sm text-destructive">{error}</p>;
  if (ejecuciones.length === 0) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          Aún no se ha ejecutado el MRP en esta sede. Pulse «Ejecutar MRP» para calcularlo.
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {ejecuciones.map((e) => (
        <Card key={e.id} data-testid={`ultima-ejecucion-${e.sede}`}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-base">{e.sede_nombre}</CardTitle>
              <Badge variant={e.estado === 'completada' ? 'outline' : 'destructive'}>
                {e.estado === 'completada' ? 'Completada' : 'Fallida'}
              </Badge>
            </div>
            <CardDescription>
              Última ejecución: {format(new Date(e.inicio), 'dd/MM/yyyy HH:mm')} · {e.iniciada_por_nombre ?? 'sistema'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {e.estado === 'completada' ? (
              <p>
                {plural(e.requerimientos, 'requerimiento', 'requerimientos')} ·{' '}
                {plural(e.sugerencias_compra, 'sugerencia de compra', 'sugerencias de compra')} ·{' '}
                {plural(e.productos_a_producir, 'producto a producir', 'productos a producir')}
              </p>
            ) : (
              <p className="text-destructive">{e.mensaje_error}</p>
            )}
            {e.advertencias.length > 0 && (
              <details className="rounded-md border border-amber-200 bg-amber-50 p-2">
                <summary className="flex cursor-pointer items-center gap-1 text-amber-800">
                  <AlertTriangle className="w-4 h-4" />
                  {plural(e.advertencias.length, 'advertencia', 'advertencias')}
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-900">
                  {e.advertencias.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </details>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function Paginacion({ currentPage, totalPages, setCurrentPage }: {
  currentPage: number; totalPages: number; setCurrentPage: (p: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <ControlesPaginacion
      currentPage={currentPage}
      totalPages={totalPages}
      setCurrentPage={setCurrentPage}
      className="mt-4"
    />
  );
}

function Cargando() {
  return (
    <div className="flex items-center justify-center p-8 text-muted-foreground">
      <Loader2 className="w-6 h-6 animate-spin" />
    </div>
  );
}

function Vacio({ texto }: { texto: string }) {
  return (
    <div className="text-center py-8 text-muted-foreground">
      <Package className="w-12 h-12 mx-auto mb-2 opacity-20" />
      <p>{texto}</p>
    </div>
  );
}
