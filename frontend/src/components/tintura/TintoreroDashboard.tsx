import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { FormulaColor, ProcesoTintoreria, Quimico } from '../../lib/types';
import { FormulaQuimica } from '../tintura/FormulaQuimica';
import { StockQuimicosDashboard } from '../tintura/StockQuimicosDashboard';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

interface FormulaColorWrite {
  codigo: string;
  nombre_color: string;
  description?: string;
  tipo_sustrato?: string;
  estado: string;
  observaciones?: string;
  motivo?: string;
  fases: any[];
}

// Mensaje legible del formato de error estándar del backend ({success, error: {message}})
const mensajeError = (error: any, porDefecto: string) =>
  error?.response?.data?.error?.message || porDefecto;

export function TintoreroDashboard() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [quimicos, setQuimicos] = useState<Quimico[]>([]);
  const [procesos, setProcesos] = useState<ProcesoTintoreria[]>([]);
  const [loading, setLoading] = useState(true);

  // Determine active tab from pathname
  const pathname = location.pathname;
  const activeTab = pathname.includes('/stock') ? 'stock' : 'formulas';

  // Filtros desde URL (Modelo Híbrido)
  const estado = searchParams.get('estado') || '';
  const sustra = searchParams.get('sustrato') || '';

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (estado) params.append('estado', estado);
      if (sustra) params.append('tipo_sustrato', sustra);

      const [formulasRes, quimicosRes, procesosRes] = await Promise.all([
        apiClient.get<FormulaColor[]>(`/formula-colors/?${params.toString()}`),
        apiClient.get<Quimico[]>('/chemicals/'),
        apiClient.get<ProcesoTintoreria[]>('/procesos-tintoreria/?activo=true'),
      ]);
      const lista = (data: any) => (Array.isArray(data) ? data : data?.results || []);
      setFormulas(lista(formulasRes.data));
      setQuimicos(lista(quimicosRes.data));
      setProcesos(lista(procesosRes.data));
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

  const handleApprove = async (id: number, motivo: string): Promise<boolean> => {
    try {
      const { data } = await apiClient.post(`/formula-colors/${id}/aprobar/`, { motivo });
      toast.success(`Formula aprobada: version oficial v${data.numero}.`);
      await fetchData();
      return true;
    } catch (error: any) {
      toast.error(mensajeError(error, 'Error al aprobar la formula.'));
      return false;
    }
  };

  // «Duplicar» crea una variante nueva, en pruebas, con su propio código y color
  const handleDuplicate = async (id: number, datos: { codigo: string; nombre_color: string }): Promise<boolean> => {
    try {
      await apiClient.post(`/formula-colors/${id}/duplicar/`, datos);
      toast.success('Variante creada en pruebas.');
      await fetchData();
      return true;
    } catch (error: any) {
      toast.error(mensajeError(error, 'Error al crear la variante.'));
      return false;
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('¿Estás seguro de eliminar esta fórmula?')) return;
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
        <h1 className="text-3xl font-bold tracking-tight">Panel de Tintorería</h1>
        <p className="text-muted-foreground">
          Bienvenido, {profile?.user.username}. Gestiona formulas químicas y monitorea el stock.
        </p>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(value) => navigate(value === 'stock' ? '/stock' : '/')}
        className="flex-1 flex flex-col"
      >
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="formulas">Fórmulas Químicas</TabsTrigger>
          <TabsTrigger value="stock">Stock Disponible</TabsTrigger>
        </TabsList>

        <TabsContent value="formulas" className="flex-1">
          <FormulaQuimica
            formulas={formulas}
            quimicos={quimicos}
            procesos={procesos}
            loading={loading}
            canDelete={false}
            onFormulaCreate={handleCreate}
            onFormulaUpdate={handleUpdate}
            onFormulaApprove={handleApprove}
            onFormulaDuplicate={handleDuplicate}
            onFormulaDelete={handleDelete}
            onExportDosificador={handleExportDosificador}
          />
        </TabsContent>

        <TabsContent value="stock" className="flex-1">
          <StockQuimicosDashboard />
        </TabsContent>
      </Tabs>
    </div>
  );
}
