import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { toArray } from '../../lib/collections';
import type {
  User, Area, Producto, Quimico, Bodega,
  OrdenProduccion, LoteProduccion, FormulaColor, Cliente, PedidoVenta, Proveedor
} from '../../lib/types';
import { showApiError } from './sedeUtils';

const getData = <T,>(res: { data?: unknown } | undefined): T[] => toArray<T>(res?.data);

// `areas` vive en el componente padre (no aquí) porque también lo mutan los
// handlers de useSedesYGrupos (handleAreaCreate/Update/Delete) — se recibe
// `setAreas` para evitar una dependencia circular entre ambos hooks.
export function useSedeSpecificData(selectedSedeId: string, sedesLength: number, setAreas: React.Dispatch<React.SetStateAction<Area[]>>) {
  const [users, setUsers] = useState<User[]>([]);
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

  const fetchSedeSpecificData = async () => {
    if (!selectedSedeId) return;
    setLoading(true);

    // Solo cargamos lo necesario para la pestaña activa si es posible,
    // pero para mantener la consistencia del dashboard cargaremos el bloque sede_id.
    const params = { params: { sede_id: selectedSedeId } };

    try {
      // Cargamos en paralelo pero en grupos mas pequenos o solo lo necesario
      const [
        usersRes, areasRes, productosRes, quimicosRes, bodegasRes,
        ordenesRes, lotesRes, formulasRes, pedidosRes,
        clientesRes, provRes
      ] = await Promise.all([
        apiClient.get<User[]>('/users/', params),
        apiClient.get<Area[]>('/areas/', params),
        apiClient.get<Producto[]>('/productos/', params),
        apiClient.get<Quimico[]>('/chemicals/', params),
        apiClient.get<Bodega[]>('/bodegas/', params),
        apiClient.get<OrdenProduccion[]>('/ordenes-produccion/', params),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/', params),
        apiClient.get<FormulaColor[]>('/formula-colors/', params),
        apiClient.get<PedidoVenta[]>('/pedidos-venta/', params),
        apiClient.get<Cliente[]>('/clientes/', params),
        apiClient.get<Proveedor[]>('/proveedores/', params),
      ]);

      setUsers(getData(usersRes));
      setAreas(getData(areasRes));
      setProductos(getData(productosRes));
      setQuimicos(getData(quimicosRes));
      setBodegas(getData(bodegasRes));
      setOrdenesProduccion(getData(ordenesRes));
      setLotesProduccion(getData(lotesRes));
      setFormulasColor(getData(formulasRes));
      setPedidosVenta(getData(pedidosRes));
      setClientes(getData(clientesRes));
      setProveedores(getData(provRes));

    } catch (error) {
      console.error('Error fetching sede specific data:', error);
      toast.error('Error al cargar datos de la sede');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedSedeId) {
      fetchSedeSpecificData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSedeId]);

  const handleUserCreate = async (userData: any): Promise<boolean> => {
    try {
      if (!selectedSedeId && sedesLength > 0) {
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
      if (!selectedSedeId && sedesLength > 0) {
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
      if (!selectedSedeId && sedesLength > 0) {
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
      if (!selectedSedeId && sedesLength > 0) {
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
      if (!selectedSedeId && sedesLength > 0) {
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
      if (!selectedSedeId && sedesLength > 0) {
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

  return {
    users, productos, quimicos, bodegas,
    ordenesProduccion, lotesProduccion, formulasColor, pedidosVenta, clientes, proveedores,
    loading,
    fetchSedeSpecificData,
    handleUserCreate, handleUserUpdate, handleUserDelete,
    handleClienteCreate, handleClienteUpdate, handleClienteDelete,
    handleBodegaCreate, handleBodegaUpdate, handleBodegaDelete,
    handleFormulaCreate, handleFormulaUpdate, handleFormulaDelete,
    handleChemicalCreate, handleChemicalUpdate, handleChemicalDelete,
    handleProductCreate, handleProductUpdate, handleProductDelete,
    handleProveedorCreate, handleProveedorUpdate, handleProveedorDelete,
  };
}
