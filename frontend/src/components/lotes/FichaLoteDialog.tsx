import React from 'react';
import { Package } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { useAuth } from '../../lib/auth';
import { PanelResumen } from './paneles/PanelResumen';
import { PanelGenealogia } from './paneles/PanelGenealogia';
import { PanelMovimientos } from './paneles/PanelMovimientos';
import { PanelMateriasPrimas } from './paneles/PanelMateriasPrimas';
import { PanelConsumos } from './paneles/PanelConsumos';
import { PanelCosto } from './paneles/PanelCosto';
import type { LoteReferencia } from './paneles/tipos';

interface DefinicionPestana {
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
    Panel: ({ lote }) => <PanelGenealogia loteCodigo={lote.codigo_lote} />,
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

interface FichaLoteDialogProps {
  lote: LoteReferencia | null;
  onClose: () => void;
}

/**
 * Ficha de lote: reúne en un solo lugar la trazabilidad del lote. Cada panel
 * carga sus datos al activarse (Radix monta solo la pestaña visible).
 */
export function FichaLoteDialog({ lote, onClose }: FichaLoteDialogProps) {
  const { profile } = useAuth();
  const pestanas = pestanasParaRol(profile?.role);

  return (
    <Dialog open={lote !== null} onOpenChange={(abierto) => !abierto && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        {lote && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Package className="h-5 w-5 text-primary" />
                Ficha del lote <span className="font-mono">{lote.codigo_lote}</span>
              </DialogTitle>
              <DialogDescription>Producción, genealogía, movimientos, consumos y costos del lote.</DialogDescription>
            </DialogHeader>
            <Tabs defaultValue={pestanas[0].id}>
              <TabsList className="flex flex-wrap h-auto">
                {pestanas.map((p) => (
                  <TabsTrigger key={p.id} value={p.id}>
                    {p.etiqueta}
                  </TabsTrigger>
                ))}
              </TabsList>
              {pestanas.map(({ id, Panel }) => (
                <TabsContent key={id} value={id} className="pt-4">
                  <Panel lote={lote} />
                </TabsContent>
              ))}
            </Tabs>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
