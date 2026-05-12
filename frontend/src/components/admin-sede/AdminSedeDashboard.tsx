import React from 'react';
import { EjecutivosDashboard } from '../ejecutivos/EjecutivosDashboard';

export function AdminSedeDashboard() {
  return <EjecutivosDashboard isAdminSede={true} />;
}