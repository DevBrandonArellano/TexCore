import React, { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { TablaInsumosDosificacion } from '../shared/TablaInsumosDosificacion';
import { formulasApi } from '../../lib/api/formulasApi';
import { formatApiError } from '../../lib/errorUtils';
import type { DosificacionFormulaResultado } from '../../lib/types';

/**
 * Dosificación de la fórmula guardada para un peso de tela y unos litros de
 * baño, calculada en el servidor (la relación de baño se deriva: litros / peso).
 * La calculadora en vivo del editor (FormulaQuimica) cubre la receta sin guardar.
 */
export function DosificacionFormulaPanel({ formulaId }: { formulaId: number }) {
  const [peso, setPeso] = useState('');
  const [litros, setLitros] = useState('');
  const [resultado, setResultado] = useState<DosificacionFormulaResultado | null>(null);
  const [calculando, setCalculando] = useState(false);

  const calcular = async () => {
    const kg = parseFloat(peso);
    const l = parseFloat(litros);
    if (!(kg > 0) || !(l > 0)) {
      toast.error('Ingresa el peso de la tela y los litros de baño.');
      return;
    }
    setCalculando(true);
    try {
      setResultado(await formulasApi.calcularDosificacion(formulaId, kg, l));
    } catch (error) {
      const formatted = formatApiError(error);
      toast.error(formatted.message, { description: formatted.note });
    } finally {
      setCalculando(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 sm:items-end">
        <div className="space-y-2">
          <Label htmlFor="dosif-peso">Peso de la tela (kg)</Label>
          <Input id="dosif-peso" type="number" step="0.001" min="0" value={peso} onChange={(e) => setPeso(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="dosif-litros">Litros de baño</Label>
          <Input id="dosif-litros" type="number" step="0.01" min="0" value={litros} onChange={(e) => setLitros(e.target.value)} />
        </div>
        <Button onClick={calcular} disabled={calculando}>{calculando ? 'Calculando...' : 'Calcular'}</Button>
      </div>
      {resultado && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {Number(resultado.kg_tela).toFixed(3)} kg de tela · {Number(resultado.volumen_bano_litros).toFixed(2)} L ·
            relación 1:{Number(resultado.relacion_bano).toFixed(2)}
          </p>
          <TablaInsumosDosificacion insumos={resultado.insumos} />
        </div>
      )}
    </div>
  );
}
