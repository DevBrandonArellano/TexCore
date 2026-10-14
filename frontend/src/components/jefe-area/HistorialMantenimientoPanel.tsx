import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Printer, Wrench, AlertTriangle, RotateCcw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { mantenimientoApi } from '../../lib/api/mantenimientoApi';
import type { CategoriaParo, FiltrosHistorialParos } from '../../lib/api/mantenimientoApi';

/** Las 9 categorías, con el mismo texto que muestra el backend. */
const CATEGORIAS: { valor: CategoriaParo; etiqueta: string }[] = [
  { valor: 'MANTENIMIENTO_PLANIFICADO', etiqueta: 'Mantenimiento Planificado' },
  { valor: 'AVERIA', etiqueta: 'Avería / Falla de Equipo' },
  { valor: 'SETUP', etiqueta: 'Setup y Ajustes' },
  { valor: 'MICROPARO', etiqueta: 'Paro Menor / Microparo' },
  { valor: 'VELOCIDAD_REDUCIDA', etiqueta: 'Velocidad Reducida' },
  { valor: 'RECHAZO_ARRANQUE', etiqueta: 'Rechazo de Arranque' },
  { valor: 'DEFECTO_PROCESO', etiqueta: 'Defecto de Proceso' },
  { valor: 'FALTA_MATERIAL', etiqueta: 'Falta de Material' },
  { valor: 'OTRO', etiqueta: 'Otro' },
];

const TODAS = 'todas';
const FILAS_POR_PAGINA = 50;

const haceDias = (dias: number) => {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - dias);
  return fecha.toISOString().slice(0, 10);
};

const fechaHora = (iso: string | null) => {
  if (!iso) return '—';
  const f = new Date(iso);
  return `${f.toLocaleDateString('es-EC', { day: '2-digit', month: '2-digit', year: 'numeric' })} ${f.toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' })}`;
};

const soloFecha = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('es-EC', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—';

const horas = (valor: number | null) => (valor === null || valor === undefined ? '—' : valor.toFixed(2));

export interface HistorialMantenimientoPanelProps {
  /** Máquinas del área, para el selector. */
  maquinas: { id: number; nombre: string }[];
}

/**
 * Historial de mantenimiento y paros de las máquinas del área: resumen por máquina, detalle
 * paro por paro e impresión en PDF. Los paros de origen `estado` los abre el sistema cuando
 * la máquina pasa a mantenimiento o inactiva, y se cierran al volver a operativa.
 */
export function HistorialMantenimientoPanel({ maquinas }: HistorialMantenimientoPanelProps) {
  const [desde, setDesde] = useState(haceDias(30));
  const [hasta, setHasta] = useState(haceDias(0));
  const [maquina, setMaquina] = useState<string>(TODAS);
  const [categoria, setCategoria] = useState<string>(TODAS);
  const [pagina, setPagina] = useState(1);
  const [imprimiendo, setImprimiendo] = useState(false);

  const filtros = useMemo<FiltrosHistorialParos>(
    () => ({
      fecha_desde: desde || undefined,
      fecha_hasta: hasta || undefined,
      maquina: maquina === TODAS ? undefined : Number(maquina),
      categoria: categoria === TODAS ? undefined : (categoria as CategoriaParo),
    }),
    [desde, hasta, maquina, categoria],
  );

  const clave = `${desde}|${hasta}|${maquina}|${categoria}|${pagina}`;
  const { datos, cargando, error, recargar } = useCargaRemota(
    () => mantenimientoApi.historial(filtros, pagina, FILAS_POR_PAGINA),
    clave,
  );

  const cambiarFiltro = (aplicar: () => void) => {
    aplicar();
    setPagina(1);
  };

  const imprimir = async () => {
    setImprimiendo(true);
    try {
      const pdf = await mantenimientoApi.imprimirHistorial(filtros);
      window.open(URL.createObjectURL(new Blob([pdf], { type: 'application/pdf' })), '_blank');
    } catch {
      toast.error('No se pudo generar el historial en PDF.');
    } finally {
      setImprimiendo(false);
    }
  };

  const totales = datos?.totales;
  const detalle = datos?.detalle;
  const totalPaginas = detalle ? Math.max(1, Math.ceil(detalle.count / FILAS_POR_PAGINA)) : 1;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5 text-primary" /> Historial de Mantenimiento y Paros
            </CardTitle>
            <CardDescription>
              Qué días se detuvo cada máquina, cuántas horas y por qué. Incluye los paros que abre el
              sistema al poner una máquina en mantenimiento o inactiva.
            </CardDescription>
          </div>
          <Button onClick={imprimir} disabled={imprimiendo || cargando} variant="outline" size="sm">
            <Printer className="mr-2 h-4 w-4" /> {imprimiendo ? 'Generando…' : 'Imprimir'}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Filtros */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1">
            <Label htmlFor="paros-desde">Desde</Label>
            <Input
              id="paros-desde"
              type="date"
              value={desde}
              onChange={(e) => cambiarFiltro(() => setDesde(e.target.value))}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="paros-hasta">Hasta</Label>
            <Input
              id="paros-hasta"
              type="date"
              value={hasta}
              onChange={(e) => cambiarFiltro(() => setHasta(e.target.value))}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="paros-maquina">Máquina</Label>
            <Select value={maquina} onValueChange={(v) => cambiarFiltro(() => setMaquina(v))}>
              <SelectTrigger id="paros-maquina">
                <SelectValue placeholder="Todas las máquinas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={TODAS}>Todas las máquinas</SelectItem>
                {maquinas.map((m) => (
                  <SelectItem key={m.id} value={String(m.id)}>{m.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="paros-categoria">Categoría</Label>
            <Select value={categoria} onValueChange={(v) => cambiarFiltro(() => setCategoria(v))}>
              <SelectTrigger id="paros-categoria">
                <SelectValue placeholder="Todas las categorías" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={TODAS}>Todas las categorías</SelectItem>
                {CATEGORIAS.map((c) => (
                  <SelectItem key={c.valor} value={c.valor}>{c.etiqueta}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Atajos */}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={categoria === 'MANTENIMIENTO_PLANIFICADO' ? 'default' : 'outline'}
            onClick={() => cambiarFiltro(() => setCategoria('MANTENIMIENTO_PLANIFICADO'))}
          >
            <Wrench className="mr-2 h-3.5 w-3.5" /> Solo mantenimiento
          </Button>
          <Button
            size="sm"
            variant={categoria === 'AVERIA' ? 'default' : 'outline'}
            onClick={() => cambiarFiltro(() => setCategoria('AVERIA'))}
          >
            <AlertTriangle className="mr-2 h-3.5 w-3.5" /> Solo averías
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              cambiarFiltro(() => {
                setDesde(haceDias(30));
                setHasta(haceDias(0));
                setMaquina(TODAS);
                setCategoria(TODAS);
              })
            }
          >
            <RotateCcw className="mr-2 h-3.5 w-3.5" /> Últimos 30 días
          </Button>
        </div>

        {error && (
          <div className="flex items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm">
            <span>{error}</span>
            <Button size="sm" variant="outline" onClick={recargar}>Reintentar</Button>
          </div>
        )}

        {cargando && <p className="text-sm text-muted-foreground">Cargando historial…</p>}

        {!cargando && !error && totales && (
          <>
            {/* Totales del rango */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Paros</p>
                <p className="text-xl font-bold">{totales.paros}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Horas detenidas</p>
                <p className="text-xl font-bold">{horas(totales.horas_total)}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Horas planificadas</p>
                <p className="text-xl font-bold">{horas(totales.horas_planificadas)}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">Paros en curso</p>
                <p className="text-xl font-bold">{totales.paros_en_curso}</p>
              </div>
            </div>

            {datos.resumen.length === 0 ? (
              <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                Sin paros registrados en el rango consultado.
              </p>
            ) : (
              <>
                {/* Resumen por máquina */}
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Máquina</TableHead>
                        <TableHead className="text-right">Paros</TableHead>
                        <TableHead className="text-right">Horas detenidas</TableHead>
                        <TableHead className="text-right">Horas planificadas</TableHead>
                        <TableHead className="text-center">En curso</TableHead>
                        <TableHead>Último mantenimiento</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {datos.resumen.map((fila) => (
                        <TableRow key={fila.maquina_id}>
                          <TableCell className="font-medium">{fila.maquina_nombre}</TableCell>
                          <TableCell className="text-right">{fila.paros}</TableCell>
                          <TableCell className="text-right">{horas(fila.horas_total)}</TableCell>
                          <TableCell className="text-right">{horas(fila.horas_planificadas)}</TableCell>
                          <TableCell className="text-center">
                            {fila.paros_en_curso > 0 ? (
                              <Badge variant="destructive">{fila.paros_en_curso}</Badge>
                            ) : (
                              '—'
                            )}
                          </TableCell>
                          <TableCell>{soloFecha(fila.ultimo_mantenimiento)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Detalle paro por paro */}
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Máquina</TableHead>
                        <TableHead>Inicio</TableHead>
                        <TableHead>Fin</TableHead>
                        <TableHead className="text-right">Horas</TableHead>
                        <TableHead>Categoría</TableHead>
                        <TableHead>Registró</TableHead>
                        <TableHead>Descripción</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detalle?.results.map((paro) => (
                        <TableRow key={paro.id}>
                          <TableCell className="font-medium">{paro.maquina_nombre}</TableCell>
                          <TableCell>{fechaHora(paro.inicio)}</TableCell>
                          <TableCell>
                            {paro.en_curso ? <Badge variant="destructive">En curso</Badge> : fechaHora(paro.fin)}
                          </TableCell>
                          <TableCell className="text-right">{horas(paro.horas)}</TableCell>
                          <TableCell>
                            <div className="flex flex-wrap items-center gap-1">
                              <span>{paro.categoria_display}</span>
                              {paro.planificado && <Badge variant="outline">Planificado</Badge>}
                              {paro.origen === 'estado' && <Badge variant="secondary">Automático</Badge>}
                            </div>
                          </TableCell>
                          <TableCell>{paro.usuario_nombre ?? '—'}</TableCell>
                          <TableCell className="max-w-[18rem] truncate" title={paro.descripcion}>
                            {paro.descripcion || '—'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {totalPaginas > 1 && (
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-muted-foreground">
                      Página {pagina} de {totalPaginas} · {detalle?.count} paros
                    </span>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" disabled={pagina === 1} onClick={() => setPagina((p) => p - 1)}>
                        Anterior
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={pagina >= totalPaginas}
                        onClick={() => setPagina((p) => p + 1)}
                      >
                        Siguiente
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
