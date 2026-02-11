import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Users, Building2, Layers, Package, Beaker, Warehouse, ShoppingCart, Factory, Palette } from 'lucide-react';
import {
  User, Sede, Area, Producto, Quimico, Bodega,
  OrdenProduccion, LoteProduccion, FormulaColor, Cliente, PedidoVenta
} from '../../lib/types';
import { ManageUsers } from './ManageUsers';
import { ManageSedes } from './ManageSedes';
import { ManageAreas } from './ManageAreas';
import { ManageProductos } from './ManageProductos';
import { ManageQuimicos } from './ManageQuimicos';
import { ManageFormulas } from './ManageFormulas';
import { ManageBodegas } from './ManageBodegas';
import { ManageClientes } from './ManageClientes';
import { InventoryDashboard } from './InventoryDashboard';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '../ui/table';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { AxiosError } from 'axios';

interface Group {
  id: number;
  name: string;
}

export function AdminSistemasDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [quimicos, setQuimicos] = useState<Quimico[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [ordenesProduccion, setOrdenesProduccion] = useState<OrdenProduccion[]>([]);
  const [lotesProduccion, setLotesProduccion] = useState<LoteProduccion[]>([]);
  const [formulasColor, setFormulasColor] = useState<FormulaColor[]>([]);
  const [pedidosVenta, setPedidosVenta] = useState<PedidoVenta[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedSedeId, setSelectedSedeId] = useState<string>('');

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [
        usersRes, sedesRes, areasRes, productosRes, quimicosRes, bodegasRes,
        ordenesRes, lotesRes, formulasRes, pedidosRes, groupsRes,
        clientesRes
      ] = await Promise.all([
        apiClient.get<User[]>('/users/'),
        apiClient.get<Sede[]>('/sedes/'),
        apiClient.get<Area[]>('/areas/'),
        apiClient.get<Producto[]>('/productos/'),
        apiClient.get<Quimico[]>('/chemicals/'),
        apiClient.get<Bodega[]>('/bodegas/'),
        apiClient.get<OrdenProduccion[]>('/ordenes-produccion/'),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/'),
        apiClient.get<FormulaColor[]>('/formula-colors/'),
        apiClient.get<PedidoVenta[]>('/pedidos-venta/'),
        apiClient.get<Group[]>('/groups/'),
        apiClient.get<Cliente[]>('/clientes/'),
      ]);

      setUsers(usersRes.data);
      setSedes(sedesRes.data);
      setAreas(areasRes.data);
      setProductos(productosRes.data);
      setQuimicos(quimicosRes.data);
      setBodegas(bodegasRes.data);
      setOrdenesProduccion(ordenesRes.data);
      setLotesProduccion(lotesRes.data);
      setFormulasColor(formulasRes.data);
      setPedidosVenta(pedidosRes.data);
      setGroups(groupsRes.data);
      setClientes(clientesRes.data);

      if (sedesRes.data.length > 0) {
        setSelectedSedeId(sedesRes.data[0].id.toString());
      }
    } catch (error) {
      console.error('Error fetching initial data:', error);
      toast.error('Error al cargar datos', { description: 'No se pudieron obtener los datos iniciales del servidor.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const handleSedeCreate = async (sedeData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Sede>('/sedes/', sedeData);
      setSedes(prev => [...prev, response.data]);
      toast.success('Sede creada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', { description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre> });
      } else {
        toast.error('Error al crear la sede');
      }
      return false;
    }
  };

  const handleSedeUpdate = async (sedeId: number, sedeData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Sede>(`/sedes/${sedeId}/`, sedeData);
      setSedes(prev => prev.map(s => s.id === sedeId ? response.data : s));
      toast.success('Sede actualizada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', { description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre> });
      } else {
        toast.error('Error al actualizar la sede');
      }
      return false;
    }
  };

  const handleSedeDelete = async (sedeId: number) => {
    if (window.confirm('¿Estás seguro de eliminar esta sede?')) {
      try {
        await apiClient.delete(`/sedes/${sedeId}/`);
        setSedes(prev => prev.filter(s => s.id !== sedeId));
        toast.success('Sede eliminada exitosamente');
      } catch (error) {
        toast.error('Error al eliminar la sede');
      }
    }
  };

  const handleAreaCreate = async (areaData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Area>('/areas/', areaData);
      setAreas(prev => [...prev, response.data]);
      toast.success('Área creada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', { description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre> });
      } else {
        toast.error('Error al crear el área');
      }
      return false;
    }
  };

  const handleAreaUpdate = async (areaId: number, areaData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Area>(`/areas/${areaId}/`, areaData);
      setAreas(prev => prev.map(a => a.id === areaId ? response.data : a));
      toast.success('Área actualizada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', { description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre> });
      } else {
        toast.error('Error al actualizar el área');
      }
      return false;
    }
  };

  const handleAreaDelete = async (areaId: number) => {
    if (window.confirm('¿Estás seguro de eliminar esta área?')) {
      try {
        await apiClient.delete(`/areas/${areaId}/`);
        setAreas(prev => prev.filter(a => a.id !== areaId));
        toast.success('Área eliminada exitosamente');
      } catch (error) {
        toast.error('Error al eliminar el área');
      }
    }
  };

  const handleUserCreate = async (userData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<User>('/users/', userData);
      setUsers(prevUsers => [...prevUsers, response.data]);
      toast.success('Usuario creado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al crear el usuario');
      }
      console.error('Error creating user:', error);
      return false;
    }
  };

  const handleUserUpdate = async (userId: number, userData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<User>(`/users/${userId}/`, userData);
      setUsers(prevUsers => prevUsers.map(u => u.id === userId ? response.data : u));
      toast.success('Usuario actualizado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al actualizar el usuario');
      }
      console.error('Error updating user:', error);
      return false;
    }
  };

  const handleUserDelete = async (userId: number) => {
    if (window.confirm('¿Estás seguro de eliminar este usuario?')) {
      try {
        await apiClient.delete(`/users/${userId}/`);
        setUsers(prevUsers => prevUsers.filter(u => u.id !== userId));
        toast.success('Usuario eliminado exitosamente');
      } catch (error) {
        toast.error('Error al eliminar el usuario');
        console.error('Error deleting user:', error);
      }
    }
  };

  const handleClienteCreate = async (clienteData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Cliente>('/clientes/', clienteData);
      setClientes(prev => [...prev, response.data]);
      toast.success('Cliente creado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al crear el cliente');
      }
      console.error('Error creating cliente:', error);
      return false;
    }
  };

  const handleClienteUpdate = async (clienteId: number, clienteData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Cliente>(`/clientes/${clienteId}/`, clienteData);
      setClientes(prev => prev.map(c => c.id === clienteId ? response.data : c));
      toast.success('Cliente actualizado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al actualizar el cliente');
      }
      console.error('Error updating cliente:', error);
      return false;
    }
  };

  const handleClienteDelete = async (clienteId: number) => {
    if (window.confirm('¿Estás seguro de eliminar este cliente?')) {
      try {
        await apiClient.delete(`/clientes/${clienteId}/`);
        setClientes(prev => prev.filter(c => c.id !== clienteId));
        toast.success('Cliente eliminado exitosamente');
      } catch (error) {
        toast.error('Error al eliminar el cliente');
        console.error('Error deleting cliente:', error);
      }
    }
  };

  const handleBodegaCreate = async (bodegaData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Bodega>('/bodegas/', bodegaData);
      setBodegas(prev => [...prev, response.data]);
      toast.success('Bodega creada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al crear la bodega');
      }
      console.error('Error creating bodega:', error);
      return false;
    }
  };

  const handleBodegaUpdate = async (bodegaId: number, bodegaData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Bodega>(`/bodegas/${bodegaId}/`, bodegaData);
      setBodegas(prev => prev.map(b => b.id === bodegaId ? response.data : b));
      toast.success('Bodega actualizada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al actualizar la bodega');
      }
      console.error('Error updating bodega:', error);
      return false;
    }
  };

  const handleBodegaDelete = async (bodegaId: number) => {
    if (window.confirm('¿Estás seguro de eliminar esta bodega?')) {
      try {
        await apiClient.delete(`/bodegas/${bodegaId}/`);
        setBodegas(prev => prev.filter(b => b.id !== bodegaId));
        toast.success('Bodega eliminada exitosamente');
      } catch (error) {
        toast.error('Error al eliminar la bodega');
        console.error('Error deleting bodega:', error);
      }
    }
  };

  const handleFormulaCreate = async (formulaData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<FormulaColor>('/formula-colors/', formulaData);
      setFormulasColor(prev => [...prev, response.data]);
      toast.success('Fórmula creada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al crear la fórmula');
      }
      console.error('Error creating formula:', error);
      return false;
    }
  };

  const handleFormulaUpdate = async (formulaId: number, formulaData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<FormulaColor>(`/formula-colors/${formulaId}/`, formulaData);
      setFormulasColor(prev => prev.map(f => f.id === formulaId ? response.data : f));
      toast.success('Fórmula actualizada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al actualizar la fórmula');
      }
      console.error('Error updating formula:', error);
      return false;
    }
  };

  const handleFormulaDelete = async (formulaId: number) => {
    if (window.confirm('¿Estás seguro de eliminar esta fórmula?')) {
      try {
        await apiClient.delete(`/formula-colors/${formulaId}/`);
        setFormulasColor(prev => prev.filter(f => f.id !== formulaId));
        toast.success('Fórmula eliminada exitosamente');
      } catch (error) {
        toast.error('Error al eliminar la fórmula');
        console.error('Error deleting formula:', error);
      }
    }
  };

  const handleChemicalCreate = async (chemicalData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Quimico>('/chemicals/', chemicalData);
      setQuimicos(prev => [...prev, response.data]);
      toast.success('Químico creado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al crear el químico');
      }
      console.error('Error creating chemical:', error);
      return false;
    }
  };

  const handleChemicalUpdate = async (chemicalId: number, chemicalData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Quimico>(`/chemicals/${chemicalId}/`, chemicalData);
      setQuimicos(prev => prev.map(q => q.id === chemicalId ? response.data : q));
      toast.success('Químico actualizado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al actualizar el químico');
      }
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
        toast.error('Error al eliminar el químico');
        console.error('Error deleting chemical:', error);
      }
    }
  };

  const handleProductCreate = async (productData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Producto>('/productos/', productData);
      setProductos(prev => [...prev, response.data]);
      toast.success('Producto creado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al crear el producto');
      }
      console.error('Error creating product:', error);
      return false;
    }
  };

  const handleProductUpdate = async (productId: number, productData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Producto>(`/productos/${productId}/`, productData);
      setProductos(prev => prev.map(p => p.id === productId ? response.data : p));
      toast.success('Producto actualizado exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', {
          description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre>
        });
      } else {
        toast.error('Error al actualizar el producto');
      }
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
        toast.error('Error al eliminar el producto');
        console.error('Error deleting product:', error);
      }
    }
  };


  // Filtrar datos por sede seleccionada
  const selectedSede = sedes.find(s => s.id.toString() === selectedSedeId);
  const sedeAreas = areas.filter(a => a.sede.toString() === selectedSedeId);
  const sedeUsers = users.filter(u => u.sede?.toString() === selectedSedeId);
  const sedeBodegas = bodegas.filter(b => b.sede.toString() === selectedSedeId);
  const sedeOrdenes = ordenesProduccion.filter(o => o.sede.toString() === selectedSedeId);
  const sedePedidos = pedidosVenta.filter(p => p.sede.toString() === selectedSedeId);

  // Calcular estadísticas por sede
  const getSedeStats = (sedeId: string) => {
    const areasCount = areas.filter(a => a.sede.toString() === sedeId).length;
    const usersCount = users.filter(u => u.sede?.toString() === sedeId).length;
    const bodegasCount = bodegas.filter(b => b.sede.toString() === sedeId).length;
    const ordenesCount = ordenesProduccion.filter(o => o.sede.toString() === sedeId).length;
    const pedidosCount = pedidosVenta.filter(p => p.sede.toString() === sedeId).length;

    return { areas: areasCount, users: usersCount, bodegas: bodegasCount, ordenes: ordenesCount, pedidos: pedidosCount };
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      {/* Sidebar de Sedes */}
      <aside className="lg:w-80 flex-shrink-0">
        <Card>
          <CardHeader>
            <CardTitle>Sedes</CardTitle>
            <CardDescription>Selecciona una sede para ver sus datos</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[600px]">
              <div className="space-y-1 p-4">
                {sedes.map((sede) => {
                  const stats = getSedeStats(sede.id.toString());
                  const isSelected = selectedSedeId === sede.id.toString();

                  return (
                    <button
                      key={sede.id}
                      onClick={() => setSelectedSedeId(sede.id.toString())}
                      className={`w-full text-left p-4 rounded-lg border-2 transition-all ${isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50 hover:bg-accent'
                        }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-medium">{sede.nombre}</h3>
                          <p className="text-sm text-muted-foreground">{sede.location}</p>
                        </div>
                        <Badge variant={sede.status === 'activo' ? 'default' : 'secondary'}>
                          {sede.status}
                        </Badge>
                      </div>

                      <Separator className="my-3" />

                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="flex items-center gap-1">
                          <Layers className="w-3 h-3 text-muted-foreground" />
                          <span className="text-muted-foreground">Áreas:</span>
                          <span className="font-medium">{stats.areas}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Users className="w-3 h-3 text-muted-foreground" />
                          <span className="text-muted-foreground">Users:</span>
                          <span className="font-medium">{stats.users}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Warehouse className="w-3 h-3 text-muted-foreground" />
                          <span className="text-muted-foreground">Bodegas:</span>
                          <span className="font-medium">{stats.bodegas}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Factory className="w-3 h-3 text-muted-foreground" />
                          <span className="text-muted-foreground">Órdenes:</span>
                          <span className="font-medium">{stats.ordenes}</span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </aside>

      {/* Contenido Principal */}
      <div className="flex-1 space-y-6">
        <div>
          <h1>Panel de Administración</h1>
          <p className="text-muted-foreground">
            {selectedSede ? `Gestión de ${selectedSede.nombre}` : 'Selecciona una sede'}
          </p>
        </div>

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4">
            <TabsTrigger value="overview">Resumen</TabsTrigger>
            <TabsTrigger value="production">Producción</TabsTrigger>
            <TabsTrigger value="inventory">Inventario</TabsTrigger>
            <TabsTrigger value="management">Gestión</TabsTrigger>
          </TabsList>

          {/* Tab: Resumen */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm">Áreas</CardTitle>
                  <Layers className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl">{sedeAreas.length}</div>
                  <p className="text-xs text-muted-foreground">en esta sede</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm">Usuarios</CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl">{sedeUsers.length}</div>
                  <p className="text-xs text-muted-foreground">personal activo</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm">Bodegas</CardTitle>
                  <Warehouse className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl">{sedeBodegas.length}</div>
                  <p className="text-xs text-muted-foreground">almacenes</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm">Pedidos</CardTitle>
                  <ShoppingCart className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl">{sedePedidos.length}</div>
                  <p className="text-xs text-muted-foreground">órdenes de venta</p>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Áreas de la Sede</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {sedeAreas.length > 0 ? (
                      sedeAreas.map(area => (
                        <div key={area.id} className="flex items-center justify-between p-2 rounded-lg bg-accent">
                          <span>{area.nombre}</span>
                          <Badge variant="outline">ID: {area.id}</Badge>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">No hay áreas registradas</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Bodegas</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {bodegas.length > 0 ? (
                      bodegas.map(bodega => (
                        <div key={bodega.id} className="flex items-center gap-2 p-2 rounded-lg bg-accent">
                          <Warehouse className="w-4 h-4 text-muted-foreground" />
                          <span className="flex-1">{bodega.nombre}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">No hay bodegas registradas</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Tab: Producción */}
          <TabsContent value="production" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Órdenes de Producción</CardTitle>
                <CardDescription>Órdenes activas en {selectedSede?.nombre}</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Código</TableHead>
                      <TableHead>Producto</TableHead>
                      <TableHead>Peso Req.</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Fecha</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sedeOrdenes.length > 0 ? (
                      sedeOrdenes.map(orden => {
                        const producto = productos.find(p => p.id === orden.producto);
                        return (
                          <TableRow key={orden.id}>
                            <TableCell>{orden.codigo}</TableCell>
                            <TableCell>{producto?.descripcion || 'N/A'}</TableCell>
                            <TableCell>{orden.peso_neto_requerido} Kg</TableCell>
                            <TableCell>
                              <Badge variant={
                                orden.estado === 'finalizada' ? 'default' :
                                  orden.estado === 'en_proceso' ? 'secondary' : 'outline'
                              }>
                                {orden.estado}
                              </Badge>
                            </TableCell>
                            <TableCell>{new Date(orden.fecha_creacion).toLocaleDateString()}</TableCell>
                          </TableRow>
                        );
                      })
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground">
                          No hay órdenes de producción
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Palette className="w-5 h-5" />
                    Fórmulas de Color
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {formulasColor.map(formula => (
                      <div key={formula.id} className="flex items-center justify-between p-2 rounded-lg bg-accent">
                        <div>
                          <p className="font-medium">{formula.nombre_color}</p>
                          <p className="text-xs text-muted-foreground">{formula.codigo}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Factory className="w-5 h-5" />
                    Lotes Producidos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {lotesProduccion.map(lote => (
                      <div key={lote.id} className="p-2 rounded-lg bg-accent">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">{lote.codigo_lote}</span>
                          <Badge variant="outline">{lote.peso_neto_producido} Kg</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {lote.maquina} - Turno {lote.turno}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Tab: Inventario */}
          <TabsContent value="inventory" className="space-y-4">
            <InventoryDashboard
              productos={productos}
              bodegas={bodegas}
              lotesProduccion={lotesProduccion}
              onDataRefresh={fetchInitialData}
            />          </TabsContent>

          {/* Tab: Gestión */}
          <TabsContent value="management" className="space-y-4">
            <Tabs defaultValue="users" className="space-y-4">
              <TabsList className="grid w-full grid-cols-3 lg:grid-cols-9">
                <TabsTrigger value="users" className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Usuarios
                </TabsTrigger>
                <TabsTrigger value="sedes" className="flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  Sedes
                </TabsTrigger>
                <TabsTrigger value="areas" className="flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Áreas
                </TabsTrigger>
                <TabsTrigger value="productos" className="flex items-center gap-2">
                  <Package className="w-4 h-4" />
                  Productos
                </TabsTrigger>
                <TabsTrigger value="quimicos" className="flex items-center gap-2">
                  <Beaker className="w-4 h-4" />
                  Químicos
                </TabsTrigger>
                <TabsTrigger value="formulas" className="flex items-center gap-2">
                  <Palette className="w-4 h-4" />
                  Fórmulas
                </TabsTrigger>
                <TabsTrigger value="bodegas" className="flex items-center gap-2">
                  <Warehouse className="w-4 h-4" />
                  Bodegas
                </TabsTrigger>
                <TabsTrigger value="clientes" className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Clientes
                </TabsTrigger>
                <TabsTrigger value="roles" className="flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Roles
                </TabsTrigger>
              </TabsList>

              <TabsContent value="users">
                <ManageUsers
                  users={users}
                  sedes={sedes}
                  areas={areas}
                  groups={groups}
                  onUserCreate={handleUserCreate}
                  onUserUpdate={handleUserUpdate}
                  onUserDelete={handleUserDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="sedes">
                <ManageSedes />
              </TabsContent>

              <TabsContent value="areas">
                <ManageAreas
                  areas={areas}
                  sedes={sedes}
                  onAreaCreate={handleAreaCreate}
                  onAreaUpdate={handleAreaUpdate}
                  onAreaDelete={handleAreaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="productos">
                <ManageProductos
                  productos={productos}
                  onProductCreate={handleProductCreate}
                  onProductUpdate={handleProductUpdate}
                  onProductDelete={handleProductDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="quimicos">
                <ManageQuimicos
                  quimicos={quimicos}
                  onChemicalCreate={handleChemicalCreate}
                  onChemicalUpdate={handleChemicalUpdate}
                  onChemicalDelete={handleChemicalDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="formulas">
                <ManageFormulas
                  formulas={formulasColor}
                  onFormulaCreate={handleFormulaCreate}
                  onFormulaUpdate={handleFormulaUpdate}
                  onFormulaDelete={handleFormulaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="bodegas">
                <ManageBodegas
                  bodegas={bodegas}
                  sedes={sedes}
                  users={users}
                  onBodegaCreate={handleBodegaCreate}
                  onBodegaUpdate={handleBodegaUpdate}
                  onBodegaDelete={handleBodegaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="clientes">
                <ManageClientes
                  clientes={clientes}
                  onClienteCreate={handleClienteCreate}
                  onClienteUpdate={handleClienteUpdate}
                  onClienteDelete={handleClienteDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="roles">
                <Card>
                  <CardHeader>
                    <CardTitle>Roles del Sistema</CardTitle>
                    <CardDescription>Lista de grupos y roles configurados en la base de datos.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {groups.map(group => (
                        <div key={group.id} className="p-4 rounded-lg bg-accent border flex items-center justify-between">
                          <div>
                            <p className="font-bold text-primary">{group.name.replace('_', ' ').toUpperCase()}</p>
                            <p className="text-xs text-muted-foreground italic">Internal ID: {group.id}</p>
                          </div>
                          <Badge variant="secondary">
                            {users.filter(u => u.groups.includes(group.id)).length} Usuarios
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}