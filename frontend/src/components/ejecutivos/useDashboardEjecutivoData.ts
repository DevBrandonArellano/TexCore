import { useState, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { Cliente, PedidoVenta, Sede } from '../../lib/types';
import { toArray } from './utils';
import type { StockItem } from './DrillDownModals';
import type { AlertaStock, KpiEjecutivo, ProduccionResumen, TendenciaDia } from './types';

const REFRESH_INTERVAL_MS = 60_000;

interface UseDashboardEjecutivoDataParams {
  isAdminSede: boolean;
  userSedeId?: string;
  setProduccionResumen: (v: ProduccionResumen | null) => void;
  setTendencia: (v: TendenciaDia[]) => void;
  setAlertas: (v: AlertaStock[]) => void;
  setStock: (v: StockItem[]) => void;
  setClientes: (v: Cliente[]) => void;
  setPedidos: (v: PedidoVenta[]) => void;
}

export function useDashboardEjecutivoData({
  isAdminSede,
  userSedeId,
  setProduccionResumen,
  setTendencia,
  setAlertas,
  setStock,
  setClientes,
  setPedidos,
}: UseDashboardEjecutivoDataParams) {
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [filtroSedeId, setFiltroSedeId] = useState<string>(isAdminSede && userSedeId ? userSedeId : 'todas');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [kpiEjecutivo, setKpiEjecutivo] = useState<KpiEjecutivo | null>(null);

  const fetchSedes = useCallback(async () => {
    try {
      const res = await apiClient.get<Sede[]>('/sedes/');
      setSedes(toArray(res.data));
    } catch {
      setSedes([]);
    }
  }, []);

  const fetchData = useCallback(async (showToast = false) => {
    if (showToast) setRefreshing(true);
    else setLoading(true);

    const params = (filtroSedeId && filtroSedeId !== 'todas') ? { sede_id: filtroSedeId } : {};

    try {
      const [
        kpiRes,
        prodRes,
        tendRes,
        alertasRes,
        stockRes,
        clientesRes,
        pedidosRes,
      ] = await Promise.all([
        apiClient.get<KpiEjecutivo>('/kpi-ejecutivo/', { params }).catch(() => ({ data: null as unknown as KpiEjecutivo })),
        apiClient.get<ProduccionResumen>('/produccion/resumen/', { params }).catch(() => ({ data: null as unknown as ProduccionResumen })),
        apiClient.get<TendenciaDia[]>('/produccion/tendencia/', { params }).catch(() => ({ data: [] as TendenciaDia[] })),
        apiClient.get<AlertaStock[]>('/inventory/alertas-stock/', { params }).catch(() => ({ data: [] as AlertaStock[] })),
        apiClient.get<StockItem[]>('/inventory/stock/', { params }).catch(() => ({ data: [] as StockItem[] })),
        apiClient.get<Cliente[]>('/clientes/', { params }).catch(() => ({ data: [] as Cliente[] })),
        apiClient.get<PedidoVenta[]>('/pedidos-venta/', { params: { ...params, limit: 200 } }).catch(() => ({ data: [] as PedidoVenta[] })),
      ]);

      setKpiEjecutivo(kpiRes.data);
      setProduccionResumen(prodRes.data);
      setTendencia(toArray(tendRes.data));
      setAlertas(toArray(alertasRes.data));
      setStock(toArray(stockRes.data));
      setClientes(toArray(clientesRes.data));
      setPedidos(toArray(pedidosRes.data));

      if (showToast) toast.success('Datos actualizados');
    } catch (err) {
      console.error('Error cargando dashboard ejecutivo:', err);
      toast.error('Error al cargar los datos del dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filtroSedeId, setProduccionResumen, setTendencia, setAlertas, setStock, setClientes, setPedidos]);

  useEffect(() => { fetchSedes(); }, [fetchSedes]);
  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => fetchData(), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [autoRefresh, fetchData]);

  return {
    sedes,
    filtroSedeId,
    setFiltroSedeId,
    loading,
    refreshing,
    autoRefresh,
    setAutoRefresh,
    kpiEjecutivo,
    fetchData,
  };
}
