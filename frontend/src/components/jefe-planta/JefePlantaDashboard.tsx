import React, { useState, useEffect } from 'react';
import { OrdenProduccion, Producto, FormulaColor, Sede, Maquina, Area } from '../../lib/types';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { ManageOrdenesProduccion } from './ManageOrdenesProduccion';
import { AxiosError } from 'axios';

export function JefePlantaDashboard() {
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [ordenesRes, productosRes, formulasRes, sedesRes, maquinasRes, areasRes] = await Promise.all([
        apiClient.get('/ordenes-produccion/'),
        apiClient.get('/productos/'),
        apiClient.get('/formula-colors/'),
        apiClient.get('/sedes/'),
        apiClient.get('/maquinas/'),
        apiClient.get('/areas/'),
      ]);
      setOrdenes(ordenesRes.data);
      setProductos(productosRes.data);
      setFormulas(formulasRes.data);
      setSedes(sedesRes.data);
      setMaquinas(maquinasRes.data);
      setAreas(areasRes.data);
    } catch (error) {
      console.error('Error fetching data for dashboard:', error);
      toast.error('Error al cargar los datos del panel.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOrdenCreate = async (data: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<OrdenProduccion>('/ordenes-produccion/', data);
      setOrdenes(prev => [...prev, response.data]);
      toast.success('Orden de producción creada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', { description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre> });
      } else {
        toast.error('Error al crear la orden de producción');
      }
      return false;
    }
  };

  const handleOrdenUpdate = async (id: number, data: any): Promise<boolean> => {
    try {
      const response = await apiClient.patch<OrdenProduccion>(`/ordenes-produccion/${id}/`, data);
      setOrdenes(prev => prev.map(o => (o.id === id ? response.data : o)));
      toast.success('Orden de producción actualizada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response && axiosError.response.status === 400) {
        toast.error('Error de validación', { description: <pre>{JSON.stringify(axiosError.response.data, null, 2)}</pre> });
      } else {
        toast.error('Error al actualizar la orden de producción');
      }
      return false;
    }
  };

  const handleOrdenDelete = async (id: number) => {
    if (window.confirm('¿Estás seguro de eliminar esta orden de producción?')) {
      try {
        await apiClient.delete(`/ordenes-produccion/${id}/`);
        setOrdenes(prev => prev.filter(o => o.id !== id));
        toast.success('Orden de producción eliminada exitosamente');
      } catch (error) {
        toast.error('Error al eliminar la orden de producción');
      }
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Panel de Jefe de Planta</h1>
        <p className="text-muted-foreground">
          Administra las órdenes de producción y supervisa el progreso.
        </p>
      </div>
      <ManageOrdenesProduccion
        ordenes={ordenes}
        productos={productos}
        formulas={formulas}
        sedes={sedes}
        maquinas={maquinas}
        areas={areas}
        onOrdenCreate={handleOrdenCreate}
        onOrdenUpdate={handleOrdenUpdate}
        onOrdenDelete={handleOrdenDelete}
        loading={loading}
        onDataRefresh={fetchData}
      />
    </div>
  );
}