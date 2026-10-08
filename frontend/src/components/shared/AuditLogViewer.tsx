import React, { useState } from 'react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search, Filter, RefreshCcw, User as UserIcon, Calendar, Info, ChevronLeft, ChevronRight } from 'lucide-react';
import apiClient from '@/lib/axios';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { RegistroAuditoria } from '../../lib/types';
import { useCargaRemota } from '../../hooks/useCargaRemota';

const ITEMS_PER_PAGE = 20;
const SIN_REGISTROS: RegistroAuditoria[] = [];

interface AuditLogViewerProps {
  sedeId?: string;
  /** Si true, ignora el filtro por sede y muestra todos los logs */
  todasLasSedes?: boolean;
  /** Si false, deshabilita la opción "Ver todas las sedes" */
  permitirVerTodasSedes?: boolean;
}

export function AuditLogViewer({ sedeId, todasLasSedes, permitirVerTodasSedes = true }: AuditLogViewerProps) {
  const [search, setSearch] = useState("");
  // TEX-52 CA-1: rango de fechas y tipo de operación. Sin «Desde», el servidor muestra el último mes.
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [accion, setAccion] = useState("");
  const [errorFiltro, setErrorFiltro] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const [verTodas, setVerTodas] = useState(todasLasSedes ?? false);
  const effectiveSedeId = (permitirVerTodasSedes && verTodas) ? undefined : sedeId;

  // Los filtros del formulario se aplican al enviar; la página y «ver todas» al cambiar.
  const [aplicados, setAplicados] = useState({ search: "", desde: "", hasta: "", accion: "" });
  const filtros = [
    aplicados.desde && `&fecha_desde=${aplicados.desde}`,
    aplicados.hasta && `&fecha_hasta=${aplicados.hasta}`,
    aplicados.accion && `&accion=${aplicados.accion}`,
  ].filter(Boolean).join('');
  const url = `/inventory/audit-logs/?search=${encodeURIComponent(aplicados.search)}&page=${page}${effectiveSedeId ? `&sede_id=${effectiveSedeId}` : ''}${filtros}`;
  const carga = useCargaRemota(
    () =>
      apiClient
        .get<{ results: RegistroAuditoria[]; count: number }>(url)
        .then((response) => response.data)
        .catch((error: unknown) => {
          console.error("Error fetching audit logs:", error);
          throw error;
        }),
    url,
  );
  const logs = carga.datos?.results ?? SIN_REGISTROS;
  const totalCount = carga.datos?.count ?? 0;
  const loading = carga.cargando;
  const totalPages = Math.max(1, Math.ceil(totalCount / ITEMS_PER_PAGE));
  const safePage = Math.min(Math.max(1, page), totalPages || 1);
  const fetchLogs = carga.recargar;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (desde && hasta && desde > hasta) {
      setErrorFiltro('La fecha «Desde» no puede ser posterior a «Hasta».');
      return;
    }
    setErrorFiltro(null);
    setAplicados({ search, desde, hasta, accion });
    setPage(1);
    // Volver a buscar con los mismos filtros también consulta de nuevo.
    fetchLogs();
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'CREATE': return <Badge className="bg-green-100 text-green-700 hover:bg-green-100 border-green-200">CREAR</Badge>;
      case 'UPDATE': return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100 border-blue-200">EDITAR</Badge>;
      case 'DELETE': return <Badge className="bg-red-100 text-red-700 hover:bg-red-100 border-red-200">ELIMINAR</Badge>;
      default: return <Badge variant="outline">{action}</Badge>;
    }
  };

  return (
    <div className="space-y-4 max-w-full overflow-hidden">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold">Registro de Auditoría</h2>
          <p className="text-sm text-muted-foreground">
            Trazabilidad completa de cambios críticos en el sistema (Inmutable).
          </p>
        </div>
        <div className="flex items-center gap-3">
          {sedeId && permitirVerTodasSedes && (
            <label className="flex items-center gap-2 text-sm cursor-pointer whitespace-nowrap">
              <input
                type="checkbox"
                checked={verTodas}
                onChange={(e) => setVerTodas(e.target.checked)}
                className="rounded"
              />
              <Filter className="w-4 h-4 text-muted-foreground" />
              Ver todas las sedes
            </label>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchLogs()} disabled={loading} className="shrink-0">
          <RefreshCcw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refrescar
        </Button>
      </div>

      <Card className="border-shadow-sm overflow-hidden">
        <CardHeader className="bg-muted/30 pb-4">
          <form onSubmit={handleSearch} className="flex flex-wrap gap-2">
            <div className="relative flex-1 min-w-[200px] self-end">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por usuario, tabla o ID..."
                className="pl-9 bg-background shadow-none"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="audit-desde" className="text-xs text-muted-foreground">Desde</label>
              <Input id="audit-desde" type="date" className="bg-background shadow-none" value={desde}
                onChange={(e) => setDesde(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="audit-hasta" className="text-xs text-muted-foreground">Hasta</label>
              <Input id="audit-hasta" type="date" className="bg-background shadow-none" value={hasta}
                onChange={(e) => setHasta(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="audit-accion" className="text-xs text-muted-foreground">Operación</label>
              <select id="audit-accion" value={accion} onChange={(e) => setAccion(e.target.value)}
                className="h-9 rounded-md border bg-background px-2 text-sm">
                <option value="">Todas</option>
                <option value="CREATE">Creación</option>
                <option value="UPDATE">Edición</option>
                <option value="DELETE">Eliminación</option>
              </select>
            </div>
            <Button type="submit" className="self-end">Buscar</Button>
          </form>
          {errorFiltro && <p className="mt-2 text-sm text-destructive">{errorFiltro}</p>}
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[800px]">
            <TableHeader className="bg-muted/50">
              <TableRow>
                <TableHead className="w-[180px]">Fecha y Hora</TableHead>
                <TableHead className="w-[150px]">Usuario / IP</TableHead>
                <TableHead className="w-[180px]">Objeto Afectado</TableHead>
                <TableHead className="min-w-[300px]">Detalle de Cambios</TableHead>
                <TableHead className="w-[200px]">Justificación</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <RefreshCcw className="w-8 h-8 animate-spin opacity-20" />
                      Cargando registros...
                    </div>
                  </TableCell>
                </TableRow>
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                    No se encontraron registros de auditoría.
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => {
                  const accion = log?.accion ?? 'UPDATE';
                  return (
                  <TableRow key={log.id} className="hover:bg-muted/5 group transition-colors">
                    <TableCell className="align-top py-4">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                        {log.fecha_hora ? format(new Date(log.fecha_hora), "dd MMM, HH:mm:ss", { locale: es }) : '-'}
                      </div>
                    </TableCell>
                    <TableCell className="align-top py-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm">
                          <UserIcon className="w-3.5 h-3.5 text-primary" />
                          <span className="font-semibold">{log.usuario_nombre || 'Sistema'}</span>
                        </div>
                        <div className="text-[10px] text-muted-foreground font-mono pl-5">
                          IP: {log.ip_address || 'Local'}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="align-top py-4">
                      <div className="space-y-2">
                        <div className="shrink-0">{getActionBadge(accion)}</div>
                        <div className="text-xs font-mono bg-accent/80 px-2 py-1.5 rounded break-all min-w-0">
                          {log?.tabla_afectada ?? 'N/A'} #{log?.registro_id ?? log?.object_id ?? '-'}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="align-top max-w-0 whitespace-normal">
                      <div className="min-w-0 max-w-full overflow-x-auto">
                        <div className="text-[10px] space-y-1 w-fit min-w-0">
                          {accion === 'UPDATE' && log.valor_anterior != null && (
                            <div className="p-2 border rounded bg-muted/30 break-words">
                              <div className="text-destructive mb-1">
                                <span className="font-bold">-</span> Anterior: 
                                <pre className="inline break-all ml-1">{JSON.stringify(log.valor_anterior, null, 1)}</pre>
                              </div>
                              <div className="text-green-600">
                                <span className="font-bold">+</span> Nuevo: 
                                <pre className="inline break-all ml-1">{JSON.stringify(log.valor_nuevo, null, 1)}</pre>
                              </div>
                            </div>
                          )}
                          {accion === 'CREATE' && (
                            <div className="p-2 border rounded bg-green-50/50 text-green-700 break-words">
                              Registro inicial: <pre className="inline break-all ml-1">{JSON.stringify(log.valor_nuevo, null, 1)}</pre>
                            </div>
                          )}
                          {accion === 'DELETE' && (
                            <div className="p-2 border rounded bg-red-50/50 text-red-700 break-words">
                              Valores eliminados: <pre className="inline break-all ml-1">{JSON.stringify(log.valor_anterior, null, 1)}</pre>
                            </div>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="align-top w-[200px] min-w-[160px] pl-4 whitespace-normal">
                      <div className="flex items-start gap-2 w-full min-w-0">
                        <Info className="w-4 h-4 text-primary shrink-0 mt-0.5 flex-shrink-0" />
                        <span className="text-sm italic break-words">{log?.justificacion ?? '-'}</span>
                      </div>
                    </TableCell>
                  </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
        {!loading && totalCount > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t">
            <span className="text-sm text-muted-foreground">
              Página {safePage} de {totalPages} ({totalCount} registros)
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" /> Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
              >
                Siguiente <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
