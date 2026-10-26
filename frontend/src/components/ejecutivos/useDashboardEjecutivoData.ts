import { useState, useCallback, useEffect, useLayoutEffect, useRef } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { indicadoresApi } from '../../lib/api/indicadoresApi';
import { inventarioApi } from '../../lib/api/inventarioApi';
import type { VendedorResumen } from '../../types/indicadores';
import type { Cliente, PedidoVenta, Sede } from '../../lib/types';
import { toArray } from './utils';
import type { StockResumen } from '../../types/inventario';
import type { AlertaStock, KpiEjecutivo, ProduccionResumen, TendenciaDia } from './types';

const REFRESH_INTERVAL_MS = 60_000;

interface UseDashboardEjecutivoDataParams {
  isAdminSede: boolean;
  userSedeId?: string;
  setProduccionResumen: (v: ProduccionResumen | null) => void;
  setTendencia: (v: TendenciaDia[]) => void;
  setAlertas: (v: AlertaStock[]) => void;
  setResumenStock: (v: StockResumen | null) => void;
  setClientes: (v: Cliente[]) => void;
  setPedidos: (v: PedidoVenta[]) => void;
}

export function useDashboardEjecutivoData({
  isAdminSede,
  userSedeId,
  setProduccionResumen,
  setTendencia,
  setAlertas,
  setResumenStock,
  setClientes,
  setPedidos,
}: UseDashboardEjecutivoDataParams) {
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [filtroSedeId, setFiltroSedeIdState] = useState<string>(isAdminSede && userSedeId ? userSedeId : 'todas');
  // Filtro de pedidos por vendedor (solo ejecutivo y admin de sistemas pueden listar vendedores).
  const [vendedores, setVendedores] = useState<VendedorResumen[]>([]);
  const [filtroVendedorId, setFiltroVendedorIdState] = useState<string>('todos');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [kpiEjecutivo, setKpiEjecutivo] = useState<KpiEjecutivo | null>(null);

  // Cada pedido de datos es una solicitud numerada; `conToast` distingue la
  // actualización manual (spinner del botón + aviso) de la carga normal.
  const [solicitud, setSolicitud] = useState({ n: 0, conToast: false });
  const [completada, setCompletada] = useState<string | null>(null);
  const claveVigente = `${filtroSedeId}|${filtroVendedorId}|${solicitud.n}`;
  const pendiente = completada !== claveVigente;
  const loading = pendiente && !solicitud.conToast;
  const refreshing = pendiente && solicitud.conToast;

  // Los setters vienen de otros hooks del padre: se leen desde una ref para no
  // volver a pedir si cambia su identidad.
  const settersRef = useRef({ setProduccionResumen, setTendencia, setAlertas, setResumenStock, setClientes, setPedidos });
  useLayoutEffect(() => {
    settersRef.current = { setProduccionResumen, setTendencia, setAlertas, setResumenStock, setClientes, setPedidos };
  });

  useEffect(() => {
    apiClient.get<Sede[]>('/sedes/').then(
      (res) => setSedes(toArray(res.data)),
      () => setSedes([]),
    );
  }, []);

  useEffect(() => {
    indicadoresApi.vendedores().then(setVendedores, () => setVendedores([]));
  }, []);

  useEffect(() => {
    let vigente = true;
    const clave = `${filtroSedeId}|${filtroVendedorId}|${solicitud.n}`;
    const params = (filtroSedeId && filtroSedeId !== 'todas') ? { sede_id: filtroSedeId } : {};
    const paramsPedidos = filtroVendedorId !== 'todos' ? { ...params, vendedor_id: filtroVendedorId } : params;

    // Async para que un error síncrono al armar las peticiones también termine en el `catch`.
    const pedir = async () => Promise.all([
      apiClient.get<KpiEjecutivo>('/kpi-ejecutivo/', { params }).catch(() => ({ data: null as unknown as KpiEjecutivo })),
      apiClient.get<ProduccionResumen>('/produccion/resumen/', { params }).catch(() => ({ data: null as unknown as ProduccionResumen })),
      apiClient.get<TendenciaDia[]>('/produccion/tendencia/', { params }).catch(() => ({ data: [] as TendenciaDia[] })),
      apiClient.get<AlertaStock[]>('/inventory/alertas-stock/', { params }).catch(() => ({ data: [] as AlertaStock[] })),
      inventarioApi.resumenStock(params).catch(() => null),
      apiClient.get<Cliente[]>('/clientes/', { params }).catch(() => ({ data: [] as Cliente[] })),
      apiClient.get<PedidoVenta[]>('/pedidos-venta/', { params: { ...paramsPedidos, limit: 200 } }).catch(() => ({ data: [] as PedidoVenta[] })),
    ]);

    pedir()
      .then(([kpiRes, prodRes, tendRes, alertasRes, resumenStock, clientesRes, pedidosRes]) => {
        if (!vigente) return;
        const setters = settersRef.current;
        setKpiEjecutivo(kpiRes.data);
        setters.setProduccionResumen(prodRes.data);
        setters.setTendencia(toArray(tendRes.data));
        setters.setAlertas(toArray(alertasRes.data));
        setters.setResumenStock(resumenStock);
        setters.setClientes(toArray(clientesRes.data));
        setters.setPedidos(toArray(pedidosRes.data));
        if (solicitud.conToast) toast.success('Datos actualizados');
      })
      .catch((err: unknown) => {
        if (!vigente) return;
        console.error('Error cargando dashboard ejecutivo:', err);
        toast.error('Error al cargar los datos del dashboard');
      })
      .finally(() => {
        if (vigente) setCompletada(clave);
      });
    return () => {
      vigente = false;
    };
  }, [filtroSedeId, filtroVendedorId, solicitud]);

  const fetchData = useCallback((showToast = false) => {
    setSolicitud((s) => ({ n: s.n + 1, conToast: showToast }));
  }, []);

  // Un cambio de filtro es una carga normal, no una actualización manual.
  const setFiltroSedeId = useCallback((v: string) => {
    setSolicitud((s) => (s.conToast ? { ...s, conToast: false } : s));
    setFiltroSedeIdState(v);
  }, []);
  const setFiltroVendedorId = useCallback((v: string) => {
    setSolicitud((s) => (s.conToast ? { ...s, conToast: false } : s));
    setFiltroVendedorIdState(v);
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => fetchData(), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [autoRefresh, fetchData]);

  return {
    sedes,
    filtroSedeId,
    setFiltroSedeId,
    vendedores,
    filtroVendedorId,
    setFiltroVendedorId,
    loading,
    refreshing,
    autoRefresh,
    setAutoRefresh,
    kpiEjecutivo,
    fetchData,
  };
}
