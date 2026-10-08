import { Package } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { useAuth } from '../../lib/auth';
import { pestanasParaRol } from './pestanasFichaLote';
import type { LoteReferencia } from './paneles/tipos';

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
