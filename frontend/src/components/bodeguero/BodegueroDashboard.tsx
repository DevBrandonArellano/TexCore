import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Package, History, Warehouse, AlertTriangle, ShoppingCart, ChevronLeft, ChevronRight, Download, Beaker, PackagePlus } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Producto, Bodega, LoteProduccion, Proveedor, Quimico } from '../../lib/types';
import { InventoryDashboard } from '../admin-sistemas/InventoryDashboard';
import { useReportesExport } from '../admin-sistemas/useReportesExport';
import { useAuth } from '../../lib/auth';
import { Skeleton } from '../ui/skeleton';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { MRPDashboard } from '../shared/MRPDashboard';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { usePagination } from '../../hooks/usePagination';
import { ManageProductos } from '../admin-sistemas/ManageProductos';
import { ManageQuimicos } from '../admin-sistemas/ManageQuimicos';
import { showApiError } from '../admin-sistemas/sedeUtils';
import { toArray } from '../../lib/collections';

interface AlertaStock {
  producto: string;
  producto_codigo: string;
  bodega: string;
  stock_actual: string;
  stock_minimo: string;
}

type CatalogProductFormData = Partial<Producto> & {
  stock_minimo?: number | string;
  precio_base?: number | string;
};

type CatalogChemicalFormData = Partial<Quimico> & {
  precio_base?: number | string;
};

function buildProductPayload(productData: CatalogProductFormData) {
  return {
    codigo: String(productData.codigo ?? '').trim(),
    descripcion: String(productData.descripcion ?? '').trim(),
    tipo: productData.tipo ?? 'hilo',
    unidad_medida: productData.unidad_medida ?? 'kg',
    stock_minimo: Number(productData.stock_minimo) || 0,
    precio_base: Number(productData.precio_base) || 0,
    presentacion: productData.presentacion?.trim() || null,
    pais_origen: productData.pais_origen?.trim() || null,
    calidad: productData.calidad?.trim() || null,
  };
}

function buildChemicalPayload(chemicalData: CatalogChemicalFormData) {
  return {
    codigo: String(chemicalData.codigo ?? '').trim(),
    descripcion: String(chemicalData.descripcion ?? '').trim(),
    tipo: 'quimico',
    unidad_medida: chemicalData.unidad_medida ?? 'kg',
    stock_minimo: 0,
    precio_base: Number(chemicalData.precio_base) || 0,
    presentacion: chemicalData.presentacion?.trim() || null,
  };
}

function AlertasStockView({ bodegas }: { bodegas: Bodega[] }) {
  const [alertas, setAlertas] = useState<AlertaStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportBodega, setExportBodega] = useState('');
  const { loading: exportLoading, handleExport } = useReportesExport(exportBodega);
  const ITEMS_PER_PAGE = 20;

  const {
    currentPage: safePage,
    setCurrentPage,
    totalPages,
    paginatedItems: paginatedAlertas,
  } = usePagination(alertas, ITEMS_PER_PAGE, { resetKey: alertas.length });

  useEffect(() => {
    const fetchAlertas = async () => {
      try {
        const response = await apiClient.get('/inventory/alertas-stock/');
        setAlertas(Array.isArray(response.data) ? response.data : (response.data as any).results || []);
      } catch (error) {
        console.error('Error fetching alertas:', error);
        toast.error('Error al cargar las alertas de stock');
      } finally {
        setLoading(false);
      }
    };
    fetchAlertas();
  }, []);

  const exportarBar = (
    <div className="flex flex-col sm:flex-row sm:items-end gap-3 mb-4">
      <div className="flex-1 space-y-1">
        <span className="text-xs text-muted-foreground">Bodega a exportar</span>
        <Select value={exportBodega} onValueChange={setExportBodega}>
          <SelectTrigger className="bg-background">
            <SelectValue placeholder="Selecciona una bodega" />
          </SelectTrigger>
          <SelectContent>
            {bodegas.map((b) => (
              <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        variant="outline"
        className="gap-2"
        onClick={() => handleExport('stock-bajo')}
        disabled={exportLoading['stock-bajo'] || !exportBodega}
      >
        <Download className="w-4 h-4" />
        {exportLoading['stock-bajo'] ? 'Generando...' : 'Exportar Excel'}
      </Button>
    </div>
  );

  if (loading) {
    return (
      <div className="space-y-3">
        {exportarBar}
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (alertas.length === 0) {
    return (
      <div>
        {exportarBar}
        <div className="text-center py-8 text-muted-foreground">
          <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No hay alertas de stock bajo en este momento.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      {exportarBar}
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
            onClick={() => setCurrentPage((p) => p - 1)}
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
            onClick={() => setCurrentPage((p) => p + 1)}
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
  const [quimicos, setQuimicos] = useState<Quimico[]>([]);
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

      let quimicosRes = { data: [] };
      try {
         quimicosRes = await apiClient.get('/chemicals/');
      } catch (e) {
        console.warn("No se pudieron cargar químicos");
      }

      setProductos(toArray<Producto>(productosRes.data));
      setQuimicos(toArray<Quimico>(quimicosRes.data));
      setBodegas(toArray<Bodega>(bodegasRes.data));
      setLotesProduccion(toArray<LoteProduccion>(lotesRes.data));
      setProveedores(toArray<Proveedor>(provRes.data));
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

  const currentSedeId = profile?.user?.sede ? Number(profile.user.sede) : null;

  const handleProductCreate = async (productData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Producto>('/productos/', {
        ...buildProductPayload(productData),
        sede: currentSedeId,
      });
      setProductos(prev => [...prev, response.data]);
      toast.success('Producto creado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'el producto');
      console.error('Error creating product:', error);
      return false;
    }
  };

  const handleProductUpdate = async (productId: number, productData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Producto>(`/productos/${productId}/`, buildProductPayload(productData));
      setProductos(prev => prev.map(p => p.id === productId ? response.data : p));
      toast.success('Producto actualizado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'update', 'el producto');
      console.error('Error updating product:', error);
      return false;
    }
  };

  const handleProductDelete = async (productId: number) => {
    if (window.confirm('¿Estás seguro de eliminar este producto?')) {
      try {
        await apiClient.delete(`/productos/${productId}/`);
        setProductos(prev => prev.filter(p => p.id !== productId));
        toast.success('Producto eliminado exitosamente');
      } catch (error) {
        showApiError(error, 'delete', 'el producto');
        console.error('Error deleting product:', error);
      }
    }
  };

  const handleChemicalCreate = async (chemicalData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Quimico>('/chemicals/', {
        ...buildChemicalPayload(chemicalData),
        sede: currentSedeId,
      });
      setQuimicos(prev => [...prev, response.data]);
      toast.success('Químico creado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'el químico');
      console.error('Error creating chemical:', error);
      return false;
    }
  };

  const handleChemicalUpdate = async (chemicalId: number, chemicalData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Quimico>(`/chemicals/${chemicalId}/`, buildChemicalPayload(chemicalData));
      setQuimicos(prev => prev.map(q => q.id === chemicalId ? response.data : q));
      toast.success('Químico actualizado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'update', 'el químico');
      console.error('Error updating chemical:', error);
      return false;
    }
  };

  const handleChemicalDelete = async (chemicalId: number) => {
    if (window.confirm('¿Estás seguro de eliminar este químico?')) {
      try {
        await apiClient.delete(`/chemicals/${chemicalId}/`);
        setQuimicos(prev => prev.filter(q => q.id !== chemicalId));
        toast.success('Químico eliminado exitosamente');
      } catch (error) {
        showApiError(error, 'delete', 'el químico');
        console.error('Error deleting chemical:', error);
      }
    }
  };

  return (
    <div className="flex flex-col space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Panel de Bodeguero
          </h1>
          <p className="text-sm text-muted-foreground">
            Bienvenido, {profile?.user?.first_name || profile?.user?.username}. Gestiona el inventario y las transferencias.
          </p>
        </div>
        <div className="flex items-center gap-3 self-start sm:self-auto">
          <Button variant="outline" onClick={fetchInitialData} disabled={isLoading} className="text-xs sm:text-sm">
            <History className="w-4 h-4 mr-2" />
            Actualizar Datos
          </Button>
          <Warehouse className="w-8 h-8 text-primary shrink-0 hidden sm:block" />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 flex-shrink-0">
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
        <TabsList className="flex flex-wrap w-full sm:w-auto gap-1">
          <TabsTrigger value="inventario" className="gap-2 flex-1 sm:flex-initial">
            <Package className="w-4 h-4" />
            <span>Inventario</span>
          </TabsTrigger>
          <TabsTrigger value="alertas" className="gap-2 flex-1 sm:flex-initial">
            <AlertTriangle className="w-4 h-4" />
            <span>Alertas</span>
          </TabsTrigger>
          <TabsTrigger value="mrp" className="gap-2 flex-1 sm:flex-initial">
            <ShoppingCart className="w-4 h-4" />
            <span>MRP</span>
          </TabsTrigger>
          <TabsTrigger value="catalogos" className="gap-2 flex-1 sm:flex-initial">
            <PackagePlus className="w-4 h-4" />
            <span>Catálogos</span>
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
              <AlertasStockView bodegas={bodegas} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mrp" className="mt-4">
           <MRPDashboard />
        </TabsContent>

        <TabsContent value="catalogos" className="mt-4">
          <Card>
            <CardHeader className="flex-shrink-0">
              <CardTitle>Gestión de Productos e Insumos</CardTitle>
              <CardDescription>
                Crea y actualiza productos, insumos y químicos para mantener los catálogos de bodega al día.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 md:p-6">
              <Tabs defaultValue="productos" className="space-y-4">
                <TabsList className="grid w-full grid-cols-1 sm:grid-cols-2">
                  <TabsTrigger value="productos" className="gap-2">
                    <Package className="w-4 h-4" />
                    Productos e Insumos
                  </TabsTrigger>
                  <TabsTrigger value="quimicos" className="gap-2">
                    <Beaker className="w-4 h-4" />
                    Químicos
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="productos">
                  <ManageProductos
                    productos={productos}
                    onProductCreate={handleProductCreate}
                    onProductUpdate={handleProductUpdate}
                    onProductDelete={handleProductDelete}
                    loading={isLoading}
                  />
                </TabsContent>
                <TabsContent value="quimicos">
                  <ManageQuimicos
                    quimicos={quimicos}
                    onChemicalCreate={handleChemicalCreate}
                    onChemicalUpdate={handleChemicalUpdate}
                    onChemicalDelete={handleChemicalDelete}
                    loading={isLoading}
                  />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
