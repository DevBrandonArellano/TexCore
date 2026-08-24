import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { Layers, Users, Warehouse, Factory } from 'lucide-react';
import type { Sede, Area, User, Bodega, OrdenProduccion, PedidoVenta } from '../../lib/types';
import { getSedeStats } from './sedeUtils';

interface SedesSidebarProps {
  sedes: Sede[];
  selectedSedeId: string;
  onSelectSede: (sedeId: string) => void;
  areas: Area[];
  users: User[];
  bodegas: Bodega[];
  ordenes: OrdenProduccion[];
  pedidos: PedidoVenta[];
}

function SedesSidebarImpl({ sedes, selectedSedeId, onSelectSede, areas, users, bodegas, ordenes, pedidos }: SedesSidebarProps) {
  return (
    <aside className="lg:w-80 flex-shrink-0 flex flex-col">
      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader className="flex-shrink-0">
          <CardTitle>Sedes</CardTitle>
          <CardDescription>Selecciona una sede para ver sus datos</CardDescription>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto p-0">
          <div className="space-y-1 p-4">
            {sedes.map((sede) => {
              const stats = getSedeStats(sede.id.toString(), { sedes, areas, users, bodegas, ordenes, pedidos });
              const isSelected = selectedSedeId === sede.id.toString();

              return (
                <button
                  key={sede.id}
                  onClick={() => onSelectSede(sede.id.toString())}
                  className={`w-full text-left p-4 rounded-lg border-2 transition-all ${isSelected
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50 hover:bg-accent'
                    }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-medium">{sede.nombre}</h3>
                      <p className="text-sm text-muted-foreground">{sede.location}</p>
                    </div>
                    <Badge variant={sede.status === 'activo' ? 'default' : 'secondary'}>
                      {sede.status}
                    </Badge>
                  </div>

                  <Separator className="my-3" />

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-1">
                      <Layers className="w-3 h-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Áreas:</span>
                      <span className="font-medium">{stats.areas}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Users className="w-3 h-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Users:</span>
                      <span className="font-medium">{stats.users}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Warehouse className="w-3 h-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Bodegas:</span>
                      <span className="font-medium">{stats.bodegas}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Factory className="w-3 h-3 text-muted-foreground" />
                      <span className="text-muted-foreground">Órdenes:</span>
                      <span className="font-medium">{stats.ordenes}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </aside>
  );
}

export const SedesSidebar = React.memo(SedesSidebarImpl);
