import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

let mockAuthState: any = { isAuthenticated: false, profile: null };

vi.mock('./lib/auth', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => mockAuthState,
}));

vi.mock('./components/Login', () => ({ Login: () => <div>login-screen</div> }));
vi.mock('./components/Layout', () => ({
  Layout: ({ children }: { children: React.ReactNode }) => <div data-testid="layout">{children}</div>,
}));
vi.mock('./components/ui/sonner', () => ({ Toaster: () => null }));

vi.mock('./components/operario/OperarioDashboard', () => ({ OperarioDashboard: () => <div>operario</div> }));
vi.mock('./components/jefe-area/JefeAreaDashboard', () => ({ JefeAreaDashboard: () => <div>jefe-area</div> }));
vi.mock('./components/jefe-planta/JefePlantaDashboard', () => ({ JefePlantaDashboard: () => <div>jefe-planta</div> }));
vi.mock('./components/admin-sede/AdminSedeDashboard', () => ({ AdminSedeDashboard: () => <div>admin-sede</div> }));
vi.mock('./components/ejecutivos/EjecutivosDashboard', () => ({ EjecutivosDashboard: () => <div>ejecutivos</div> }));
vi.mock('./components/admin-sistemas/AdminSistemasDashboard', () => ({
  AdminSistemasDashboard: () => <div>admin-sistemas</div>,
}));
vi.mock('./components/bodeguero/BodegueroDashboard', () => ({ BodegueroDashboard: () => <div>bodeguero</div> }));
vi.mock('./components/vendedor/VendedorDashboard', () => ({ VendedorDashboard: () => <div>vendedor</div> }));
vi.mock('./components/empaquetado/EmpaquetadoDashboard', () => ({ EmpaquetadoDashboard: () => <div>empaquetado</div> }));
vi.mock('./components/despacho/DespachoDashboard', () => ({ DespachoDashboard: () => <div>despacho</div> }));
vi.mock('./components/despacho/HistorialDespachos', () => ({ HistorialDespachos: () => <div>historial-despachos</div> }));
vi.mock('./components/tintura/TintoreroDashboard', () => ({ TintoreroDashboard: () => <div>tintorero</div> }));

function renderApp() {
  return render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
}

describe('App — dispatch por rol', () => {
  it('dado usuario no autenticado cuando renderiza entonces muestra Login', () => {
    mockAuthState = { isAuthenticated: false, profile: null };
    renderApp();
    expect(screen.getByText('login-screen')).toBeInTheDocument();
  });

  it('dado autenticado sin profile aun cuando renderiza entonces muestra estado de carga', () => {
    mockAuthState = { isAuthenticated: true, profile: null };
    renderApp();
    expect(screen.getByText('Cargando información del usuario...')).toBeInTheDocument();
  });

  it.each([
    ['admin_sistemas', 'admin-sistemas'],
    ['admin_sede', 'admin-sede'],
    ['jefe_planta', 'jefe-planta'],
    ['jefe_area', 'jefe-area'],
    ['ejecutivo', 'ejecutivos'],
    ['vendedor', 'vendedor'],
    ['bodeguero', 'bodeguero'],
    ['operario', 'operario'],
    ['empaquetado', 'empaquetado'],
    ['tintorero', 'tintorero'],
  ])('dado rol %s cuando renderiza entonces muestra el dashboard %s', (role, expectedText) => {
    mockAuthState = { isAuthenticated: true, profile: { role, user: { id: 1 } } };
    renderApp();
    expect(screen.getByText(expectedText)).toBeInTheDocument();
    expect(screen.getByTestId('layout')).toBeInTheDocument();
  });

  it('dado rol despacho cuando renderiza entonces muestra DespachoDashboard en la ruta raiz', () => {
    mockAuthState = { isAuthenticated: true, profile: { role: 'despacho', user: { id: 1 } } };
    renderApp();
    expect(screen.getByText('despacho')).toBeInTheDocument();
  });

  it('dado rol no reconocido cuando renderiza entonces muestra mensaje de sin permisos', () => {
    mockAuthState = { isAuthenticated: true, profile: { role: 'rol_inexistente', user: { id: 1 } } };
    renderApp();
    expect(screen.getByText('Rol no reconocido o sin permisos asignados.')).toBeInTheDocument();
  });
});
