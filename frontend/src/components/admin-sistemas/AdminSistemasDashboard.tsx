import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Users, Building2, Layers, Package, Beaker, Warehouse, ShoppingCart, Factory, Palette, Truck } from 'lucide-react';
import {
  User, Sede, Area, Producto, Quimico, Bodega,
  OrdenProduccion, LoteProduccion, FormulaColor, Cliente, PedidoVenta, Proveedor
} from '../../lib/types';
import { ManageUsers } from './ManageUsers';
import { ManageSedes } from './ManageSedes';
import { ManageAreas } from './ManageAreas';
import { ManageProductos } from './ManageProductos';
import { ManageQuimicos } from './ManageQuimicos';
import { ManageFormulas } from './ManageFormulas';
import { ManageBodegas } from './ManageBodegas';
import { ManageClientes } from './ManageClientes';
import { ManageProveedores } from './ManageProveedores';
import { InventoryDashboard } from './InventoryDashboard';
import { AuditLogViewer } from '../shared/AuditLogViewer';
import { ErrorBoundary } from '../shared/ErrorBoundary';
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

/** Helper para mostrar errores de API de forma consistente en gestión */
function showApiError(error: unknown, action: 'create' | 'update' | 'delete', entity: string) {
  const axiosError = error as AxiosError<Record<string, unknown>>;
  const actionLabel = action === 'create' ? 'crear' : action === 'update' ? 'actualizar' : 'eliminar';
  if (axiosError.response?.status === 400) {
    const data = axiosError.response.data;
    const msg = typeof data === 'object' && data !== null
      ? Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`).join('; ')
      : String(data);
    toast.error('Error de validación', { description: msg });
  } else if (axiosError.response?.status === 403) {
    toast.error(`No tienes permiso para ${actionLabel} ${entity}`);
  } else if (axiosError.response?.status === 401) {
    toast.error('Sesión expirada. Inicia sesión de nuevo.');
  } else {
    const detail = axiosError.response?.data;
    const errMsg = typeof detail === 'object' && detail && 'detail' in detail
      ? String((detail as { detail?: unknown }).detail) : `Error al ${actionLabel} ${entity}`;
    toast.error(errMsg || `Error al ${actionLabel} ${entity}`);
  }
}

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
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [loading, setLoading] = useState(true);

  const [searchParams, setSearchParams] = useSearchParams();
  const selectedSedeId = searchParams.get('sede') || '';

  const fetchInitialData = async () => {
    setLoading(true);
    
    // Limpieza de estados para evitar "flashes" de la sede anterior
    setUsers([]);
    setAreas([]);
    setProductos([]);
    setQuimicos([]);
    setBodegas([]);
    setOrdenesProduccion([]);
    setLotesProduccion([]);
    setFormulasColor([]);
    setPedidosVenta([]);
    setClientes([]);
    setProveedores([]);

    try {
      const params = selectedSedeId ? { params: { sede_id: selectedSedeId } } : {};
      
      const [
        usersRes, sedesRes, areasRes, productosRes, quimicosRes, bodegasRes,
        ordenesRes, lotesRes, formulasRes, pedidosRes, groupsRes,
        clientesRes, provRes
      ] = await Promise.all([
        apiClient.get<User[]>('/users/', params),
        apiClient.get<Sede[]>('/sedes/'),
        apiClient.get<Area[]>('/areas/', params),
        apiClient.get<Producto[]>('/productos/', params),
        apiClient.get<Quimico[]>('/chemicals/', params),
        apiClient.get<Bodega[]>('/bodegas/', params),
        apiClient.get<OrdenProduccion[]>('/ordenes-produccion/', params),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/', params),
        apiClient.get<FormulaColor[]>('/formula-colors/', params),
        apiClient.get<PedidoVenta[]>('/pedidos-venta/', params),
        apiClient.get<Group[]>('/groups/'),
        apiClient.get<Cliente[]>('/clientes/', params),
        apiClient.get<Proveedor[]>('/proveedores/', params),
      ]);

      const getData = (res: any) => {
        if (res && res.data) {
          if (Array.isArray(res.data.results)) return res.data.results;
          if (Array.isArray(res.data)) return res.data;
        }
        return [];
      };

      setUsers(getData(usersRes));
      setSedes(getData(sedesRes));
      setAreas(getData(areasRes));
      setProductos(getData(productosRes));
      setQuimicos(getData(quimicosRes));
      setBodegas(getData(bodegasRes));
      setOrdenesProduccion(getData(ordenesRes));
      setLotesProduccion(getData(lotesRes));
      setFormulasColor(getData(formulasRes));
      setPedidosVenta(getData(pedidosRes));
      setGroups(getData(groupsRes));
      setClientes(getData(clientesRes));
      setProveedores(getData(provRes));

      if (sedesRes.data.length > 0 && !selectedSedeId) {
        setSearchParams(prev => {
          prev.set('sede', sedesRes.data[0].id.toString());
          return prev;
        }, { replace: true });
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
  }, [selectedSedeId]);

  const handleSedeCreate = async (sedeData: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<Sede>('/sedes/', sedeData);
      setSedes(prev => [...prev, response.data]);
      toast.success('Sede creada exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'la sede');
      console.error('Error creating sede:', error);
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
      showApiError(error, 'update', 'la sede');
      console.error('Error updating sede:', error);
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
        showApiError(error, 'delete', 'la sede');
        console.error('Error deleting sede:', error);
      }
    }
  };

  const handleAreaCreate = async (areaData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedes.length > 0) {
        toast.error('Selecciona una sede en el menú lateral antes de crear un área');
        return false;
      }
      const payload = {
        ...areaData,
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      if (!payload.sede) {
        toast.error('No hay sedes disponibles. Crea o selecciona una sede primero.');
        return false;
      }
      const response = await apiClient.post<Area>('/areas/', payload);
      setAreas(prev => [...prev, response.data]);
      toast.success('Área creada exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'el área');
      console.error('Error creating area:', error);
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
      showApiError(error, 'update', 'el área');
      console.error('Error updating area:', error);
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
        showApiError(error, 'delete', 'el área');
        console.error('Error deleting area:', error);
      }
    }
  };

  const handleUserCreate = async (userData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedes.length > 0) {
        toast.error('Selecciona una sede en el menú lateral antes de crear un usuario');
        return false;
      }
      const payload = {
        ...userData,
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      const response = await apiClient.post<User>('/users/', payload);
      setUsers(prevUsers => [...prevUsers, response.data]);
      toast.success('Usuario creado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'el usuario');
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
      showApiError(error, 'update', 'el usuario');
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
        showApiError(error, 'delete', 'el usuario');
        console.error('Error deleting user:', error);
      }
    }
  };

  const handleClienteCreate = async (clienteData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedes.length > 0) {
        toast.error('Selecciona una sede en el menú lateral antes de crear un cliente');
        return false;
      }
      const payload = {
        ...clienteData,
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      const response = await apiClient.post<Cliente>('/clientes/', payload);
      setClientes(prev => [...prev, response.data]);
      toast.success('Cliente creado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'el cliente');
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
      showApiError(error, 'update', 'el cliente');
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
        showApiError(error, 'delete', 'el cliente');
        console.error('Error deleting cliente:', error);
      }
    }
  };

  const handleBodegaCreate = async (bodegaData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedes.length > 0) {
        toast.error('Selecciona una sede en el menú lateral antes de crear una bodega');
        return false;
      }
      const payload = {
        ...bodegaData,
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      const response = await apiClient.post<Bodega>('/bodegas/', payload);
      setBodegas(prev => [...prev, response.data]);
      toast.success('Bodega creada exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'la bodega');
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
      showApiError(error, 'update', 'la bodega');
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
        showApiError(error, 'delete', 'la bodega');
        console.error('Error deleting bodega:', error);
      }
    }
  };

  const handleFormulaCreate = async (formulaData: any): Promise<boolean> => {
    try {
      const payload = {
        ...formulaData,
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      const response = await apiClient.post<FormulaColor>('/formula-colors/', payload);
      setFormulasColor(prev => [...prev, response.data]);
      toast.success('Fórmula creada exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'la fórmula');
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
      showApiError(error, 'update', 'la fórmula');
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
        showApiError(error, 'delete', 'la fórmula');
        console.error('Error deleting formula:', error);
      }
    }
  };

  const handleChemicalCreate = async (chemicalData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedes.length > 0) {
        toast.error('Selecciona una sede en el menú lateral antes de crear un químico');
        return false;
      }
      const payload = {
        codigo: String(chemicalData.codigo ?? '').trim(),
        descripcion: String(chemicalData.descripcion ?? '').trim(),
        tipo: 'quimico',
        unidad_medida: chemicalData.unidad_medida ?? 'kg',
        stock_minimo: 0,
        precio_base: Number(chemicalData.precio_base) || 0,
        presentacion: chemicalData.presentacion?.trim() || null,
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      const response = await apiClient.post<Quimico>('/chemicals/', payload);
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
      const payload: Record<string, unknown> = {
        codigo: String(chemicalData.codigo ?? '').trim(),
        descripcion: String(chemicalData.descripcion ?? '').trim(),
        tipo: 'quimico',
        unidad_medida: chemicalData.unidad_medida ?? 'kg',
        presentacion: chemicalData.presentacion?.trim() || null,
        precio_base: Number(chemicalData.precio_base) || 0,
      };
      const response = await apiClient.patch<Quimico>(`/chemicals/${chemicalId}/`, payload);
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

  const handleProductCreate = async (productData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedes.length > 0) {
        toast.error('Selecciona una sede en el menú lateral antes de crear un producto');
        return false;
      }
      // Construir payload compatible con el backend (Producto model)
      const payload = {
        codigo: String(productData.codigo ?? '').trim(),
        descripcion: String(productData.descripcion ?? '').trim(),
        tipo: productData.tipo ?? 'hilo',
        unidad_medida: productData.unidad_medida ?? 'kg',
        stock_minimo: Number(productData.stock_minimo) || 0,
        precio_base: Number(productData.precio_base) || 0,
        presentacion: productData.presentacion?.trim() || null,
        pais_origen: productData.pais_origen?.trim() || null,
        calidad: productData.calidad?.trim() || null,
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      const response = await apiClient.post<Producto>('/productos/', payload);
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
      const payload: Record<string, unknown> = {
        codigo: String(productData.codigo ?? '').trim(),
        descripcion: String(productData.descripcion ?? '').trim(),
        tipo: productData.tipo ?? 'hilo',
        unidad_medida: productData.unidad_medida ?? 'kg',
        stock_minimo: Number(productData.stock_minimo) || 0,
        presentacion: productData.presentacion?.trim() || null,
        pais_origen: productData.pais_origen?.trim() || null,
        calidad: productData.calidad?.trim() || null,
      };
      if (productData.precio_base != null && !Number.isNaN(Number(productData.precio_base))) {
        payload.precio_base = Number(productData.precio_base);
      }
      const response = await apiClient.patch<Producto>(`/productos/${productId}/`, payload);
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

  const handleProveedorCreate = async (proveedorData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedes.length > 0) {
        toast.error('Selecciona una sede en el menú lateral antes de crear un proveedor');
        return false;
      }
      const payload = {
        nombre: String(proveedorData.nombre ?? '').trim(),
        sede: selectedSedeId ? parseInt(selectedSedeId, 10) : null
      };
      const response = await apiClient.post<Proveedor>('/proveedores/', payload);
      setProveedores(prev => [...prev, response.data]);
      toast.success('Proveedor creado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'create', 'el proveedor');
      console.error('Error creating proveedor:', error);
      return false;
    }
  };

  const handleProveedorUpdate = async (proveedorId: number, proveedorData: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<Proveedor>(`/proveedores/${proveedorId}/`, proveedorData);
      setProveedores(prev => prev.map(p => p.id === proveedorId ? response.data : p));
      toast.success('Proveedor actualizado exitosamente');
      return true;
    } catch (error) {
      showApiError(error, 'update', 'el proveedor');
      console.error('Error updating proveedor:', error);
      return false;
    }
  };

  const handleProveedorDelete = async (proveedorId: number) => {
    if (window.confirm('¿Estás seguro de eliminar este proveedor?')) {
      try {
        await apiClient.delete(`/proveedores/${proveedorId}/`);
        setProveedores(prev => prev.filter(p => p.id !== proveedorId));
        toast.success('Proveedor eliminado exitosamente');
      } catch (error) {
        showApiError(error, 'delete', 'el proveedor');
        console.error('Error deleting proveedor:', error);
      }
    }
  };

  // Filtrar datos por sede seleccionada (asegurar arrays por si la API devuelve formato paginado)
  const _sedes = Array.isArray(sedes) ? sedes : [];
  const selectedSede = _sedes.find(s => s.id.toString() === selectedSedeId);

  const _areas = Array.isArray(areas) ? areas : [];
  const _users = Array.isArray(users) ? users : [];
  const _bodegas = Array.isArray(bodegas) ? bodegas : [];
  const _ordenes = Array.isArray(ordenesProduccion) ? ordenesProduccion : [];
  const _pedidos = Array.isArray(pedidosVenta) ? pedidosVenta : [];
  const _productos = Array.isArray(productos) ? productos : [];
  const _clientes = Array.isArray(clientes) ? clientes : [];
  const _proveedores = Array.isArray(proveedores) ? proveedores : [];
  const _quimicos = Array.isArray(quimicos) ? quimicos : [];
  const _formulas = Array.isArray(formulasColor) ? formulasColor : [];

  const sedeAreas = selectedSedeId
    ? _areas.filter(a => a.sede?.toString() === selectedSedeId)
    : _areas;

  const sedeUsers = selectedSedeId
    ? _users.filter(u => u.sede?.toString() === selectedSedeId)
    : _users;

  const sedeBodegas = selectedSedeId
    ? _bodegas.filter(b => b.sede?.toString() === selectedSedeId)
    : _bodegas;

  const sedeOrdenes = selectedSedeId
    ? _ordenes.filter(o => o.sede?.toString() === selectedSedeId)
    : _ordenes;

  const sedePedidos = selectedSedeId
    ? _pedidos.filter(p => p.sede?.toString() === selectedSedeId)
    : _pedidos;

  // Calcular estadísticas por sede
  const getSedeStats = (sedeId: string) => {
    const sedeObj = sedes.find(s => s.id.toString() === sedeId);
    
    // Si tenemos los conteos anotados del backend (para todas las sedes)
    if (sedeObj && sedeObj.num_areas !== undefined) {
      return { 
        areas: sedeObj.num_areas, 
        users: sedeObj.num_users || 0, 
        bodegas: sedeObj.num_bodegas || 0, 
        ordenes: sedeObj.num_ordenes || 0, 
        pedidos: 0 // Este campo no está anotado aún
      };
    }

    // Fallback: Calcular de los arreglos locales (solo funcionará bien para la sede seleccionada)
    const areasCount = _areas.filter(a => a.sede?.toString() === sedeId).length;
    const usersCount = _users.filter(u => u.sede?.toString() === sedeId).length;
    const bodegasCount = _bodegas.filter(b => b.sede?.toString() === sedeId).length;
    const ordenesCount = _ordenes.filter(o => o.sede?.toString() === sedeId).length;
    const pedidosCount = _pedidos.filter(p => p.sede?.toString() === sedeId).length;

    return { areas: areasCount, users: usersCount, bodegas: bodegasCount, ordenes: ordenesCount, pedidos: pedidosCount };
  };

  return (
    <div className="flex h-full gap-6 p-4">
      {/* Sidebar de Sedes */}
      <aside className="lg:w-80 flex-shrink-0 flex flex-col">
        <Card className="flex-1 flex flex-col min-h-0">
          <CardHeader className="flex-shrink-0">
            <CardTitle>Sedes</CardTitle>
            <CardDescription>Selecciona una sede para ver sus datos</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-0">
              <div className="space-y-1 p-4">
                {_sedes.map((sede) => {
                  const stats = getSedeStats(sede.id.toString());
                  const isSelected = selectedSedeId === sede.id.toString();

                  return (
                    <button
                      key={sede.id}
                      onClick={() => {
                        setSearchParams(prev => {
                          prev.set('sede', sede.id.toString());
                          prev.set('page', '1');
                          return prev;
                        }, { replace: true });
                      }}
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
          </CardContent>
        </Card>
      </aside>

      {/* Contenido Principal */}
      <div className="flex-1 overflow-y-auto min-w-0 pr-4 space-y-6">
        <div>
          <h1>Panel de Administración</h1>
          <p className="text-muted-foreground">
            {selectedSede ? `Gestión de ${selectedSede.nombre}` : 'Selecciona una sede'}
          </p>
        </div>

        <Tabs
          defaultValue="overview"
          onValueChange={(v) => {
            if (v === 'management' || v === 'inventory' || v === 'audit') {
              setSearchParams(prev => {
                prev.set('page', '1');
                return prev;
              }, { replace: true });
            }
          }}
          className="space-y-4"
        >
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5">
            <TabsTrigger value="overview">Resumen</TabsTrigger>
            <TabsTrigger value="production">Producción</TabsTrigger>
            <TabsTrigger value="inventory">Inventario</TabsTrigger>
            <TabsTrigger value="management">Gestión</TabsTrigger>
            <TabsTrigger value="audit">Auditoría</TabsTrigger>
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
                    {_formulas.map(formula => (
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
                    {(Array.isArray(lotesProduccion) ? lotesProduccion : []).map(lote => (
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
              sedeId={selectedSedeId || undefined}
              productos={selectedSedeId ? _productos.filter(p => p.sede?.toString() === selectedSedeId) : _productos}
              bodegas={sedeBodegas}
              lotesProduccion={lotesProduccion}
              proveedores={proveedores}
              onDataRefresh={fetchInitialData}
            />          </TabsContent>

          {/* Tab: Gestión */}
          <TabsContent value="management" className="space-y-4">
            <Tabs
              defaultValue="users"
              onValueChange={() => {
                setSearchParams(prev => {
                  prev.set('page', '1');
                  return prev;
                }, { replace: true });
              }}
              className="space-y-4"
            >
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
                <TabsTrigger value="proveedores" className="flex items-center gap-2">
                  <Truck className="w-4 h-4" />
                  Proveedores
                </TabsTrigger>
                <TabsTrigger value="roles" className="flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Roles
                </TabsTrigger>
              </TabsList>

              <TabsContent value="users">
                <ManageUsers
                  users={sedeUsers}
                  sedes={sedes}
                  areas={sedeAreas}
                  groups={groups}
                  selectedSedeId={selectedSedeId || undefined}
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
                  areas={sedeAreas}
                  sedes={sedes}
                  selectedSedeId={selectedSedeId ?? undefined}
                  onAreaCreate={handleAreaCreate}
                  onAreaUpdate={handleAreaUpdate}
                  onAreaDelete={handleAreaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="productos">
                <ManageProductos
                  productos={selectedSedeId
                    ? _productos.filter(p => !p.sede || p.sede.toString() === selectedSedeId)
                    : _productos
                  }
                  onProductCreate={handleProductCreate}
                  onProductUpdate={handleProductUpdate}
                  onProductDelete={handleProductDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="quimicos">
                <ManageQuimicos
                  quimicos={_quimicos}
                  onChemicalCreate={handleChemicalCreate}
                  onChemicalUpdate={handleChemicalUpdate}
                  onChemicalDelete={handleChemicalDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="formulas">
                <ManageFormulas
                  formulas={_formulas}
                  onFormulaCreate={handleFormulaCreate}
                  onFormulaUpdate={handleFormulaUpdate}
                  onFormulaDelete={handleFormulaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="bodegas">
                <ManageBodegas
                  bodegas={sedeBodegas}
                  sedes={sedes}
                  users={sedeUsers}
                  selectedSedeId={selectedSedeId || undefined}
                  onBodegaCreate={handleBodegaCreate}
                  onBodegaUpdate={handleBodegaUpdate}
                  onBodegaDelete={handleBodegaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="clientes">
                <ManageClientes
                  clientes={selectedSedeId ? _clientes.filter(c => c.sede?.toString() === selectedSedeId) : _clientes}
                  onClienteCreate={handleClienteCreate}
                  onClienteUpdate={handleClienteUpdate}
                  onClienteDelete={handleClienteDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="proveedores">
                <ManageProveedores
                  proveedores={selectedSedeId
                    ? _proveedores.filter(p => !p.sede || p.sede.toString() === selectedSedeId)
                    : _proveedores
                  }
                  onProveedorCreate={handleProveedorCreate}
                  onProveedorUpdate={handleProveedorUpdate}
                  onProveedorDelete={handleProveedorDelete}
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
                      {(Array.isArray(groups) ? groups : []).map(group => (
                        <div key={group.id} className="p-4 rounded-lg bg-accent border flex items-center justify-between">
                          <div>
                            <p className="font-bold text-primary">{group.name.replace('_', ' ').toUpperCase()}</p>
                            <p className="text-xs text-muted-foreground italic">Internal ID: {group.id}</p>
                          </div>
                          <Badge variant="secondary">
                            {sedeUsers.filter(u => Array.isArray(u.groups) && u.groups.includes(group.id)).length} Usuarios
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </TabsContent>

          <TabsContent value="audit" className="space-y-4">
            <ErrorBoundary>
              <AuditLogViewer sedeId={selectedSedeId || undefined} />
            </ErrorBoundary>
          </TabsContent>
        </Tabs>
      </div>

    </div>
  );
}