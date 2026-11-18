import React from 'react';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { materialesSustratoApi } from '../../lib/api/materialesSustratoApi';

const SELECT_CLASES = 'flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm';

interface SelectorMaterialProps {
  id: string;
  /** Clave del material elegido (`FormulaColor.tipo_sustrato`). */
  value: string;
  onChange: (clave: string) => void;
  /** Nombre del material actual, para conservarlo como opción si ya está inactivo. */
  etiquetaActual?: string;
  /** Texto de la opción vacía; sin él, el selector exige un material. */
  opcional?: string;
}

/**
 * Selector del material (tipo de sustrato) de una fórmula. Ofrece los materiales
 * activos del catálogo de la sede, que mantiene el tintorero en la pestaña Materiales.
 */
export function SelectorMaterial({ id, value, onChange, etiquetaActual, opcional }: SelectorMaterialProps) {
  const { datos, cargando, error } = useCargaRemota(
    () => materialesSustratoApi.listar({ soloActivos: true }),
    'materiales-activos',
    { mensajeDeError: () => 'No se pudieron cargar los materiales.' },
  );
  const materiales = datos ?? [];
  // Una fórmula que ya usa un material desactivado lo conserva al editarse.
  const actualFueraDelCatalogo = value !== '' && !cargando && !materiales.some((m) => m.clave === value);

  return (
    <div className="space-y-1">
      <select id={id} className={SELECT_CLASES} value={value} disabled={cargando}
        onChange={(e) => onChange(e.target.value)}>
        {opcional !== undefined && <option value="">{opcional}</option>}
        {actualFueraDelCatalogo && <option value={value}>{`${etiquetaActual ?? value} (inactivo)`}</option>}
        {materiales.map((m) => <option key={m.id} value={m.clave}>{m.nombre}</option>)}
      </select>
      {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
