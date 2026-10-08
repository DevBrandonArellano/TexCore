import type React from 'react';
import { PanelResumen } from './paneles/PanelResumen';
import { PanelGenealogiaDeLote } from './paneles/PanelGenealogia';
import { PanelMovimientos } from './paneles/PanelMovimientos';
import { PanelMateriasPrimas } from './paneles/PanelMateriasPrimas';
import { PanelConsumos } from './paneles/PanelConsumos';
import { PanelCosto } from './paneles/PanelCosto';
import type { LoteReferencia } from './paneles/tipos';

export interface DefinicionPestana {
  id: string;
  etiqueta: string;
  /** Mismos roles que exige el endpoint del panel en el backend; `null` = cualquiera que vea el lote. */
  roles: readonly string[] | null;
  Panel: React.ComponentType<{ lote: LoteReferencia }>;
}

const ROLES_PRODUCCION = ['operario', 'jefe_area', 'jefe_planta', 'admin_sede', 'admin_sistemas'] as const;
// IsInventoryStaffOrAdmin: todos salvo el operario raso.
const ROLES_INVENTARIO = [
  'admin_sistemas', 'admin_sede', 'bodeguero', 'despacho', 'ejecutivo',
  'empaquetado', 'jefe_area', 'jefe_planta', 'tintorero', 'vendedor',
] as const;
// IsTrazabilidadCostosRole: la pestaña expone proveedores y costos de compra.
const ROLES_COSTOS = ['bodeguero', 'jefe_planta', 'ejecutivo', 'admin_sede', 'admin_sistemas'] as const;

/** Registro de pestañas: agregar una es agregar una entrada, sin tocar el diálogo. */
export const PESTANAS_FICHA_LOTE: readonly DefinicionPestana[] = [
  { id: 'resumen', etiqueta: 'Resumen', roles: null, Panel: PanelResumen },
  {
    id: 'genealogia',
    etiqueta: 'Genealogía',
    roles: ROLES_PRODUCCION,
    Panel: PanelGenealogiaDeLote,
  },
  { id: 'movimientos', etiqueta: 'Movimientos', roles: ROLES_INVENTARIO, Panel: PanelMovimientos },
  { id: 'consumos', etiqueta: 'Consumos', roles: null, Panel: PanelConsumos },
  { id: 'materias-primas', etiqueta: 'Materias primas y costos', roles: ROLES_COSTOS, Panel: PanelMateriasPrimas },
  // IsTrazabilidadCostosRole también en obtener-costo (F0-002).
  { id: 'costo', etiqueta: 'Costo', roles: ROLES_COSTOS, Panel: PanelCosto },
];

export function pestanasParaRol(rol: string | null | undefined): readonly DefinicionPestana[] {
  return PESTANAS_FICHA_LOTE.filter((p) => p.roles === null || (!!rol && p.roles.includes(rol)));
}
