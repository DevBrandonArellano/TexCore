import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Search, History, User, Shield, Info, ArrowRight } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { AuditLog } from '../../lib/types';
import { format } from 'date-fns';

interface AuditLogViewerProps {
  sedeId?: string;
}

export function AuditLogViewer({ sedeId }: AuditLogViewerProps) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const config = sedeId ? { params: { sede_id: sedeId } } : undefined;
        const response = await apiClient.get('/inventory/audit-logs/', config);
        setLogs(response.data);
      } catch (error) {
        console.error('Error fetching audit logs:', error);
        toast.error('Error al cargar logs de auditoría');
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, [sedeId]);

  const filteredLogs = logs.filter(log => 
    (log.tabla_afectada || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (log.justificacion || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (log.usuario_nombre || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

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

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha / IP</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead>Acción / Tabla</TableHead>
                <TableHead>Cambios</TableHead>
                <TableHead>Justificación</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
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
                filteredLogs.map((log) => (
                  <TableRow key={log.id} className="group">
                    <TableCell className="text-xs">
                      <div className="font-semibold">{format(new Date(log.fecha_hora), 'dd/MM/yy HH:mm:ss')}</div>
                      <div className="text-muted-foreground flex items-center gap-1">
                        <Shield className="w-3 h-3" /> {log.ip_address}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <User className="w-4 h-4 text-primary" />
                        </div>
                        <span className="font-medium">{log.usuario_nombre || 'Desconocido'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <div>{getActionBadge(log.accion)}</div>
                        <div className="text-xs font-mono bg-accent p-1 rounded">
                          {log.tabla_afectada} #{log.registro_id}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[300px]">
                      <div className="text-[10px] space-y-1">
                        {log.accion === 'UPDATE' && log.valor_anterior && (
                          <div className="p-2 border rounded bg-muted/30">
                            <div className="flex items-center gap-2 text-destructive mb-1">
                              <span className="font-bold">-</span> Anterior: 
                              <pre className="inline">{JSON.stringify(log.valor_anterior, null, 1)}</pre>
                            </div>
                            <div className="flex items-center gap-2 text-green-600">
                              <span className="font-bold">+</span> Nuevo: 
                              <pre className="inline">{JSON.stringify(log.valor_nuevo, null, 1)}</pre>
                            </div>
                          </div>
                        )}
                        {log.accion === 'CREATE' && (
                          <div className="p-2 border rounded bg-green-50/50 text-green-700">
                            Registro inicial: {JSON.stringify(log.valor_nuevo, null, 1)}
                          </div>
                        )}
                        {log.accion === 'DELETE' && (
                          <div className="p-2 border rounded bg-red-50/50 text-red-700">
                            Valores antes de eliminar: {JSON.stringify(log.valor_anterior, null, 1)}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-start gap-2 max-w-[200px]">
                        <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                        <span className="text-sm italic">{log.justificacion}</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
