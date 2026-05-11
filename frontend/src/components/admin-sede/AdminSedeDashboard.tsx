import React from 'react';
import { MovementApproval } from '../shared/MovementApproval';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { MRPDashboard } from '../shared/MRPDashboard';
import { AuditLogViewer } from '../shared/AuditLogViewer';
import { ClipboardList, ShoppingCart, History } from 'lucide-react';
import { useAuth } from '../../lib/auth';

export function AdminSedeDashboard() {
  const { profile } = useAuth();
  const sedeId = profile?.user?.sede ? String(profile.user.sede) : undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Panel de Administrador de Sede</h1>
        <p className="text-muted-foreground">
          Gestiona aprobaciones, planificación MRP y auditoría de tu sede.
        </p>
      </div>

      <Tabs defaultValue="aprobaciones" className="w-full">
        <TabsList>
          <TabsTrigger value="aprobaciones" className="gap-2">
            <ClipboardList className="w-4 h-4" />
            Aprobaciones
          </TabsTrigger>
          <TabsTrigger value="mrp" className="gap-2">
            <ShoppingCart className="w-4 h-4" />
            MRP
          </TabsTrigger>
          <TabsTrigger value="auditoria" className="gap-2">
            <History className="w-4 h-4" />
            Auditoría
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="aprobaciones" className="mt-4">
          <MovementApproval />
        </TabsContent>
        
        <TabsContent value="mrp" className="mt-4">
          <MRPDashboard />
        </TabsContent>

        <TabsContent value="auditoria" className="mt-4">
          <AuditLogViewer sedeId={sedeId} permitirVerTodasSedes={false} />
        </TabsContent>
      </Tabs>
    </div>
  );
}