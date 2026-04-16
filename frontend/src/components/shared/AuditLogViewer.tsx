import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Search, User, Shield, Info, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { AuditLog } from '../../lib/types';
import { format } from 'date-fns';

const ITEMS_PER_PAGE = 20;

interface AuditLogViewerProps {
  sedeId?: string;
  /** Si true, ignora el filtro por sede y muestra todos los logs */
  todasLasSedes?: boolean;
  /** Si false, deshabilita la opción "Ver todas las sedes" */
  permitirVerTodasSedes?: boolean;
}

function safeFormatDate(val: unknown): string {
  try {
    if (val == null) return '-';
    const d = new Date(String(val));
    return isNaN(d.getTime()) ? '-' : format(d, 'dd/MM/yy HH:mm:ss');
  } catch {
    return '-';
  }
}

export function AuditLogViewer({ sedeId, todasLasSedes, permitirVerTodasSedes = true }: AuditLogViewerProps) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [verTodas, setVerTodas] = useState(todasLasSedes ?? false);
  const totalPages = Math.max(1, Math.ceil(totalCount / ITEMS_PER_PAGE));
  const safePage = Math.min(Math.max(1, currentPage), totalPages || 1);
  const effectiveSedeId = (permitirVerTodasSedes && verTodas) ? undefined : sedeId;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const fetchLogs = async () => {
      try {
        const params: Record<string, string> = { page: String(safePage), page_size: String(ITEMS_PER_PAGE) };
        if (effectiveSedeId) params.sede_id = effectiveSedeId;
        const response = await apiClient.get('/inventory/audit-logs/', { params });
        if (cancelled) return;
        const data = response?.data;
        let results: AuditLog[] = [];
        let count = 0;
        if (data && typeof data === 'object') {
          if (Array.isArray(data.results)) {
            results = [...data.results];
            count = typeof data.count === 'number' ? data.count : results.length;
          } else if (Array.isArray(data)) {
            results = [...data];
            count = data.length;
          }
        }
        setLogs(results);
        setTotalCount(count);
      } catch (error) {
        if (!cancelled) {
          console.error('Error fetching audit logs:', error);
          toast.error('Error al cargar logs de auditoría');
          setLogs([]);
          setTotalCount(0);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchLogs();
    return () => { cancelled = true; };
  }, [effectiveSedeId, safePage]);

  useEffect(() => {
    if (totalPages > 0 && currentPage > totalPages) {
      setCurrentPage(1);
    }
  }, [currentPage, totalPages]);

  const filteredLogs = React.useMemo((): AuditLog[] => {
    const arr = Array.isArray(logs) ? [...logs] : [];
    if (arr.length === 0) return [];
    const term = String(searchTerm || '').toLowerCase();
    if (!term) return arr;
    const out: AuditLog[] = [];
    for (let i = 0; i < arr.length; i++) {
      const log = arr[i];
      if (!log || typeof log !== 'object') continue;
      const tabla = String(log.tabla_afectada ?? '').toLowerCase();
      const just = String(log.justificacion ?? '').toLowerCase();
      const user = String(log.usuario_nombre ?? '').toLowerCase();
      if (tabla.includes(term) || just.includes(term) || user.includes(term)) {
        out.push(log);
      }
    }
    return out;
  }, [logs, searchTerm]);

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'CREATE': return <Badge variant="default" className="bg-green-500">CREAR</Badge>;
      case 'UPDATE': return <Badge variant="secondary" className="bg-blue-500 text-white">EDITAR</Badge>;
      case 'DELETE': return <Badge variant="destructive">ELIMINAR</Badge>;
      default: return <Badge variant="outline">{action}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Registro de Auditoría</h2>
          <p className="text-sm text-muted-foreground">
            Trazabilidad completa de cambios en el sistema (Inmutable).
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
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por tabla, usuario..."
              className="pl-8"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table className="table-fixed">
            <colgroup>
              <col className="w-[130px]" />
              <col className="w-[140px]" />
              <col className="w-[180px]" />
              <col className="w-[min(320px,30%)]" />
              <col className="w-[min(200px,22%)]" />
            </colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha / IP</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead>Acción / Tabla</TableHead>
                <TableHead>Cambios</TableHead>
                <TableHead className="text-right">Justificación</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className={loading ? 'opacity-60 pointer-events-none' : ''}>
              {loading && filteredLogs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">Cargando...</TableCell>
                </TableRow>
              ) : filteredLogs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    No se encontraron registros de auditoría.
                  </TableCell>
                </TableRow>
              ) : (
                filteredLogs.map((log, idx) => {
                  const logId = log?.id ?? idx;
                  const accion = log?.accion ?? 'UPDATE';
                  return (
                  <TableRow key={logId} className="group">
                    <TableCell className="text-xs">
                      <div className="font-semibold">{safeFormatDate(log?.fecha_hora)}</div>
                      <div className="text-muted-foreground flex items-center gap-1">
                        <Shield className="w-3 h-3" /> {log?.ip_address ?? '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <User className="w-4 h-4 text-primary" />
                        </div>
                        <span className="font-medium">{log?.usuario_nombre || 'Desconocido'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="align-top whitespace-normal min-w-0">
                      <div className="flex flex-col gap-1.5 min-w-0">
                        <div className="shrink-0">{getActionBadge(accion)}</div>
                        <div className="text-xs font-mono bg-accent/80 px-2 py-1.5 rounded break-all min-w-0">
                          {log?.tabla_afectada ?? 'N/A'} #{log?.registro_id ?? log?.object_id ?? '-'}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="align-top max-w-0 whitespace-normal">
                      <div className="min-w-0 max-w-full overflow-x-auto">
                        <div className="text-[10px] space-y-1 w-fit min-w-0">
                          {accion === 'UPDATE' && log?.valor_anterior != null && (
                            <div className="p-2 border rounded bg-muted/30 break-words">
                              <div className="text-destructive mb-1">
                                <span className="font-bold">-</span> Anterior: <span className="break-all">{JSON.stringify(log.valor_anterior)}</span>
                              </div>
                              <div className="text-green-600">
                                <span className="font-bold">+</span> Nuevo: <span className="break-all">{JSON.stringify(log.valor_nuevo)}</span>
                              </div>
                            </div>
                          )}
                          {accion === 'CREATE' && (
                            <div className="p-2 border rounded bg-green-50/50 text-green-700 break-words">
                              Registro inicial: <span className="break-all">{JSON.stringify(log?.valor_nuevo ?? {})}</span>
                            </div>
                          )}
                          {accion === 'DELETE' && (
                            <div className="p-2 border rounded bg-red-50/50 text-red-700 break-words">
                              Valores antes de eliminar: <span className="break-all">{JSON.stringify(log?.valor_anterior ?? {})}</span>
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
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={safePage <= 1 || loading}
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Anterior
              </Button>
              <span className="flex items-center gap-1 text-sm">
                <span className="text-muted-foreground">Ir a</span>
                <Input
                  type="number"
                  min={1}
                  max={totalPages}
                  defaultValue={safePage}
                  key={safePage}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const v = parseInt((e.target as HTMLInputElement).value, 10);
                      if (!isNaN(v) && v >= 1 && v <= totalPages) setCurrentPage(v);
                    }
                  }}
                  onBlur={(e) => {
                    const v = parseInt(e.target.value, 10);
                    if (!isNaN(v) && v >= 1 && v <= totalPages) setCurrentPage(v);
                  }}
                  className="w-14 h-8 text-center py-0 px-1"
                />
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={safePage >= totalPages || loading}
              >
                Siguiente
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </Card>
      <p className="text-xs text-muted-foreground mt-2">
        Solo se está mostrando la información de los últimos 30 días.
      </p>
    </div>
  );
}
