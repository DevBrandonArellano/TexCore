import React, { useState, useEffect, useMemo } from 'react';
import { OrdenProduccion, Producto, FormulaColor, Sede, Maquina, Area, Bodega } from '../../lib/types';
import apiClient from '../../lib/axios';
import { createLogger } from '../../lib/logger';
import { getApiErrorMessage } from '../../lib/apiError';
import { toast } from 'sonner';
import { useSearchParams } from 'react-router-dom';
import { ManageOrdenesProduccion } from './ManageOrdenesProduccion';
import { TransferenciasInterarea } from '../produccion/TransferenciasInterarea';
import { BuscadorLotes } from '../empaquetado/BuscadorLotes';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Button } from '../ui/button';

import { AxiosError } from 'axios';
import { Card, CardContent } from '../ui/card';
import { Factory, FileDown, Loader2, Play, CheckCircle2, TrendingUp, AlertTriangle } from 'lucide-react';

interface UsuarioBasico {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  sede: number | null;
}

// UX-1: semáforo de severidad para la eficiencia global (producido/requerido) —
// 90%+ en línea con el plan, 70-89% requiere atención, <70% crítico.
function claseSeveridadEficiencia(pct: number): string {
  if (pct >= 90) return 'text-emerald-700';
  if (pct >= 70) return 'text-amber-700';
  return 'text-red-700';
}

// RFC 5424 — logger del módulo (relay a /api/logs/ para WARNING+).
const logger = createLogger('JefePlantaDashboard');

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
  const [isExportingAvance, setIsExportingAvance] = useState(false);
  const [isExportingBalance, setIsExportingBalance] = useState(false);
  const [searchParams] = useSearchParams();
  const [pulsoDiario, setPulsoDiario] = useState({
    kg_planificados_hoy: 0,
    kg_producidos_hoy: 0,
    kg_merma_hoy: 0,
    wip_estancado: 0,
  });
  
  const [ordenesCount, setOrdenesCount] = useState(0);

  const fetchData = async () => {
    try {
      setLoading(true);
      const params = Object.fromEntries(searchParams.entries());
      const queryStr = new URLSearchParams(params).toString();
      const [ordenesRes, productosRes, formulasRes, sedesRes, maquinasRes, areasRes, bodegasRes, usuariosRes, pulsoRes] = await Promise.all([
        apiClient.get(`/ordenes-produccion/?${queryStr}`),
        apiClient.get('/productos/'),
        apiClient.get('/formula-colors/'),
        apiClient.get('/sedes/'),
        apiClient.get('/maquinas/'),
        apiClient.get('/areas/'),
        apiClient.get('/bodegas/'),
        apiClient.get('/users/'),
        apiClient.get('/produccion/pulso-diario/'),
      ]);
      setOrdenes(Array.isArray(ordenesRes.data) ? ordenesRes.data : (ordenesRes.data as any).results || []);
      setOrdenesCount((ordenesRes.data as any).count || 0);
      setProductos(Array.isArray(productosRes.data) ? productosRes.data : (productosRes.data as any).results || []);
      setFormulas(Array.isArray(formulasRes.data) ? formulasRes.data : (formulasRes.data as any).results || []);
      setSedes(Array.isArray(sedesRes.data) ? sedesRes.data : (sedesRes.data as any).results || []);
      setMaquinas(Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || []);
      setAreas(Array.isArray(areasRes.data) ? areasRes.data : (areasRes.data as any).results || []);
      setBodegas(Array.isArray(bodegasRes.data) ? bodegasRes.data : (bodegasRes.data as any).results || []);
      setOperarios(Array.isArray(usuariosRes.data) ? usuariosRes.data : (usuariosRes.data as any).results || []);
      setPulsoDiario(pulsoRes.data);
    } catch (error) {
      logger.error('Fallo al cargar el panel de Jefe de Planta', {
        operacion: 'fetchData',
      });
      toast.error(getApiErrorMessage(error, 'Error al cargar los datos del panel.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [searchParams]);

  // ── Exportación PDF — Reporte de Avance Operativo ────────────────────────
  /**
   * Llama al endpoint Django que proxia al printing_service.
   * Patrón: POST → blob → createObjectURL → click() → revokeObjectURL.
   * responseType:'blob' es obligatorio para que axios no intente parsear el PDF
   * como JSON y corrompa los bytes.
   */
  const exportarAvancePdf = async () => {
    setIsExportingAvance(true);
    try {
      const response = await apiClient.post(
        '/internal/v1/reports/produccion/reporte-avance/',
        { empresa_nombre: 'TexCore Industrial' },
        { responseType: 'blob' },
      );
      const blobUrl = window.URL.createObjectURL(
        new Blob([response.data], { type: 'application/pdf' }),
      );
      const anchor = document.createElement('a');
      anchor.href     = blobUrl;
      anchor.download = `reporte_avance_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(blobUrl);
      toast.success('Reporte de Avance exportado correctamente');
    } catch (error) {
      logger.error('Fallo al exportar PDF de Avance Operativo', { operacion: 'exportarAvancePdf' });
      toast.error(getApiErrorMessage(error, 'Error al generar el PDF de Avance Operativo'));
    } finally {
      setIsExportingAvance(false);
    }
  };

  // ── Exportación PDF — Balance de Masas Mensual ───────────────────────────
  // La sede NO se envía desde el cliente: el backend la deriva del usuario
  // autenticado e impone el aislamiento (evita generar reportes de otra sede
  // manipulando el orden de las órdenes visibles).
  const exportarBalancePdf = async () => {
    setIsExportingBalance(true);
    try {
      const mesLabel = new Date().toLocaleString('es-EC', { month: 'long', year: 'numeric' });
      const response = await apiClient.post(
        '/internal/v1/reports/produccion/reporte-balance/',
        {
          mes_label:      mesLabel,
          empresa_nombre: 'TexCore Industrial',
        },
        { responseType: 'blob' },
      );
      const blobUrl = window.URL.createObjectURL(
        new Blob([response.data], { type: 'application/pdf' }),
      );
      const anchor = document.createElement('a');
      anchor.href     = blobUrl;
      anchor.download = `balance_masas_${new Date().toISOString().slice(0, 7)}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(blobUrl);
      toast.success('Balance de Masas exportado correctamente');
    } catch (error) {
      logger.error('Fallo al exportar PDF de Balance de Masas', { operacion: 'exportarBalancePdf' });
      toast.error(getApiErrorMessage(error, 'Error al generar el PDF de Balance de Masas'));
    } finally {
      setIsExportingBalance(false);
    }
  };

  // KPIs Torre de Control Industrial
  const cumplimientoDiario = pulsoDiario.kg_planificados_hoy > 0 
    ? Math.round((pulsoDiario.kg_producidos_hoy / pulsoDiario.kg_planificados_hoy) * 100) 
    : 0;
  const indiceDesperdicio = pulsoDiario.kg_producidos_hoy > 0
    ? ((pulsoDiario.kg_merma_hoy / pulsoDiario.kg_producidos_hoy) * 100).toFixed(2)
    : "0.00";

  const handleOrdenCreate = async (data: any): Promise<boolean> => {
    try {
      const response = await apiClient.post<OrdenProduccion>('/ordenes-produccion/', data);
      setOrdenes(prev => [response.data, ...prev]);
      toast.success('Orden de producción creada exitosamente');
      return true;
    } catch (error) {
      logger.warning('Fallo al crear orden de producción', { operacion: 'handleOrdenCreate' });
      toast.error(getApiErrorMessage(error, 'Error al crear la orden de producción'));
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
      logger.warning('Fallo al actualizar orden de producción', {
        operacion: 'handleOrdenUpdate', orden_id: id,
      });
      toast.error(getApiErrorMessage(error, 'Error al actualizar la orden'));
      return false;
    }
  };

  const handleOrdenDelete = async (id: number) => {
    if (window.confirm('¿Eliminar esta orden de producción? Esta acción no se puede deshacer.')) {
      try {
        await apiClient.delete(`/ordenes-produccion/${id}/`);
        setOrdenes(prev => prev.filter(o => o.id !== id));
        toast.success('Orden eliminada');
      } catch (error) {
        logger.warning('Fallo al eliminar orden de producción', {
          operacion: 'handleOrdenDelete', orden_id: id,
        });
        toast.error(getApiErrorMessage(error, 'Error al eliminar la orden'));
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
      logger.warning('Fallo al cambiar estado de orden', {
        operacion: 'handleOrderStatusChange', orden_id: id, estado_destino: newStatus,
      });
      const axiosError = error as AxiosError<any>;
      if (axiosError.response?.status === 400) {
        const msg = axiosError.response.data?.estado?.[0] || getApiErrorMessage(error);
        toast.error('No se puede cambiar el estado', { description: msg });
      } else {
        toast.error(getApiErrorMessage(error, 'Error al cambiar el estado de la orden'));
      }
      return false;
    }
  };

  const controlTowerCards = [
    {
      label: 'Cumplimiento Diario',
      value: `${cumplimientoDiario}%`,
      icon: <TrendingUp className="w-6 h-6 text-emerald-500" />,
      color: 'bg-emerald-50 border-emerald-200',
      textColor: claseSeveridadEficiencia(cumplimientoDiario),
    },
    {
      label: 'Índice de Desperdicio',
      value: `${indiceDesperdicio}%`,
      icon: <Factory className="w-6 h-6 text-amber-500" />,
      color: 'bg-amber-50 border-amber-200',
      textColor: 'text-amber-700',
    },
    {
      label: 'Alerta WIP Estancado',
      value: `${pulsoDiario.wip_estancado} Kg`,
      icon: <AlertTriangle className={`w-6 h-6 ${pulsoDiario.wip_estancado > 0 ? 'text-red-500 animate-pulse' : 'text-slate-400'}`} />,
      color: pulsoDiario.wip_estancado > 0 ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200',
      textColor: pulsoDiario.wip_estancado > 0 ? 'text-red-700 font-black' : 'text-slate-600',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Título + botones de exportación */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Panel de Jefe de Planta</h1>
          <p className="text-muted-foreground">
            Gestión de órdenes de producción, lotes y control de avance.
          </p>
        </div>

        {/* ── Botones de exportación PDF ───────────────────────── */}
        <div className="flex gap-2 flex-shrink-0 items-center">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2 border-indigo-200 text-indigo-700 hover:bg-indigo-50">
                <FileDown className="w-4 h-4" />
                Acciones Gerenciales
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={exportarAvancePdf} disabled={isExportingAvance} className="gap-2 cursor-pointer">
                {isExportingAvance ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4 text-teal-600" />}
                <span>Reporte Avance Operativo</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={exportarBalancePdf} disabled={isExportingBalance} className="gap-2 cursor-pointer">
                {isExportingBalance ? <Loader2 className="w-4 h-4 animate-spin" /> : <Factory className="w-4 h-4 text-violet-600" />}
                <span>Balance de Masas Mensual</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* KPIs */}
      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin" /> Cargando datos...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {controlTowerCards.map(card => (
            <Card key={card.label} className={`border ${card.color} shadow-sm transition-all hover:shadow-md`}>
              <CardContent className="pt-6 pb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-600 uppercase tracking-wider">{card.label}</span>
                  {card.icon}
                </div>
                <div className={`text-4xl font-extrabold tracking-tight ${card.textColor}`}>{card.value}</div>
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
        bodegas={bodegas}
        onOrdenCreate={handleOrdenCreate}
        onOrdenUpdate={handleOrdenUpdate}
        onOrderStatusChange={handleOrderStatusChange}
        onOrdenDelete={handleOrdenDelete}
        loading={loading}
        onDataRefresh={fetchData}
      />

      <TransferenciasInterarea />

      <BuscadorLotes />
    </div>
  );
}

