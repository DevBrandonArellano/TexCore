import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { FormulaColor, Quimico } from '../../lib/types';
import { FormulaQuimica } from '../tintura/FormulaQuimica';

interface FormulaColorWrite {
  codigo: string;
  nombre_color: string;
  description?: string;
  tipo_sustrato?: string;
  estado: string;
  observaciones?: string;
  detalles: any[];
}

export function TintoreroDashboard() {
  const { profile } = useAuth();
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [quimicos, setQuimicos] = useState<Quimico[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [formulasRes, quimicosRes] = await Promise.all([
        apiClient.get<FormulaColor[]>('/formula-colors/'),
        apiClient.get<Quimico[]>('/chemicals/'),
      ]);
      setFormulas(formulasRes.data);
      setQuimicos(quimicosRes.data);
    } catch (error) {
      console.error('Error al cargar datos de tintoreria', error);
      toast.error('No se pudieron cargar los datos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async (data: FormulaColorWrite): Promise<boolean> => {
    try {
      await apiClient.post('/formula-colors/', data);
      toast.success('Formula creada exitosamente.');
      await fetchData();
      return true;
    } catch (error: any) {
      const detail = error.response?.data;
      toast.error(detail ? JSON.stringify(detail) : 'Error al crear la formula.');
      return false;
    }
  };

  const handleUpdate = async (id: number, data: FormulaColorWrite): Promise<boolean> => {
    try {
      await apiClient.put(`/formula-colors/${id}/`, data);
      toast.success('Formula actualizada exitosamente.');
      await fetchData();
      return true;
    } catch (error: any) {
      const detail = error.response?.data;
      toast.error(detail ? JSON.stringify(detail) : 'Error al actualizar la formula.');
      return false;
    }
  };

  const handleDuplicate = async (id: number): Promise<boolean> => {
    try {
      await apiClient.post(`/formula-colors/${id}/duplicar/`);
      await fetchData();
      return true;
    } catch (error: any) {
      toast.error('Error al duplicar la formula.');
      return false;
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.delete(`/formula-colors/${id}/`);
      toast.success('Formula eliminada.');
      await fetchData();
    } catch (error) {
      toast.error('Error al eliminar la formula.');
    }
  };

  return (
    <div className="flex flex-col h-full space-y-6 p-4">
      <div className="flex-shrink-0">
        <h1 className="text-3xl font-bold tracking-tight">Panel de Tintoreria</h1>
        <p className="text-muted-foreground">
          Bienvenido, {profile?.user.username}. Gestiona las formulas quimicas de tintoreria y acabados.
        </p>
      </div>

      <FormulaQuimica
        formulas={formulas}
        quimicos={quimicos}
        loading={loading}
        canDelete={false}
        onFormulaCreate={handleCreate}
        onFormulaUpdate={handleUpdate}
        onFormulaDuplicate={handleDuplicate}
        onFormulaDelete={handleDelete}
      />
    </div>
  );
}
