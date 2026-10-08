import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { formulasApi } from '../../lib/api/formulasApi';
import type { VersionFormula } from '../../lib/types';
import { useCargaRemota } from '../../hooks/useCargaRemota';

interface RecetaVersionDialogProps {
  formulaId: number;
  /** Versión a mostrar; `null` cierra el diálogo. */
  numero: number | null;
  onClose: () => void;
}

/** Receta congelada de una versión (snapshot): lo que se produjo con ella, aunque la fórmula viva haya cambiado. */
export function RecetaVersionDialog({ formulaId, numero, onClose }: RecetaVersionDialogProps) {
  const carga = useCargaRemota<VersionFormula>(
    () => formulasApi.version(formulaId, numero as number),
    `${formulaId}|${numero}`,
    { habilitado: numero != null },
  );
  const version = carga.datos;
  const error = carga.error !== null;

  return (
    <Dialog open={numero != null} onOpenChange={(abierto) => { if (!abierto) onClose(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Receta de la versión v{numero}</DialogTitle>
          <DialogDescription>
            {version ? (version.observaciones || version.motivo) : 'Receta congelada de esta versión.'}
          </DialogDescription>
        </DialogHeader>
        {error && <p className="text-sm text-destructive">No se pudo cargar la receta de esta versión.</p>}
        {!error && !version && <p className="text-sm text-muted-foreground">Cargando receta...</p>}
        {version && (
          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {version.snapshot.fases.map((fase) => (
              <div key={fase.orden} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold">Fase {fase.orden}: {fase.proceso_nombre}</span>
                  <span className="text-xs text-muted-foreground">{fase.temperatura ?? '—'}°C / {fase.tiempo ?? '—'}'</span>
                </div>
                {fase.detalles.map((d) => (
                  <div key={`${fase.orden}-${d.orden_adicion}-${d.producto_id}`}
                    className="flex justify-between text-xs bg-muted/30 rounded px-2 py-1">
                    <span>{d.producto_descripcion || d.producto_codigo || '—'}</span>
                    <span className="font-mono">
                      {d.tipo_calculo === 'gr_l' ? `${d.concentracion_gr_l ?? 0} g/L` : `${d.porcentaje ?? 0}%`}
                    </span>
                  </div>
                ))}
              </div>
            ))}
            {version.snapshot.fases.length === 0 && (
              <p className="text-sm text-muted-foreground">Esta versión no tiene fases.</p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
