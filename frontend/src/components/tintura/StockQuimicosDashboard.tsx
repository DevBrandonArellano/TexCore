import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { StockQuimico, DescargaQuimicoOP } from '../../lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import {
  AlertTriangle,
  Eye,
  RefreshCw,
} from 'lucide-react';

export function StockQuimicosDashboard() {
  const { profile } = useAuth();
  const [stock, setStock] = useState<StockQuimico[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChemical, setSelectedChemical] = useState<StockQuimico | null>(null);
  const [descargas, setDescargas] = useState<DescargaQuimicoOP[]>([]);
  const [showDescargas, setShowDescargas] = useState(false);

  const sede_id = profile?.user.sede;

  const fetchStock = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<StockQuimico[]>(
        `/ordenes-produccion/stock-quimicos/?sede_id=${sede_id}`
      );
      setStock(response.data);
    } catch (error) {
      console.error('Error al cargar stock de químicos', error);
      toast.error('No se pudo cargar el stock de químicos.');
    } finally {
      setLoading(false);
    }
  }, [sede_id]);

  useEffect(() => {
    if (sede_id) {
      fetchStock();
    }
  }, [sede_id, fetchStock]);

  const handleViewDescargas = async (chemical: StockQuimico) => {
    setSelectedChemical(chemical);
    try {
      // Buscar descargas del químico en las últimas 30 días
      const response = await apiClient.get<DescargaQuimicoOP[]>(
        `/gestion/descarga-quimico-op/?producto_id=${chemical.producto_id}&limit=50`
      );
      setDescargas(response.data);
      setShowDescargas(true);
    } catch (error) {
      console.error('Error cargando historial de descargas', error);
      toast.error('No se pudo cargar el historial de descargas.');
    }
  };

  const alertaCount = stock.filter(s => s.alerta).length;
  const totalQuimicos = stock.length;

  return (
    <div className="flex flex-col h-full space-y-6 p-4">
      {/* Header */}
      <div className="flex-shrink-0">
        <h1 className="text-3xl font-bold tracking-tight">Stock de Químicos en Tintorería</h1>
        <p className="text-muted-foreground">
          Monitorea el inventario de insumos químicos. {alertaCount > 0 && (
            <span className="text-red-600 font-semibold">⚠️ {alertaCount} químicos con stock bajo</span>
          )}
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Químicos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalQuimicos}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Stock Bajo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${alertaCount > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {alertaCount}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Disponibles</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{totalQuimicos - alertaCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabla Stock */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle>Inventario</CardTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={fetchStock}
            disabled={loading}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Actualizar
          </Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Cargando...</div>
          ) : stock.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">Sin químicos registrados</div>
          ) : (
            <div className="rounded-lg border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right">Disponible (kg)</TableHead>
                    <TableHead className="text-right">Mínimo (kg)</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-center">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stock.map((item) => (
                    <TableRow key={item.producto_id}>
                      <TableCell className="font-mono text-sm">{item.producto_codigo}</TableCell>
                      <TableCell>{item.producto_descripcion}</TableCell>
                      <TableCell className="text-right font-semibold">
                        {Number(item.cantidad).toFixed(3)}
                      </TableCell>
                      <TableCell className="text-right">{Number(item.stock_minimo).toFixed(3)}</TableCell>
                      <TableCell>
                        {item.alerta ? (
                          <Badge variant="destructive" className="flex w-fit items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            STOCK BAJO
                          </Badge>
                        ) : (
                          <Badge variant="outline">OK</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleViewDescargas(item)}
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
      </Card>

      {/* Modal Descargas */}
      {showDescargas && selectedChemical && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle>
                Historial de Descargas: {selectedChemical.producto_descripcion}
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDescargas(false)}
              >
                ✕
              </Button>
            </CardHeader>
            <CardContent>
              {descargas.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">Sin descargas registradas</div>
              ) : (
                <div className="rounded-lg border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Fecha</TableHead>
                        <TableHead>OP</TableHead>
                        <TableHead className="text-right">Cantidad (kg)</TableHead>
                        <TableHead>Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {descargas.map((descarga) => (
                        <TableRow key={descarga.id}>
                          <TableCell className="text-sm">
                            {new Date(descarga.fecha_descarga).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="font-mono">{descarga.orden_produccion}</TableCell>
                          <TableCell className="text-right">
                            {Number(descarga.cantidad_calculada_kg).toFixed(3)}
                          </TableCell>
                          <TableCell>
                            <Badge variant={descarga.estado === 'aplicada' ? 'default' : 'secondary'}>
                              {descarga.estado}
                            </Badge>
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
      )}
    </div>
  );
}
