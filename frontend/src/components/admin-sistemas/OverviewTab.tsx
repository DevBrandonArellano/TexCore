import React from 'react';
import { TabsContent } from '../ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Layers, Users, Warehouse, ShoppingCart } from 'lucide-react';
import type { Sede, Area, Bodega } from '../../lib/types';

interface OverviewTabProps {
  selectedSedeData: Sede | undefined;
  sedeAreas: Area[];
  bodegas: Bodega[];
}

function OverviewTabImpl({ selectedSedeData, sedeAreas, bodegas }: OverviewTabProps) {
  return (
    <TabsContent value="overview" className="space-y-4">

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Áreas</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedSedeData?.num_areas || 0}</div>
            <p className="text-xs text-muted-foreground">departamentos en sede</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Usuarios</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedSedeData?.num_users || 0}</div>
            <p className="text-xs text-muted-foreground">personal registrado</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Bodegas</CardTitle>
            <Warehouse className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedSedeData?.num_bodegas || 0}</div>
            <p className="text-xs text-muted-foreground">almacenamiento activo</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ventas (Pedidos)</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(selectedSedeData as any)?.num_pedidos || 0}</div>
            <p className="text-xs text-muted-foreground">órdenes totales</p>
          </CardContent>
        </Card>
      </div>


      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Áreas de la Sede</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {sedeAreas.length > 0 ? (
                sedeAreas.map(area => (
                  <div key={area.id} className="flex items-center justify-between p-2 rounded-lg bg-accent">
                    <span>{area.nombre}</span>
                    <Badge variant="outline">ID: {area.id}</Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No hay áreas registradas</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Bodegas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {bodegas.length > 0 ? (
                bodegas.map(bodega => (
                  <div key={bodega.id} className="flex items-center gap-2 p-2 rounded-lg bg-accent">
                    <Warehouse className="w-4 h-4 text-muted-foreground" />
                    <span className="flex-1">{bodega.nombre}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No hay bodegas registradas</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </TabsContent>
  );
}

export const OverviewTab = React.memo(OverviewTabImpl);
