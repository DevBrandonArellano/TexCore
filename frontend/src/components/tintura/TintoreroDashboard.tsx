import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import apiClient from '../../lib/axios';
import { datosDeError, mensajeDeLaApi } from '../../lib/apiError';
import { toast } from 'sonner';
import { FormulaColor, ProcesoTintoreria, Quimico } from '../../lib/types';
import { FormulaQuimica, type FormulaFormValues } from '../tintura/FormulaQuimica';
import { StockQuimicosDashboard } from '../tintura/StockQuimicosDashboard';
import { HistorialOrdenesTintoreria } from '../tintura/HistorialOrdenesTintoreria';
import { ManageProcesosTintoreria } from './ManageProcesosTintoreria';
import { DescargasQuimicosTintoreria } from '../tintura/DescargasQuimicosTintoreria';
import { DerivarFormulaDatos } from '../tintura/DialogosFormula';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { toArray } from '../../lib/collections';

interface FormulaColorWrite {
  codigo: string;
  nombre_color: string;
  description?: string;
  tipo_sustrato?: string;
  estado: string;
  observaciones?: string;
  es_laboratorio?: boolean;
  fases: FormulaFormValues['fases'];
}

export function TintoreroDashboard() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [formulas, setFormulas] = useState<FormulaColor[]>([]);
  const [quimicos, setQuimicos] = useState<Quimico[]>([]);
  const [procesos, setProcesos] = useState<ProcesoTintoreria[]>([]);
  const [incluirLaboratorio, setIncluirLaboratorio] = useState(false);

  // Determine active tab from pathname (Fase 3 §8 + catálogo de procesos, 2-oct-2026)
  const pathname = location.pathname;
  const activeTab = pathname.includes('/procesos')
    ? 'procesos'
    : pathname.includes('/stock')
    ? 'stock'
    : pathname.includes('/historial')
    ? 'historial'
    : pathname.includes('/descargas')
    ? 'descargas'
    : 'formulas';

  // Filtros desde URL (Modelo Híbrido)
  const estado = searchParams.get('estado') || '';
  const sustra = searchParams.get('sustrato') || '';

  // `loading` cubre la carga de cada combinación de filtros (derivado de la
  // clave) y las recargas pedidas tras una mutación, que se pueden esperar.
  const claveFiltros = `${estado}|${sustra}|${incluirLaboratorio}`;
  const [cargadoPara, setCargadoPara] = useState<string | null>(null);
  const [recargando, setRecargando] = useState(false);
  const loading = cargadoPara !== claveFiltros || recargando;

  const cargarDatos = useCallback(() => {
    const clave = `${estado}|${sustra}|${incluirLaboratorio}`;
    const params = new URLSearchParams();
    if (estado) params.append('estado', estado);
    if (sustra) params.append('tipo_sustrato', sustra);
    if (incluirLaboratorio) params.append('incluir_laboratorio', 'true');

    return Promise.all([
      apiClient.get<FormulaColor[]>(`/formula-colors/?${params.toString()}`),
      apiClient.get<Quimico[]>('/chemicals/'),
      apiClient.get<ProcesoTintoreria[]>('/procesos-tintoreria/?activo=true'),
    ])
      .then(
        ([formulasRes, quimicosRes, procesosRes]) => {
          setFormulas(toArray(formulasRes.data));
          setQuimicos(toArray(quimicosRes.data));
          setProcesos(toArray(procesosRes.data));
        },
        (error: unknown) => {
          console.error('Error al cargar datos de tintoreria', error);
          toast.error('No se pudieron cargar los datos.');
        },
      )
      .finally(() => setCargadoPara(clave));
  }, [estado, sustra, incluirLaboratorio]);

  useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);

  const fetchData = useCallback(() => {
    setRecargando(true);
    return cargarDatos().finally(() => setRecargando(false));
  }, [cargarDatos]);

  const handleCreate = async (data: FormulaColorWrite): Promise<boolean> => {
    try {
      await apiClient.post('/formula-colors/', data);
      toast.success('Formula creada exitosamente.');
      await fetchData();
      return true;
    } catch (error) {
      const detail = datosDeError(error);
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
    } catch (error) {
      const detail = datosDeError(error);
      toast.error(detail ? JSON.stringify(detail) : 'Error al actualizar la formula.');
      return false;
    }
  };

  // Regla 1 (D7): congela la receta viva como un ensayo nuevo, NO oficial.
  const handleCrearVersion = async (id: number, observaciones: string): Promise<boolean> => {
    try {
      const { data } = await apiClient.post(`/formula-colors/${id}/versiones/`, { observaciones });
      toast.success(`Versión v${data.numero} guardada como ensayo.`);
      await fetchData();
      return true;
    } catch (error) {
      toast.error(mensajeDeLaApi(error, 'Error al guardar la versión.'));
      return false;
    }
  };

  // Reglas 3-5: designa una versión existente como la oficial vigente.
  const handleMarcarOficial = async (id: number, numero: number): Promise<boolean> => {
    try {
      await apiClient.post(`/formula-colors/${id}/versiones/${numero}/marcar-oficial/`, {});
      toast.success(`Versión v${numero} marcada como oficial.`);
      await fetchData();
      return true;
    } catch (error) {
      toast.error(mensajeDeLaApi(error, 'Error al marcar la versión oficial.'));
      return false;
    }
  };

  // Reglas 6-7 (D8-D9): crea una fórmula nueva a partir del snapshot de una versión concreta.
  const handleDerivar = async (
    id: number, datos: DerivarFormulaDatos & { version_origen: number },
  ): Promise<boolean> => {
    try {
      const { data } = await apiClient.post(`/formula-colors/${id}/derivar/`, datos);
      toast.success(`Fórmula derivada creada: ${data.codigo}.`);
      await fetchData();
      return true;
    } catch (error) {
      toast.error(mensajeDeLaApi(error, 'Error al derivar la fórmula.'));
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
    } catch (error) {
      toast.error(mensajeDeLaApi(error, 'Error al crear la variante.'));
      return false;
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('¿Estás seguro de eliminar esta fórmula?')) return;
    try {
      await apiClient.delete(`/formula-colors/${id}/`);
      toast.success('Formula eliminada.');
      await fetchData();
    } catch {
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
    } catch {
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
        onValueChange={(value) => navigate(
          value === 'formulas' ? '/' : `/${value}`
        )}
        className="flex-1 flex flex-col"
      >
        <TabsList className="grid w-full max-w-3xl grid-cols-5">
          <TabsTrigger value="formulas">Fórmulas</TabsTrigger>
          <TabsTrigger value="stock">Stock de Químicos</TabsTrigger>
          <TabsTrigger value="historial">Historial de Órdenes</TabsTrigger>
          <TabsTrigger value="descargas">Descargas de Químicos</TabsTrigger>
          <TabsTrigger value="procesos">Procesos</TabsTrigger>
        </TabsList>

        <TabsContent value="formulas" className="flex-1">
          <FormulaQuimica
            formulas={formulas}
            quimicos={quimicos}
            procesos={procesos}
            loading={loading}
            canDelete={false}
            incluirLaboratorio={incluirLaboratorio}
            onToggleIncluirLaboratorio={() => setIncluirLaboratorio((v) => !v)}
            onFormulaCreate={handleCreate}
            onFormulaUpdate={handleUpdate}
            onFormulaCrearVersion={handleCrearVersion}
            onFormulaMarcarOficial={handleMarcarOficial}
            onFormulaDerivar={handleDerivar}
            onFormulaDuplicate={handleDuplicate}
            onFormulaDelete={handleDelete}
            onExportDosificador={handleExportDosificador}
          />
        </TabsContent>

        <TabsContent value="procesos" className="flex-1">
          <ManageProcesosTintoreria onCatalogoCambiado={fetchData} />
        </TabsContent>

        <TabsContent value="stock" className="flex-1">
          <StockQuimicosDashboard />
        </TabsContent>

        <TabsContent value="historial" className="flex-1">
          <HistorialOrdenesTintoreria />
        </TabsContent>

        <TabsContent value="descargas" className="flex-1">
          <DescargasQuimicosTintoreria />
        </TabsContent>
      </Tabs>
    </div>
  );
}
