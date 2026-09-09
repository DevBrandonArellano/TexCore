/**
 * RUP — Componente: EjecutivosDashboard
 * ======================================
 * Artefacto   : Diseño de Interfaz de Usuario / Vista
 * Patrón      : Container/Presentational — este componente es el contenedor
 *               de estado; los tabs son unidades de presentación independientes.
 * Principios  : SRP — cada tab tiene responsabilidad única de presentación.
 *               OCP — nuevos tabs se agregan sin modificar los existentes.
 *
 * Casos de Uso cubiertos:
 *   CU-EJ-01 Ver Resumen Ejecutivo (KPIs consolidados)
 *   CU-EJ-02 Ver Resumen de Producción (estado OPs, tendencia kg)
 *   CU-EJ-03 Ver Tendencia de Producción (serie temporal 30d)
 *   CU-EJ-04 Ver Planificación MRP (sugerencias y requerimientos)
 *   CU-EJ-05 Ver Inventario y Alertas de Stock
 *   CU-EJ-06 Ver Ventas, Cobranza y Exportar Reportes
 *   CU-EJ-08 Ver Producción por Producto (drill-down, tabla + impresión PDF)
 *   CU-EJ-09 Ver Historial de Producción de un Producto (drill-down de un item)
 */
import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import {
  Warehouse,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  TrendingUp,
  Activity,
  Factory,
  ShoppingCart,
  CheckCircle2,
  AlertCircle,
  Layers,
  ClipboardList,
  History,
  FileSpreadsheet,
} from 'lucide-react';
import { useAuth } from '../../lib/auth';
import { MRPDashboard } from '../shared/MRPDashboard';
import { MovementApproval } from '../shared/MovementApproval';
import { AuditLogViewer } from '../shared/AuditLogViewer';
import { KpiCard } from './KpiCard';
import { useDashboardEjecutivoData } from './useDashboardEjecutivoData';
import { useProduccionEjecutivo } from './useProduccionEjecutivo';
import { useProduccionPorProducto } from './useProduccionPorProducto';
import { useStockEjecutivo } from './useStockEjecutivo';
import { useVentasEjecutivo } from './useVentasEjecutivo';
import { useExportesGerenciales } from './useExportesGerenciales';
import { ResumenTab } from './ResumenTab';
import { ProduccionTab } from './ProduccionTab';
import { StockTab } from './StockTab';
import { VentasTab } from './VentasTab';
import { ReportesTab } from './ReportesTab';

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

interface EjecutivosDashboardProps {
  isAdminSede?: boolean;
}

export function EjecutivosDashboard({ isAdminSede = false }: EjecutivosDashboardProps) {
  const { profile } = useAuth();
  const userSedeId = profile?.user?.sede ? String(profile.user.sede) : undefined;
  const [activeTab, setActiveTab] = useState(isAdminSede ? 'aprobaciones' : 'resumen');

  const produccion = useProduccionEjecutivo();
  const stockHook = useStockEjecutivo();
  const ventas = useVentasEjecutivo();

  const dash = useDashboardEjecutivoData({
    isAdminSede,
    userSedeId,
    setProduccionResumen: produccion.setProduccionResumen,
    setTendencia: produccion.setTendencia,
    setAlertas: stockHook.setAlertas,
    setStock: stockHook.setStock,
    setClientes: ventas.setClientes,
    setPedidos: ventas.setPedidos,
  });

  const exportes = useExportesGerenciales(dash.filtroSedeId);
  const produccionPorProducto = useProduccionPorProducto({
    fechaInicio: exportes.reportFechas.inicio,
    fechaFin: exportes.reportFechas.fin,
    sedeId: dash.filtroSedeId,
  });

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  if (dash.loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      </div>
    );
  }

  const kp = dash.kpiEjecutivo;
  const pr = produccion.produccionResumen;

  // ---------------------------------------------------------------------------
  // JSX
  // ---------------------------------------------------------------------------

  return (
    <div className="p-4 md:p-6 space-y-6 bg-slate-50/50 dark:bg-slate-950/50 min-h-screen">
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            {isAdminSede ? 'Panel de Administrador de Sede' : 'Panel Ejecutivo'}
          </h1>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mt-1">
            {isAdminSede
              ? 'Gestiona aprobaciones, planificación MRP, auditoría y métricas de tu sede.'
              : 'Vista gerencial consolidada'} — Hola, <span className="text-slate-700 dark:text-slate-300">{profile?.user?.username}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Selector de sede */}
          {!isAdminSede && (
            <Select value={dash.filtroSedeId} onValueChange={dash.setFiltroSedeId}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Todas las sedes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas las sedes</SelectItem>
                {dash.sedes.map(s => (
                  <SelectItem key={s.id} value={String(s.id)}>{s.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => dash.fetchData(true)}
            disabled={dash.refreshing}
            className="gap-1"
          >
            <RefreshCw className={`w-4 h-4 ${dash.refreshing ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>

          <Button
            variant={dash.autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => dash.setAutoRefresh(v => !v)}
            className="gap-1"
          >
            <Activity className="w-4 h-4" />
            Auto
          </Button>
        </div>
      </div>

      {/* ── Tabs principales ── */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="flex flex-wrap h-auto gap-1">
          {isAdminSede && <TabsTrigger value="aprobaciones" className="gap-1"><ClipboardList className="w-4 h-4" />Aprobaciones</TabsTrigger>}
          <TabsTrigger value="resumen" className="gap-1"><BarChart3 className="w-4 h-4" />Resumen</TabsTrigger>
          <TabsTrigger value="produccion" className="gap-1"><Factory className="w-4 h-4" />Producción</TabsTrigger>
          <TabsTrigger value="mrp" className="gap-1"><Layers className="w-4 h-4" />MRP</TabsTrigger>
          <TabsTrigger value="stock" className="gap-1"><Warehouse className="w-4 h-4" />Stock</TabsTrigger>
          <TabsTrigger value="ventas" className="gap-1"><TrendingUp className="w-4 h-4" />Ventas</TabsTrigger>
          <TabsTrigger value="reportes" className="gap-1"><FileSpreadsheet className="w-4 h-4" />Reportes</TabsTrigger>
          {isAdminSede && <TabsTrigger value="auditoria" className="gap-1"><History className="w-4 h-4" />Auditoría</TabsTrigger>}
        </TabsList>

        {isAdminSede && (
          <TabsContent value="aprobaciones" className="mt-4">
            <MovementApproval />
          </TabsContent>
        )}

        {/* TAB 1: RESUMEN EJECUTIVO — CU-EJ-01 */}
        <ResumenTab
          kp={kp}
          cuentasPorCobrar={ventas.cuentasPorCobrar}
          carteraVencida={ventas.carteraVencida}
          limiteCartera={ventas.limiteCartera}
          alertaCartera={ventas.alertaCartera}
        />

        {/* TAB 2: PRODUCCIÓN — CU-EJ-02, CU-EJ-03 */}
        <ProduccionTab
          pr={pr}
          datosTendenciaProcesados={produccion.datosTendenciaProcesados}
          rangoTendencia={produccion.rangoTendencia}
          setRangoTendencia={produccion.setRangoTendencia}
          agrupacionTendencia={produccion.agrupacionTendencia}
          setAgrupacionTendencia={produccion.setAgrupacionTendencia}
          reportFechas={exportes.reportFechas}
          setReportFechas={exportes.setReportFechas}
          exportOrdenes={exportes.exportOrdenes}
          exportLotes={exportes.exportLotes}
          productosPorProducto={produccionPorProducto.productos}
          cargandoProductosPorProducto={produccionPorProducto.cargandoProductos}
          productoSeleccionado={produccionPorProducto.productoSeleccionado}
          historialProducto={produccionPorProducto.historialProducto}
          cargandoHistorialProducto={produccionPorProducto.cargandoHistorial}
          imprimiendoProduccionPorProducto={produccionPorProducto.imprimiendo}
          onVerHistorialProducto={produccionPorProducto.verHistorialProducto}
          onCerrarHistorialProducto={produccionPorProducto.cerrarHistorialProducto}
          onImprimirProduccionPorProducto={produccionPorProducto.imprimirProduccionPorProducto}
        />

        {/* ════════════════════════════════════════════════════════════
            TAB 3: MRP — CU-EJ-04
            Reutiliza MRPDashboard existente (OCP — sin modificar el componente)
        ════════════════════════════════════════════════════════════ */}
        <TabsContent value="mrp" className="mt-4">
          {/* KPIs rápidos del MRP para contexto ejecutivo */}
          {!isAdminSede && (
            <div className="grid gap-4 grid-cols-2 md:grid-cols-4 mb-6">
              <KpiCard
                titulo="OCS Pendientes"
                valor={kp?.mrp.ocs_pendientes ?? '—'}
                icon={<ShoppingCart className="w-4 h-4" />}
                alerta={(kp?.mrp.ocs_pendientes ?? 0) > 0}
                alertaTexto="Pendientes de aprobación"
              />
              <KpiCard titulo="Productos en Déficit" valor={kp?.mrp.productos_en_deficit ?? '—'} icon={<AlertTriangle className="w-4 h-4" />} />
              <KpiCard titulo="OCS Aprobadas" valor={kp?.mrp.ocs_aprobadas ?? '—'} icon={<CheckCircle2 className="w-4 h-4" />} />
              <KpiCard titulo="OCS Rechazadas" valor={kp?.mrp.ocs_rechazadas ?? '—'} icon={<AlertCircle className="w-4 h-4" />} />
            </div>
          )}
          <MRPDashboard />
        </TabsContent>

        {/* TAB 4: STOCK — CU-EJ-05 */}
        <StockTab
          alertas={stockHook.alertas}
          stock={stockHook.stock}
          busquedaAlertas={stockHook.busquedaAlertas}
          setBusquedaAlertas={stockHook.setBusquedaAlertas}
          bodegaSeleccionada={stockHook.bodegaSeleccionada}
          setBodegaSeleccionada={stockHook.setBodegaSeleccionada}
          stockPorBodega={stockHook.stockPorBodega}
          alertasFiltradas={stockHook.alertasFiltradas}
          topAlertas={stockHook.topAlertas}
        />

        {/* TAB 5: VENTAS — CU-EJ-06 */}
        <VentasTab
          pedidos={ventas.pedidos}
          clientes={ventas.clientes}
          cuentasPorCobrar={ventas.cuentasPorCobrar}
          carteraVencida={ventas.carteraVencida}
          limiteCartera={ventas.limiteCartera}
          alertaCartera={ventas.alertaCartera}
          totalVentas={ventas.totalVentas}
          ventasPorVendedor={ventas.ventasPorVendedor}
          topClientesGerencial={ventas.topClientesGerencial}
          topDeudores={ventas.topDeudores}
          distribucionPago={ventas.distribucionPago}
          funnelData={ventas.funnelData}
          modalEstadoPedido={ventas.modalEstadoPedido}
          setModalEstadoPedido={ventas.setModalEstadoPedido}
          modalVendedor={ventas.modalVendedor}
          setModalVendedor={ventas.setModalVendedor}
          modalClienteCompras={ventas.modalClienteCompras}
          setModalClienteCompras={ventas.setModalClienteCompras}
          modalClienteDeudor={ventas.modalClienteDeudor}
          setModalClienteDeudor={ventas.setModalClienteDeudor}
          reportFechas={exportes.reportFechas}
          setReportFechas={exportes.setReportFechas}
          exportVentas={exportes.exportVentas}
          exportTopClientes={exportes.exportTopClientes}
          exportDeudores={exportes.exportDeudores}
        />

        {/* TAB 6: REPORTES DE GERENCIA — CU-EJ-07 */}
        <ReportesTab
          sedes={dash.sedes}
          filtroSedeId={dash.filtroSedeId}
          reportFechas={exportes.reportFechas}
          setReportFechas={exportes.setReportFechas}
          totalVentas={ventas.totalVentas}
          pedidosLength={ventas.pedidos.length}
          carteraVencida={ventas.carteraVencida}
          alertaCartera={ventas.alertaCartera}
          kp={kp}
          alertas={stockHook.alertas}
          descargando={exportes.descargando}
          exportVentas={exportes.exportVentas}
          exportTopClientes={exportes.exportTopClientes}
          exportDeudores={exportes.exportDeudores}
          exportOrdenes={exportes.exportOrdenes}
          exportLotes={exportes.exportLotes}
          exportTendencia={exportes.exportTendencia}
        />

        {isAdminSede && (
          <TabsContent value="auditoria" className="mt-4">
            <AuditLogViewer sedeId={userSedeId} permitirVerTodasSedes={false} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
