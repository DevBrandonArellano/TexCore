import React from 'react';
import { MovementApproval } from '../shared/MovementApproval';

export function JefeAreaDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Panel de Jefe de Área</h1>
        <p className="text-muted-foreground">
          Aprueba o rechaza los movimientos de inventario de tu área.
        </p>
      </div>
      <MovementApproval />
    </div>
  );
}