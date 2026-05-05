import React, { useState, useEffect, useMemo } from 'react';
import { OrdenProduccion, Producto, FormulaColor, Sede, Maquina, Area, Bodega } from '../../lib/types';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { ManageOrdenesProduccion } from './ManageOrdenesProduccion';
import { AxiosError } from 'axios';
import { Card, CardContent } from '../ui/card';
import { Factory, Loader2, Play, CheckCircle2, TrendingUp, AlertTriangle } from 'lucide-react';

interface UsuarioBasico {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  sede: number | null;
}

export function JefePlantaDashboard() {
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [operarios, setOperarios] = useState<UsuarioBasico[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [ordenesRes, productosRes, formulasRes, sedesRes, maquinasRes, areasRes, bodegasRes, usuariosRes] = await Promise.all([
        apiClient.get('/ordenes-produccion/'),
        apiClient.get('/productos/'),
        apiClient.get('/formula-colors/'),
        apiClient.get('/sedes/'),
        apiClient.get('/maquinas/'),
        apiClient.get('/areas/'),
        apiClient.get('/bodegas/'),
        apiClient.get('/users/'),
      ]);
      setOrdenes(Array.isArray(ordenesRes.data) ? ordenesRes.data : (ordenesRes.data as any).results || []);
      setProductos(Array.isArray(productosRes.data) ? productosRes.data : (productosRes.data as any).results || []);
      setFormulas(Array.isArray(formulasRes.data) ? formulasRes.data : (formulasRes.data as any).results || []);
      setSedes(Array.isArray(sedesRes.data) ? sedesRes.data : (sedesRes.data as any).results || []);
      setMaquinas(Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || []);
      setAreas(Array.isArray(areasRes.data) ? areasRes.data : (areasRes.data as any).results || []);
      setBodegas(Array.isArray(bodegasRes.data) ? bodegasRes.data : (bodegasRes.data as any).results || []);
      setOperarios(Array.isArray(usuariosRes.data) ? usuariosRes.data : (usuariosRes.data as any).results || []);
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

  // KPIs derivados del estado de las órdenes
  const kpis = useMemo(() => {
    const pendientes = ordenes.filter(o => o.estado === 'pendiente').length;
    const enProceso = ordenes.filter(o => o.estado === 'en_proceso').length;
    const finalizadas = ordenes.filter(o => o.estado === 'finalizada').length;
    const today = new Date().toISOString().split('T')[0];
    const vencidas = ordenes.filter(o =>
      o.estado !== 'finalizada' && o.fecha_fin_planificada && o.fecha_fin_planificada < today
    ).length;
    const totalRequerido = ordenes.reduce((s, o) => s + Number(o.peso_neto_requerido || 0), 0);
    const totalProducido = ordenes.reduce((s, o) => s + Number(o.peso_producido || 0), 0);
    const eficiencia = totalRequerido > 0 ? Math.round((totalProducido / totalRequerido) * 100) : 0;
    return { pendientes, enProceso, finalizadas, vencidas, eficiencia };
  }, [ordenes]);

  const handleOrdenCreate = async (data: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<OrdenProduccion>('/ordenes-produccion/', data);
      setOrdenes(prev => [response.data, ...prev]);
      toast.success('Orden de producción creada exitosamente');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response?.status === 400) {
        const msgs = Object.entries(axiosError.response.data).map(([k, v]) => `${k}: ${v}`).join(' | ');
        toast.error('Error de validación', { description: msgs });
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
      toast.success('Orden actualizada');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response?.status === 400) {
        const msgs = Object.entries(axiosError.response.data).map(([k, v]) => `${k}: ${v}`).join(' | ');
        toast.error('Error de validación', { description: msgs });
      } else {
        toast.error('Error al actualizar la orden');
      }
      return false;
    }
  };

  const handleOrdenDelete = async (id: number) => {
    if (window.confirm('¿Eliminar esta orden de producción? Esta acción no se puede deshacer.')) {
      try {
        await apiClient.delete(`/ordenes-produccion/${id}/`);
        setOrdenes(prev => prev.filter(o => o.id !== id));
        toast.success('Orden eliminada');
      } catch {
        toast.error('Error al eliminar la orden');
      }
    }
  };

  const handleOrderStatusChange = async (id: number, newStatus: string): Promise<boolean> => {
    try {
      const response = await apiClient.patch<{ status: string; estado: string }>(
        `/ordenes-produccion/${id}/cambiar_estado/`,
        { estado: newStatus }
      );
      setOrdenes(prev =>
        prev.map(o => (o.id === id ? { ...o, estado: response.data.estado as OrdenProduccion['estado'] } : o))
      );
      const labels: Record<string, string> = {
        en_proceso: 'Orden iniciada — en proceso',
        finalizada: 'Orden marcada como finalizada',
      };
      toast.success(labels[newStatus] || 'Estado actualizado');
      return true;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      if (axiosError.response?.status === 400) {
        const msg = axiosError.response.data?.estado?.[0] || JSON.stringify(axiosError.response.data);
        toast.error('No se puede cambiar el estado', { description: msg });
      } else {
        toast.error('Error al cambiar el estado de la orden');
      }
      return false;
    }
  };

  const kpiCards = [
    {
      label: 'Pendientes',
      value: kpis.pendientes,
      icon: <Factory className="w-5 h-5 text-slate-500" />,
      color: 'bg-slate-50 border-slate-200',
      textColor: 'text-slate-700',
    },
    {
      label: 'En Proceso',
      value: kpis.enProceso,
      icon: <Play className="w-5 h-5 text-blue-500" />,
      color: 'bg-blue-50 border-blue-200',
      textColor: 'text-blue-700',
    },
    {
      label: 'Finalizadas',
      value: kpis.finalizadas,
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
      color: 'bg-emerald-50 border-emerald-200',
      textColor: 'text-emerald-700',
    },
    {
      label: 'Eficiencia Global',
      value: `${kpis.eficiencia}%`,
      icon: <TrendingUp className="w-5 h-5 text-purple-500" />,
      color: 'bg-purple-50 border-purple-200',
      textColor: 'text-purple-700',
    },
    ...(kpis.vencidas > 0 ? [{
      label: 'Vencidas',
      value: kpis.vencidas,
      icon: <AlertTriangle className="w-5 h-5 text-red-500" />,
      color: 'bg-red-50 border-red-200',
      textColor: 'text-red-700',
    }] : []),
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Panel de Jefe de Planta</h1>
        <p className="text-muted-foreground">
          Gestión de órdenes de producción, lotes y control de avance.
        </p>
      </div>

      {/* KPIs */}
      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin" /> Cargando datos...
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {kpiCards.map(card => (
            <Card key={card.label} className={`border ${card.color}`}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground font-medium">{card.label}</span>
                  {card.icon}
                </div>
                <div className={`text-3xl font-bold ${card.textColor}`}>{card.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ManageOrdenesProduccion
        ordenes={ordenes}
        productos={productos}
        formulas={formulas}
        sedes={sedes}
        maquinas={maquinas}
        areas={areas}
        onOrdenCreate={handleOrdenCreate}
        onOrdenUpdate={handleOrdenUpdate}
        onOrderStatusChange={handleOrderStatusChange}
        onOrdenDelete={handleOrdenDelete}
        loading={loading}
        onDataRefresh={fetchData}
      />
    </div>
  );
}
