import React, { useState } from 'react';
import { ManageMaquinas } from './ManageMaquinas';
import { ManageLineas } from './ManageLineas';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Activity, GitBranch } from 'lucide-react';
import { EtapasProduccion } from '../produccion/EtapasProduccion';
import { FlujoProduccion } from '../produccion/FlujoProduccion';
import { TrazabilidadProducto } from '../produccion/TrazabilidadProducto';
import { BuscadorLotes } from '../empaquetado/BuscadorLotes';
import { RegistrarParoModal } from './RegistrarParoModal';
import { useAuth } from '../../lib/auth';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { useJefeAreaData } from './useJefeAreaData';
import { useMaquinaActions } from './useMaquinaActions';
import { MaquinaDialog } from './MaquinaDialog';
import { KpiSection } from './KpiSection';
import { OrdenesAsignacionPanel } from './OrdenesAsignacionPanel';
import { MaquinasPorLineaPanel } from './MaquinasPorLineaPanel';
import { AlertasInventarioPanel } from './AlertasInventarioPanel';
import { LotesRecientesTable } from './LotesRecientesTable';

export function JefeAreaDashboard() {
  const { profile } = useAuth();
  const {
    kpis, maquinas, alertas, lotes, ordenes, operarios, lineas,
    isLoading, maquinasCarga, maquinasOee, fetchDashboardData,
  } = useJefeAreaData(profile);

  const {
    isMaquinaDialogOpen, setIsMaquinaDialogOpen,
    selectedMaquina,
    handleEditMaquina, handleToggleEstadoMaquina, handleRechazarLote,
  } = useMaquinaActions(fetchDashboardData);

  const [trazaOrdenId, setTrazaOrdenId] = useState<number | null>(null);
  const [paroModalMaquina, setParoModalMaquina] = useState<{ id: number; nombre: string } | null>(null);

  if (isLoading) return <div>Cargando panel...</div>;

  return (
    <div className="flex flex-col space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 flex-shrink-0">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Panel de Control - Área de Producción</h1>
          <p className="text-sm text-muted-foreground">Monitoreo en tiempo real de KPIs y maquinaria.</p>
        </div>
        <Button onClick={fetchDashboardData} variant="outline" size="sm" className="self-start sm:self-auto">
          <Activity className="mr-2 h-4 w-4" /> Actualizar Datos
        </Button>
      </div>

      <KpiSection kpis={kpis} alertasCount={alertas.length} />

      <OrdenesAsignacionPanel
        ordenes={ordenes}
        maquinas={maquinas}
        operarios={operarios}
        onDataRefresh={fetchDashboardData}
      />

      {/* Producción en curso — trazabilidad de transformaciones máquina a máquina */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-primary" /> Producción en Curso — Trazabilidad
          </CardTitle>
          <CardDescription>
            Registra cada transformación de máquina (cambio de código y merma) y consulta el flujo completo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {ordenes.filter(o => o.estado === 'en_proceso').length > 0 ? (
            <div className="space-y-3">
              {ordenes.filter(o => o.estado === 'en_proceso').map((orden) => (
                <div key={orden.id} className="flex items-center justify-between gap-3 p-3 border rounded-lg bg-slate-50/50">
                  <div className="flex items-center gap-2 min-w-0">
                    <Badge variant="outline" className="font-mono text-[10px] text-blue-600 border-blue-200 bg-blue-50">{orden.codigo}</Badge>
                    <span className="font-medium text-slate-800 truncate">{orden.producto_nombre}</span>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => setTrazaOrdenId(orden.id)}>
                    <GitBranch className="mr-2 h-4 w-4" /> Ver flujo / Registrar
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-lg border border-dashed">
              <GitBranch className="h-8 w-8 text-muted-foreground mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">No hay órdenes en proceso en tu área.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Diálogo: timeline de trazabilidad + registro de transformaciones */}
      <Dialog open={trazaOrdenId !== null} onOpenChange={(o) => !o && setTrazaOrdenId(null)}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Flujo de Producción</DialogTitle>
            <DialogDescription>Transformaciones máquina a máquina de la orden seleccionada.</DialogDescription>
          </DialogHeader>
          {trazaOrdenId !== null && (
            <TrazabilidadProducto ordenId={trazaOrdenId} allowRegister />
          )}
        </DialogContent>
      </Dialog>

      {/* Buscador y Reetiquetado Supervisado de Lotes */}
      <BuscadorLotes />

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-7 flex-shrink-0">
        <MaquinasPorLineaPanel
          maquinas={maquinas}
          lineas={lineas}
          maquinasCarga={maquinasCarga}
          maquinasOee={maquinasOee}
          areaId={profile?.user.area ?? undefined}
          onDataRefresh={fetchDashboardData}
          onEdit={handleEditMaquina}
          onToggle={handleToggleEstadoMaquina}
          onRegistrarParo={(mm) => setParoModalMaquina({ id: mm.id, nombre: mm.nombre })}
        />

        <AlertasInventarioPanel alertas={alertas} />
      </div>

      <LotesRecientesTable lotes={lotes} onRechazarLote={handleRechazarLote} />

      {/* Flujo de Producción - Visualización General */}
      {profile?.user.area && (
        <FlujoProduccion />
      )}

      {/* Etapas de Producción - Configuración */}
      {profile?.user.area && (
        <EtapasProduccion areaId={profile.user.area} />
      )}

      {/* Gestión avanzada de máquinas con merma */}
      <Card className="flex-shrink-0">
        <CardHeader>
          <CardTitle>Gestión de Máquinas</CardTitle>
          <CardDescription>Administra máquinas, estados y configuración de merma vendible.</CardDescription>
        </CardHeader>
        <CardContent>
          <ManageMaquinas areaId={profile?.user.area ?? undefined} />
        </CardContent>
      </Card>

      {/* Gestión de líneas de producción (células de manufactura flexible) */}
      <Card className="flex-shrink-0">
        <CardHeader>
          <CardTitle>Líneas de Producción</CardTitle>
          <CardDescription>
            Agrupa máquinas en células de manufactura flexible. Las máquinas compartidas entre líneas
            activas se marcan como "Recurso Compartido" para maximizar el OEE.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ManageLineas
            areaId={profile?.user.area ?? undefined}
            onChange={fetchDashboardData}
          />
        </CardContent>
      </Card>

      <MaquinaDialog
        open={isMaquinaDialogOpen}
        onOpenChange={setIsMaquinaDialogOpen}
        maquina={selectedMaquina}
        operarios={operarios}
        areaId={profile?.user.area ?? undefined}
        onSave={fetchDashboardData}
      />

      <RegistrarParoModal
        open={paroModalMaquina !== null}
        onOpenChange={(open) => !open && setParoModalMaquina(null)}
        maquinaId={paroModalMaquina?.id ?? null}
        maquinaNombre={paroModalMaquina?.nombre}
        onRegistrado={fetchDashboardData}
      />

    </div>
  );
}
