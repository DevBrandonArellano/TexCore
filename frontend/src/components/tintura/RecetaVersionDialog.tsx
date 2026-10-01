import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { formulasApi } from '../../lib/api/formulasApi';
import type { VersionFormula } from '../../lib/types';

interface RecetaVersionDialogProps {
  formulaId: number;
  /** Versión a mostrar; `null` cierra el diálogo. */
  numero: number | null;
  onClose: () => void;
}

/** Receta congelada de una versión (snapshot): lo que se produjo con ella, aunque la fórmula viva haya cambiado. */
export function RecetaVersionDialog({ formulaId, numero, onClose }: RecetaVersionDialogProps) {
  const [version, setVersion] = useState<VersionFormula | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (numero == null) return;
    let vigente = true;
    setVersion(null);
    setError(false);
    formulasApi.version(formulaId, numero)
      .then((v) => { if (vigente) setVersion(v); })
      .catch(() => { if (vigente) setError(true); });
    return () => { vigente = false; };
  }, [formulaId, numero]);

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
