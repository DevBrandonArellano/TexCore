import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { TablaInsumosDosificacion } from '../shared/TablaInsumosDosificacion';
import { ordenesApi } from '../../lib/api/ordenesApi';
import { formatApiError } from '../../lib/errorUtils';
import type { DosificacionOrdenResultado, ProcesoTintoreria } from '../../lib/types';

interface DosificacionOrdenPanelProps {
  ordenId: number;
  maquinaId: number | null | undefined;
  /** Litros de baño propuestos (aún sin guardar). */
  litros: string;
}

/**
 * Vista previa del baño de tintura de una orden: cuánto químico lleva con los
 * litros propuestos (calculado en el servidor sobre la versión de fórmula de la
 * orden; no guarda nada) y qué procesos de tintorería ejecuta la máquina asignada.
 */
export function DosificacionOrdenPanel({ ordenId, maquinaId, litros }: DosificacionOrdenPanelProps) {
  const [resultado, setResultado] = useState<DosificacionOrdenResultado | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [procesos, setProcesos] = useState<ProcesoTintoreria[]>([]);

  useEffect(() => {
    setResultado(null);
  }, [ordenId]);

  useEffect(() => {
    if (!maquinaId) {
      setProcesos([]);
      return;
    }
    let vigente = true;
    ordenesApi.procesosDeMaquina(maquinaId)
      .then((lista) => { if (vigente) setProcesos(lista); })
      .catch(() => { if (vigente) setProcesos([]); });
    return () => { vigente = false; };
  }, [maquinaId]);

  const calcular = async () => {
    const valor = parseFloat(litros);
    if (!(valor > 0)) {
      toast.error('Ingresa los litros de baño para calcular la dosificación.');
      return;
    }
    setCalculando(true);
    try {
      setResultado(await ordenesApi.calcularDosificacion(ordenId, valor));
    } catch (error) {
      const formatted = formatApiError(error);
      toast.error(formatted.message, { description: formatted.note });
    } finally {
      setCalculando(false);
    }
  };

  return (
    <div className="space-y-3">
      {procesos.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-muted-foreground">Procesos que ejecuta la máquina asignada</span>
          <div className="flex flex-wrap gap-1">
            {procesos.map((p) => <Badge key={p.id} variant="outline">{p.nombre}</Badge>)}
          </div>
        </div>
      )}

      <Button variant="outline" size="sm" onClick={calcular} disabled={calculando}>
        {calculando ? 'Calculando...' : 'Ver dosificación'}
      </Button>

      {resultado && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {Number(resultado.peso).toFixed(3)} kg de tela · {Number(resultado.litros_bano).toFixed(2)} L ·
            relación 1:{Number(resultado.relacion_bano).toFixed(2)}
          </p>
          <TablaInsumosDosificacion insumos={resultado.insumos} />
        </div>
      )}
    </div>
  );
}
