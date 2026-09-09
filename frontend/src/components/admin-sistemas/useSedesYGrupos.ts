import { useState, useEffect } from 'react';
import type { SetURLSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { Sede, Area } from '../../lib/types';
import { type Group, showApiError } from './sedeUtils';

interface UseSedesYGruposParams {
  selectedSedeId: string;
  setSearchParams: SetURLSearchParams;
  setAreas: React.Dispatch<React.SetStateAction<Area[]>>;
}

export function useSedesYGrupos({ selectedSedeId, setSearchParams, setAreas }: UseSedesYGruposParams) {
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  /** Sedes/grupos globales ya intentaron cargar (para pestaña Gestión → Sedes) */
  const [sedesFetchDone, setSedesFetchDone] = useState(false);

  const fetchGlobalData = async () => {
    try {
      const [sedesRes, groupsRes] = await Promise.all([
        apiClient.get<Sede[]>('/sedes/'),
        apiClient.get<Group[]>('/groups/')
      ]);

      const sData = Array.isArray(sedesRes.data) ? sedesRes.data : (sedesRes.data as any).results || [];
      const gData = Array.isArray(groupsRes.data) ? groupsRes.data : (groupsRes.data as any).results || [];

      setSedes(sData);
      setGroups(gData);

      if (sData.length > 0 && !selectedSedeId) {
        setSearchParams(prev => {
          prev.set('sede', sData[0].id.toString());
          return prev;
        }, { replace: true });
      }
    } catch (error) {
      console.error('Error fetching global data:', error);
    } finally {
      setSedesFetchDone(true);
    }
  };

  useEffect(() => {
    fetchGlobalData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  return {
    sedes,
    groups,
    sedesFetchDone,
    handleSedeCreate,
    handleSedeUpdate,
    handleSedeDelete,
    handleAreaCreate,
    handleAreaUpdate,
    handleAreaDelete,
  };
}
