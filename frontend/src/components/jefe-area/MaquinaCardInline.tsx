import React from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Settings2, Activity, Share2, OctagonPause } from 'lucide-react';
import type { Maquina, OeeResultado } from '../../lib/types';

interface MaquinaCardInlineProps {
  m: Maquina;
  carga: number;
  compartida: boolean;
  onEdit: (m: Maquina) => void;
  onToggle: (m: Maquina) => void;
  oee?: OeeResultado;
  onRegistrarParo: (m: Maquina) => void;
}

function MaquinaCardInlineImpl({
  m, carga, compartida, onEdit, onToggle, oee, onRegistrarParo,
}: MaquinaCardInlineProps) {
  const estadoColor =
    m.estado === 'operativa' ? 'bg-green-500/20 border-green-200' :
    m.estado === 'mantenimiento' ? 'bg-amber-500/20 border-amber-200' :
    'bg-red-500/20 border-red-200';

  return (
    <div className={`p-4 border rounded-lg ${estadoColor} hover:shadow-md transition-all`}>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-3 gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <div className={`h-3 w-3 rounded-full shrink-0 ${
              m.estado === 'operativa' ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]' :
              m.estado === 'mantenimiento' ? 'bg-amber-500' : 'bg-red-500'
            }`} />
            <h4 className="font-bold text-sm break-words">{m.nombre}</h4>
            <Badge className={`shrink-0 text-[9px] font-medium ${
              m.estado === 'operativa' ? 'bg-green-100 text-green-800' :
              m.estado === 'mantenimiento' ? 'bg-amber-100 text-amber-800' :
              'bg-red-100 text-red-800'
            }`}>
              {m.estado === 'operativa' ? '✓ Operativa' :
               m.estado === 'mantenimiento' ? '⚙ Mantenimiento' : '✕ Inactiva'}
            </Badge>
            {compartida && (
              <Badge variant="outline" className="shrink-0 text-[9px] gap-1 border-blue-300 text-blue-700 bg-blue-50">
                <Share2 className="h-2.5 w-2.5" />
                Recurso Compartido
              </Badge>
            )}
            {oee && (
              <Badge variant="outline" className="shrink-0 text-[9px] gap-1 border-purple-300 text-purple-700 bg-purple-50">
                OEE {(oee.oee * 100).toFixed(1)}%
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">Capacidad: {m.capacidad_maxima} Kg/Turno</p>
        </div>
        <div className="flex items-center gap-1 shrink-0 self-end sm:self-auto">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(m)} title="Editar máquina">
            <Settings2 className="h-4 w-4 text-gray-600" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => onToggle(m)}
            title={m.estado === 'operativa' ? 'Desactivar' : 'Activar'}
          >
            <Activity className={`h-4 w-4 ${m.estado === 'operativa' ? 'text-green-600' : 'text-gray-400'}`} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 gap-1 text-gray-600"
            onClick={() => onRegistrarParo(m)}
            title="Registrar Paro"
          >
            <OctagonPause className="h-4 w-4" />
            Paro
          </Button>
        </div>
      </div>

      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-700">Avance de Carga</span>
          <span className={`text-xs font-bold ${carga > 80 ? 'text-red-600' : carga > 60 ? 'text-amber-600' : 'text-green-600'}`}>
            {carga}%
          </span>
        </div>
        <Progress value={carga} className="h-2.5 rounded-full" />
      </div>

      <div className="mt-3">
        <p className="text-xs font-medium text-gray-700 mb-2">
          Operarios Asignados ({m.operarios_nombres?.length || 0})
        </p>
        {m.operarios_nombres && m.operarios_nombres.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {m.operarios_nombres.map((name, i) => (
              <Badge key={i} variant="secondary" className="bg-blue-100 text-blue-900 text-[11px] font-normal">
                👤 {name}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground italic">Sin operarios asignados</p>
        )}
      </div>
    </div>
  );
}

export const MaquinaCardInline = React.memo(MaquinaCardInlineImpl);
