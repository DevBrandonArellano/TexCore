import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { toArray } from '../../lib/collections';
import type { useAuth } from '../../lib/auth';
import type {
  Maquina, KPIArea, Producto, User, OrdenProduccion, LineaProduccion, OeeResultado, EficienciaMaquina,
} from '../../lib/types';

type Profile = ReturnType<typeof useAuth>['profile'];

/** GET `/maquinas/{id}/{accion}/` para cada máquina; omite las que fallan. */
async function porMaquina<T>(maquinas: Maquina[], accion: 'oee' | 'eficiencia'): Promise<[number, T][]> {
  const entradas = await Promise.all(
    maquinas.map(async (m) => {
      try {
        const res = await apiClient.get<T>(`/maquinas/${m.id}/${accion}/`);
        return [m.id, res.data] as [number, T];
      } catch {
        return null;
      }
    }),
  );
  return entradas.filter((e): e is [number, T] => e !== null);
}

export function useJefeAreaData(profile: Profile) {
  const [kpis, setKpis] = useState<KPIArea | null>(null);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [alertas, setAlertas] = useState<Producto[]>([]);
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [operarios, setOperarios] = useState<User[]>([]);
  const [lineas, setLineas] = useState<LineaProduccion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [maquinasCarga, setMaquinasCarga] = useState<Record<number, number>>({});
  const [maquinasOee, setMaquinasOee] = useState<Record<number, OeeResultado>>({});

  // La carga vive en el efecto; recargar solo pide una nueva vuelta (desde eventos).
  const [recarga, setRecarga] = useState(0);
  useEffect(() => {
    if (!profile) return;
    let vigente = true;
    const cargar = async () => {
      try {
        const [kpiRes, maquinasRes, ordenesRes, usersRes, productosRes, lineasRes] = await Promise.all([
          apiClient.get<KPIArea>('/kpi-area/'),
          apiClient.get<Maquina[]>('/maquinas/'),
          apiClient.get<OrdenProduccion[]>('/ordenes-produccion/'),
          apiClient.get<User[]>('/users/'),
          apiClient.get<Producto[]>('/productos/'),
          apiClient.get<LineaProduccion[]>('/lineas-produccion/'),
        ]);
        if (!vigente) return;

        const maquinasData = toArray<Maquina>(maquinasRes.data);
        const productosData = toArray<Producto>(productosRes.data);

        setKpis(kpiRes.data);
        setMaquinas(maquinasData);
        setOrdenes(toArray<OrdenProduccion>(ordenesRes.data));
        setOperarios(toArray<User>(usersRes.data));
        setLineas(toArray<LineaProduccion>(lineasRes.data));

        const lowStock = productosData.filter((p: Producto) =>
          (p.tipo === 'hilo' || p.tipo === 'quimico') &&
          p.stock_minimo > 0
        );
        setAlertas(lowStock.slice(0, 5));

        // OEE (R4) y carga del día por máquina: dos GET por máquina, el área es
        // pequeña por diseño (RBAC). La carga la calcula el servidor con la fecha
        // local; antes se sumaban en el navegador los lotes del día UTC.
        const [oeeEntries, eficienciaEntries] = await Promise.all([
          porMaquina<OeeResultado>(maquinasData, 'oee'),
          porMaquina<EficienciaMaquina>(maquinasData, 'eficiencia'),
        ]);
        if (!vigente) return;
        setMaquinasOee(Object.fromEntries(oeeEntries));
        setMaquinasCarga(Object.fromEntries(
          eficienciaEntries.map(([id, e]) => [id, Math.min(Math.round(Number(e.eficiencia_porcentaje)), 100)]),
        ));
      } catch (error) {
        if (!vigente) return;
        console.error("Error fetching dashboard data", error);
        toast.error("Error al cargar los datos del panel.");
      } finally {
        if (vigente) setIsLoading(false);
      }
    };
    cargar();
    return () => {
      vigente = false;
    };
  }, [profile, recarga]);

  const fetchDashboardData = useCallback(() => {
    setIsLoading(true);
    setRecarga((n) => n + 1);
  }, []);

  return {
    kpis,
    maquinas,
    alertas,
    ordenes,
    operarios,
    lineas,
    isLoading,
    maquinasCarga,
    maquinasOee,
    fetchDashboardData,
  };
}
