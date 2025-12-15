import React from 'react';
import { MovementApproval } from '../shared/MovementApproval';

export function AdminSedeDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Panel de Administrador de Sede</h1>
        <p className="text-muted-foreground">
          Aprueba o rechaza los movimientos de inventario de tu sede.
        </p>
      </div>
      <MovementApproval />
    </div>
  );
}