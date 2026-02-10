import React from 'react';
import { AuthProvider, useAuth } from './lib/auth';
import { Login } from './components/Login';
import { Layout } from './components/Layout';
import { OperarioDashboard } from './components/operario/OperarioDashboard';
import { JefeAreaDashboard } from './components/jefe-area/JefeAreaDashboard';
import { JefePlantaDashboard } from './components/jefe-planta/JefePlantaDashboard';
import { AdminSedeDashboard } from './components/admin-sede/AdminSedeDashboard';
import { EjecutivosDashboard } from './components/ejecutivos/EjecutivosDashboard';
import { AdminSistemasDashboard } from './components/admin-sistemas/AdminSistemasDashboard';
import { BodegueroDashboard } from './components/bodeguero/BodegueroDashboard';
import { VendedorDashboard } from './components/vendedor/VendedorDashboard';
import { EmpaquetadoDashboard } from './components/empaquetado/EmpaquetadoDashboard';
import { Toaster } from './components/ui/sonner';

function AppContent() {
  const { profile, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Login />;
  }

  const renderDashboard = () => {
    if (!profile) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <p>Cargando información del usuario...</p>
        </div>
      );
    }

    switch (profile.role) {
      case 'admin_sistemas':
        return <AdminSistemasDashboard />;
      case 'admin_sede':
        return <AdminSedeDashboard />;
      case 'jefe_planta':
        return <JefePlantaDashboard />;
      case 'jefe_area':
        return <JefeAreaDashboard />;
      case 'ejecutivo':
        return <EjecutivosDashboard />;
      case 'vendedor':
        return <VendedorDashboard />;
      case 'bodeguero':
        return <BodegueroDashboard />;
      case 'operario':
        return <OperarioDashboard />;
      case 'empaquetado':
        return <EmpaquetadoDashboard />;
      default:
        return (
          <div className="flex items-center justify-center min-h-screen">
            <p>Rol no reconocido o sin permisos asignados.</p>
          </div>
        );
    }
  };

  return (
    <Layout>
      {renderDashboard()}
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
      <Toaster />
    </AuthProvider>
  );
}
