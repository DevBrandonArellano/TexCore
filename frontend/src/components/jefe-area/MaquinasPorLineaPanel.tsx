import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Activity, Zap } from 'lucide-react';
import type { Maquina, LineaProduccion, OeeResultado } from '../../lib/types';
import { ManageLineas } from './ManageLineas';
import { MaquinaCardInline } from './MaquinaCardInline';
import { agruparMaquinasPorLinea } from './maquinaUtils';

interface MaquinasPorLineaPanelProps {
  maquinas: Maquina[];
  lineas: LineaProduccion[];
  maquinasCarga: Record<number, number>;
  maquinasOee: Record<number, OeeResultado>;
  areaId: number | undefined;
  onDataRefresh: () => void;
  onEdit: (m: Maquina) => void;
  onToggle: (m: Maquina) => void;
  onRegistrarParo: (m: Maquina) => void;
}

function MaquinasPorLineaPanelImpl({
  maquinas,
  lineas,
  maquinasCarga,
  maquinasOee,
  areaId,
  onDataRefresh,
  onEdit,
  onToggle,
  onRegistrarParo,
}: MaquinasPorLineaPanelProps) {
  const gruposPorLinea = useMemo(() => agruparMaquinasPorLinea(lineas, maquinas), [lineas, maquinas]);

  const calculateMachineLoad = (maquina: Maquina) => maquinasCarga[maquina.id] || 0;

  return (
    <Card className="col-span-4 flex flex-col h-auto">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-500" />
              Estado de Máquinas y Carga
            </CardTitle>
            <CardDescription>Monitoreo de capacidad, avance y personal asignado por célula de manufactura.</CardDescription>
          </div>
          <ManageLineas areaId={areaId} onChange={onDataRefresh} />
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto min-h-0">
        <div className="space-y-4">
          {gruposPorLinea.grupos.length === 0 && gruposPorLinea.sinLinea.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50 rounded-lg border border-dashed">
              <Zap className="w-8 h-8 text-muted-foreground mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">No hay máquinas registradas en esta área.</p>
            </div>
          ) : gruposPorLinea.grupos.length === 0 ? (
            // Sin líneas: lista plana (comportamiento original)
            gruposPorLinea.sinLinea.map((m) => (
              <MaquinaCardInline
                key={m.id}
                m={m}
                carga={calculateMachineLoad(m)}
                compartida={false}
                onEdit={onEdit}
                onToggle={onToggle}
                oee={maquinasOee[m.id]}
                onRegistrarParo={onRegistrarParo}
              />
            ))
          ) : (
            <>
              {gruposPorLinea.grupos.map(({ linea, maquinas: ms }) => (
                <div key={linea.id}>
                  <div className="flex items-center gap-2 mb-2 px-1">
                    <h5 className="text-sm font-semibold text-slate-700">{linea.nombre}</h5>
                    <Badge
                      variant={linea.estado === 'activa' ? 'default' : 'secondary'}
                      className="text-[9px]"
                    >
                      {linea.estado}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {ms.length} máquina{ms.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="space-y-3 pl-2 border-l-2 border-slate-200">
                    {ms.map((m) => (
                      <MaquinaCardInline
                        key={`${linea.id}-${m.id}`}
                        m={m}
                        carga={calculateMachineLoad(m)}
                        compartida={gruposPorLinea.compartidaIds.has(m.id)}
                        onEdit={onEdit}
                        onToggle={onToggle}
                        oee={maquinasOee[m.id]}
                        onRegistrarParo={onRegistrarParo}
                      />
                    ))}
                    {ms.length === 0 && (
                      <p className="text-xs text-muted-foreground italic py-2">Sin máquinas asignadas</p>
                    )}
                  </div>
                </div>
              ))}
              {gruposPorLinea.sinLinea.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2 px-1">
                    <h5 className="text-sm font-semibold text-slate-500">Sin línea</h5>
                    <span className="text-xs text-muted-foreground">
                      {gruposPorLinea.sinLinea.length} máquina{gruposPorLinea.sinLinea.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="space-y-3 pl-2 border-l-2 border-slate-100">
                    {gruposPorLinea.sinLinea.map((m) => (
                      <MaquinaCardInline
                        key={m.id}
                        m={m}
                        carga={calculateMachineLoad(m)}
                        compartida={false}
                        onEdit={onEdit}
                        onToggle={onToggle}
                        oee={maquinasOee[m.id]}
                        onRegistrarParo={onRegistrarParo}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export const MaquinasPorLineaPanel = React.memo(MaquinasPorLineaPanelImpl);
