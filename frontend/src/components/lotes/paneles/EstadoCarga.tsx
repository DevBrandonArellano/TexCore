import React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

interface EstadoCargaProps {
  cargando: boolean;
  error: string | null;
  vacio?: boolean;
  mensajeVacio?: string;
  children: React.ReactNode;
}

/** Carga / error / vacío comunes a los paneles de la ficha de lote. */
export function EstadoCarga({ cargando, error, vacio = false, mensajeVacio = 'Sin información.', children }: EstadoCargaProps) {
  if (cargando) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground" role="status">
        <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
        Cargando…
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive" role="alert">
        <AlertTriangle className="inline h-4 w-4 mr-1.5" />
        {error}
      </div>
    );
  }
  if (vacio) return <p className="py-8 text-center text-sm text-muted-foreground">{mensajeVacio}</p>;
  return <>{children}</>;
}
