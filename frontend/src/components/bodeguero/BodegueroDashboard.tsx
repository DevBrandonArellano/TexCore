import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Package, Send, History, Warehouse, AlertTriangle } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Producto, Bodega, LoteProduccion } from '../../lib/types';
import { InventoryDashboard } from '../admin-sistemas/InventoryDashboard';
import { useAuth } from '../../lib/auth';
import { Skeleton } from '../ui/skeleton';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';

interface AlertaStock {
  producto: string;
  producto_codigo: string;
  bodega: string;
  stock_actual: string;
  stock_minimo: string;
}

function AlertasStockView() {
  const [alertas, setAlertas] = useState<AlertaStock[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlertas = async () => {
      try {
        const response = await apiClient.get('/inventory/alertas-stock/');
        setAlertas(response.data);
      } catch (error) {
        console.error('Error fetching alertas:', error);
        toast.error('Error al cargar las alertas de stock');
      } finally {
        setLoading(false);
      }
    };
    fetchAlertas();
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (alertas.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No hay alertas de stock bajo en este momento.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Código</TableHead>
            <TableHead>Producto</TableHead>
            <TableHead>Bodega</TableHead>
            <TableHead className="text-right">Stock Actual</TableHead>
            <TableHead className="text-right">Stock Mínimo</TableHead>
            <TableHead>Estado</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {alertas.map((alerta, index) => (
            <TableRow key={index}>
              <TableCell className="font-mono">{alerta.producto_codigo}</TableCell>
              <TableCell>{alerta.producto}</TableCell>
              <TableCell>{alerta.bodega}</TableCell>
              <TableCell className="text-right font-medium text-destructive">
                {alerta.stock_actual}
              </TableCell>
              <TableCell className="text-right">{alerta.stock_minimo}</TableCell>
              <TableCell>
                <Badge variant="destructive" className="gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Stock Bajo
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function BodegueroDashboard() {
  const { profile } = useAuth();
  const [productos, setProductos] = useState<Producto[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [lotesProduccion, setLotesProduccion] = useState<LoteProduccion[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [productosRes, bodegasRes, lotesRes] = await Promise.all([
        apiClient.get('/productos/'),
        apiClient.get('/bodegas/'),
        apiClient.get('/lotes-produccion/'),
      ]);
      setProductos(productosRes.data);
      setBodegas(bodegasRes.data);
      setLotesProduccion(lotesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar los datos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Panel de Bodeguero
          </h1>
          <p className="text-muted-foreground">
            Bienvenido, {profile?.user?.first_name || profile?.user?.username}. Gestiona el inventario y las transferencias.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Warehouse className="w-8 h-8 text-primary" />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Productos</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : productos.length}</div>
            <p className="text-xs text-muted-foreground">productos registrados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Bodegas</CardTitle>
            <Warehouse className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : bodegas.length}</div>
            <p className="text-xs text-muted-foreground">bodegas en el sistema</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Lotes</CardTitle>
            <History className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : lotesProduccion.length}</div>
            <p className="text-xs text-muted-foreground">lotes de producción</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="inventario" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 lg:w-auto lg:inline-grid">
          <TabsTrigger value="inventario" className="gap-2">
            <Package className="w-4 h-4" />
            <span className="hidden sm:inline">Inventario</span>
          </TabsTrigger>
          <TabsTrigger value="alertas" className="gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span className="hidden sm:inline">Alertas</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="inventario">
          <Card>
            <CardHeader>
              <CardTitle>Gestión de Inventario</CardTitle>
              <CardDescription>
                Consulta el stock actual, registra entradas, realiza transferencias y gestiona el inventario.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <InventoryDashboard
                productos={productos}
                bodegas={bodegas}
                lotesProduccion={lotesProduccion}
                onDataRefresh={fetchData}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alertas">
          <Card>
            <CardHeader>
              <CardTitle>Alertas de Stock Bajo</CardTitle>
              <CardDescription>
                Productos que están por debajo del stock mínimo configurado.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AlertasStockView />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
