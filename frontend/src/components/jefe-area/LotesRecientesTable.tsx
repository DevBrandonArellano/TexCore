import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { XCircle } from 'lucide-react';
import type { LoteProduccion } from '../../lib/types';
import { TablaLotesPaginada } from '../lotes/TablaLotesPaginada';
import { RechazarLoteDialog } from './RechazarLoteDialog';

interface LotesRecientesTableProps {
  onRechazarLote: (loteId: number, motivo: string) => Promise<boolean>;
}

/** Lotes del área (el backend acota por área y sede) con la acción de rechazo. */
export function LotesRecientesTable({ onRechazarLote }: LotesRecientesTableProps) {
  const [loteRechazo, setLoteRechazo] = useState<LoteProduccion | null>(null);
  const [version, setVersion] = useState(0);

  const confirmarRechazo = async (motivo: string) => {
    if (!loteRechazo) return false;
    const rechazado = await onRechazarLote(loteRechazo.id, motivo);
    if (rechazado) setVersion((v) => v + 1);
    return rechazado;
  };

  return (
    <Card className="flex flex-col flex-shrink-0 mb-6">
      <CardHeader className="flex-shrink-0">
        <CardTitle>Gestión de Lotes Recientes</CardTitle>
        <CardDescription>Visualiza y gestiona la producción reciente.</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <TablaLotesPaginada
          version={version}
          accionesExtra={(lote) => (
            <Button variant="ghost" className="text-destructive h-8 px-2" onClick={() => setLoteRechazo(lote)}>
              <XCircle className="mr-2 h-4 w-4" /> Rechazar
            </Button>
          )}
        />
      </CardContent>
      <RechazarLoteDialog
        codigoLote={loteRechazo?.codigo_lote ?? null}
        onConfirmar={confirmarRechazo}
        onClose={() => setLoteRechazo(null)}
      />
    </Card>
  );
}
