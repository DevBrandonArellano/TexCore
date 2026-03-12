import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { FormulaColor, Quimico } from '../../lib/types';
import { FormulaQuimica } from '../tintura/FormulaQuimica';
import { useSearchParams } from 'react-router-dom';

interface FormulaColorWrite {
  codigo: string;
  nombre_color: string;
  description?: string;
  tipo_sustrato?: string;
  estado: string;
  observaciones?: string;
  fases: any[];
}

export function TintoreroDashboard() {
  const { profile } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [quimicos, setQuimicos] = useState<Quimico[]>([]);
  const [loading, setLoading] = useState(true);

  // Filtros desde URL (Modelo Híbrido)
  const estado = searchParams.get('estado') || '';
  const sustra = searchParams.get('sustrato') || '';

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (estado) params.append('estado', estado);
      if (sustra) params.append('tipo_sustrato', sustra);

      const [formulasRes, quimicosRes] = await Promise.all([
        apiClient.get<FormulaColor[]>(`/formula-colors/?${params.toString()}`),
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
  }, [estado, sustra]);

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

  const handleExportDosificador = async (id: number) => {
    try {
      const response = await apiClient.get(`/formula-colors/${id}/exportar-dosificador/`);
      const fileData = JSON.stringify(response.data, null, 2);
      const blob = new Blob([fileData], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `formula_infotint_${id}.json`;
      link.click();
      window.URL.revokeObjectURL(url);
      toast.success('Archivo exportado para Dosificadora (Infotint).');
    } catch (error) {
      toast.error('Error al exportar datos al dosificador.');
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
        onExportDosificador={handleExportDosificador}
      />
    </div>
  );
}
