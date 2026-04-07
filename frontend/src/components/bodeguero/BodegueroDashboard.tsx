import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Package, Send, History, Warehouse, AlertTriangle, ShoppingCart, ChevronLeft, ChevronRight } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Producto, Bodega, LoteProduccion, Proveedor } from '../../lib/types';
import { InventoryDashboard } from '../admin-sistemas/InventoryDashboard';
import { useAuth } from '../../lib/auth';
import { Skeleton } from '../ui/skeleton';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { MRPDashboard } from '../shared/MRPDashboard';
import { Input } from '../ui/input';

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
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 20;

  const totalPages = Math.max(1, Math.ceil(alertas.length / ITEMS_PER_PAGE));
  const safePage = Math.min(Math.max(1, currentPage), totalPages);
  const paginatedAlertas = alertas.slice(
    (safePage - 1) * ITEMS_PER_PAGE,
    safePage * ITEMS_PER_PAGE
  );

  useEffect(() => {
    const fetchAlertas = async () => {
      try {
        const response = await apiClient.get('/inventory/alertas-stock/');
        setAlertas(response.data);
        setCurrentPage(1);
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
          {paginatedAlertas.map((alerta, index) => (
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
      <div className="flex items-center justify-between mt-4">
        <span className="text-sm text-muted-foreground">
          Página {safePage} de {totalPages}
        </span>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={safePage === 1}
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
            disabled={safePage === totalPages}
          >
            Siguiente
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export function BodegueroDashboard() {
  const { profile } = useAuth();
  const [productos, setProductos] = useState<Producto[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [lotesProduccion, setLotesProduccion] = useState<LoteProduccion[]>([]);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchInitialData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [productosRes, bodegasRes] = await Promise.all([
        apiClient.get('/productos/'),
        apiClient.get('/bodegas/'),
      ]);
        
      // Fetch lotes solo si hay productos (opcional, ajusta según tu lógica)
      let lotesRes = { data: [] };
      try {
         lotesRes = await apiClient.get('/lotes-produccion/');
      } catch (e) {
        console.warn("No se pudieron cargar lotes", e);
      }

      let provRes = { data: [] };
      try {
         provRes = await apiClient.get('/proveedores/');
      } catch (e) {
        console.warn("No se pudieron cargar proveedores");
      }

      setProductos(productosRes.data);
      setBodegas(bodegasRes.data);
      setLotesProduccion(lotesRes.data);
      setProveedores(provRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar los datos');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  return (
    <div className="flex flex-col space-y-6 p-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
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
      <div className="grid gap-4 md:grid-cols-3 flex-shrink-0">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Productos</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : productos.length}</div>
            <p className="text-xs text-muted-foreground">productos registrados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Bodegas</CardTitle>
            <Warehouse className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : bodegas.length}</div>
            <p className="text-xs text-muted-foreground">bodegas en el sistema</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Lotes</CardTitle>
            <History className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? '...' : lotesProduccion.length}</div>
            <p className="text-xs text-muted-foreground">lotes de producción</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="inventario" className="flex flex-col">
        <TabsList className="grid w-full grid-cols-2 lg:w-auto lg:inline-grid flex-shrink-0">
          <TabsTrigger value="inventario" className="gap-2">
            <Package className="w-4 h-4" />
            <span className="hidden sm:inline">Inventario</span>
          </TabsTrigger>
          <TabsTrigger value="alertas" className="gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span className="hidden sm:inline">Alertas</span>
          </TabsTrigger>
          <TabsTrigger value="mrp" className="gap-2">
            <ShoppingCart className="w-4 h-4" />
            <span className="hidden sm:inline">MRP</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="inventario" className="mt-4">
          <Card>
            <CardHeader className="flex-shrink-0">
              <CardTitle>Gestión de Inventario</CardTitle>
              <CardDescription>
                Consulta el stock actual, registra entradas, realiza transferencias y gestiona el inventario.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 md:p-6">
              <InventoryDashboard
                productos={productos}
                bodegas={bodegas}
                lotesProduccion={lotesProduccion}
                proveedores={proveedores}
                onDataRefresh={fetchInitialData}
                sedeId={profile?.user?.sede?.toString()}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alertas" className="mt-4">
          <Card>
            <CardHeader className="flex-shrink-0">
              <CardTitle>Alertas de Stock Bajo</CardTitle>
              <CardDescription>
                Productos que están por debajo del stock mínimo configurado.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 md:p-6">
              <AlertasStockView />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mrp" className="mt-4">
           <MRPDashboard />
        </TabsContent>
      </Tabs>
    </div>
  );
}
