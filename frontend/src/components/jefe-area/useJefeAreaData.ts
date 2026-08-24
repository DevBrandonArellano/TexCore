import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { useAuth } from '../../lib/auth';
import type { Maquina, KPIArea, Producto, LoteProduccion, User, OrdenProduccion, LineaProduccion, OeeResultado } from '../../lib/types';

type Profile = ReturnType<typeof useAuth>['profile'];

export function useJefeAreaData(profile: Profile) {
  const [kpis, setKpis] = useState<KPIArea | null>(null);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [alertas, setAlertas] = useState<Producto[]>([]);
  const [lotes, setLotes] = useState<LoteProduccion[]>([]);
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [operarios, setOperarios] = useState<User[]>([]);
  const [lineas, setLineas] = useState<LineaProduccion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [maquinasCarga, setMaquinasCarga] = useState<Record<number, number>>({});
  const [maquinasOee, setMaquinasOee] = useState<Record<number, OeeResultado>>({});

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      const [kpiRes, maquinasRes, ordenesRes, usersRes, productosRes, lotesRes, lineasRes] = await Promise.all([
        apiClient.get<KPIArea>('/kpi-area/'),
        apiClient.get<Maquina[]>('/maquinas/'),
        apiClient.get<OrdenProduccion[]>('/ordenes-produccion/'),
        apiClient.get<User[]>('/users/'),
        apiClient.get<Producto[]>('/productos/'),
        apiClient.get<LoteProduccion[]>('/lotes-produccion/'),
        apiClient.get<LineaProduccion[]>('/lineas-produccion/'),
      ]);

      setKpis(kpiRes.data);
      setMaquinas(Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || []);
      setOrdenes(Array.isArray(ordenesRes.data) ? ordenesRes.data : (ordenesRes.data as any).results || []);
      setOperarios(Array.isArray(usersRes.data) ? usersRes.data : (usersRes.data as any).results || []);
      setLotes(Array.isArray(lotesRes.data) ? lotesRes.data : (lotesRes.data as any).results || []);
      setLineas(Array.isArray(lineasRes.data) ? lineasRes.data : (lineasRes.data as any).results || []);

      // Extraer datos para cálculos
      const maquinasData = Array.isArray(maquinasRes.data) ? maquinasRes.data : (maquinasRes.data as any).results || [];
      const lotesData = Array.isArray(lotesRes.data) ? lotesRes.data : (lotesRes.data as any).results || [];
      const productosData = Array.isArray(productosRes.data) ? productosRes.data : (productosRes.data as any).results || [];

      // Calcular carga real de trabajo por máquina
      const today = new Date().toISOString().split('T')[0];
      const cargas: Record<number, number> = {};

      maquinasData.forEach((m: Maquina) => {
        const produccionHoy = (lotesData as LoteProduccion[])
          .filter((l: LoteProduccion) => l.maquina === m.id && l.hora_final.startsWith(today))
          .reduce((sum: number, l: LoteProduccion) => sum + Number(l.peso_neto_producido), 0);

        const capacidad = Number(m.capacidad_maxima) || 1;
        cargas[m.id] = Math.min(Math.round((produccionHoy / capacidad) * 100), 100);
      });
      setMaquinasCarga(cargas);

      const lowStock = (productosData as Producto[]).filter((p: Producto) =>
        (p.tipo === 'hilo' || p.tipo === 'quimico') &&
        p.stock_minimo > 0
      );
      setAlertas(lowStock.slice(0, 5));

      // OEE por máquina (R4) — un GET por máquina; el área es pequeña por diseño (RBAC).
      const oeeEntries = await Promise.all(
        maquinasData.map(async (m: Maquina) => {
          try {
            const res = await apiClient.get<OeeResultado>(`/maquinas/${m.id}/oee/`);
            return [m.id, res.data] as const;
          } catch {
            return null;
          }
        })
      );
      const oeePorMaquina: Record<number, OeeResultado> = {};
      oeeEntries.forEach((entry) => {
        if (entry) oeePorMaquina[entry[0]] = entry[1];
      });
      setMaquinasOee(oeePorMaquina);

    } catch (error) {
      console.error("Error fetching dashboard data", error);
      toast.error("Error al cargar los datos del panel.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (profile) {
      fetchDashboardData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  return {
    kpis,
    maquinas,
    alertas,
    lotes,
    ordenes,
    operarios,
    lineas,
    isLoading,
    maquinasCarga,
    maquinasOee,
    fetchDashboardData,
  };
}
