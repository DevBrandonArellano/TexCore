import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Layout } from './Layout';

const useAuthMock = vi.fn();
vi.mock('../lib/auth', () => ({
  useAuth: () => useAuthMock(),
}));

function buildProfile(overrides: Partial<{ role: string | null; user: Record<string, unknown> }> = {}) {
  return {
    role: 'vendedor',
    user: {
      id: 1,
      first_name: 'Ana',
      last_name: 'Torres',
      email: 'ana.torres@texcore.com',
    },
    ...overrides,
  };
}

describe('Layout', () => {
  const logoutMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useAuthMock.mockReturnValue({ profile: buildProfile(), logout: logoutMock });
  });

  it('dado un perfil valido cuando renderiza entonces muestra el contenido hijo', () => {
    render(
      <Layout>
        <div>Contenido de la pagina</div>
      </Layout>,
    );

    expect(screen.getByText('Contenido de la pagina')).toBeInTheDocument();
  });

  it('dado sin perfil cuando renderiza entonces no muestra nada', () => {
    useAuthMock.mockReturnValue({ profile: null, logout: logoutMock });

    const { container } = render(
      <Layout>
        <div>Contenido de la pagina</div>
      </Layout>,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('dado un perfil con rol vendedor cuando renderiza entonces muestra la etiqueta del rol', () => {
    render(
      <Layout>
        <div>hijo</div>
      </Layout>,
    );

    expect(screen.getByText('Vendedor')).toBeInTheDocument();
  });

  it('dado un perfil con rol jefe_area cuando renderiza entonces muestra la etiqueta correspondiente', () => {
    useAuthMock.mockReturnValue({ profile: buildProfile({ role: 'jefe_area' }), logout: logoutMock });

    render(
      <Layout>
        <div>hijo</div>
      </Layout>,
    );

    expect(screen.getByText('Jefe de Área')).toBeInTheDocument();
  });

  it('dado un rol no mapeado cuando renderiza entonces muestra el rol tal cual', () => {
    useAuthMock.mockReturnValue({ profile: buildProfile({ role: 'rol_desconocido' }), logout: logoutMock });

    render(
      <Layout>
        <div>hijo</div>
      </Layout>,
    );

    expect(screen.getByText('rol_desconocido')).toBeInTheDocument();
  });

  it('dado un usuario cuando renderiza entonces muestra la inicial de su primer nombre en el avatar', () => {
    render(
      <Layout>
        <div>hijo</div>
      </Layout>,
    );

    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('dado click en el boton de cerrar sesion de escritorio cuando se hace click entonces llama a logout', async () => {
    render(
      <Layout>
        <div>hijo</div>
      </Layout>,
    );

    await userEvent.click(screen.getByRole('button', { name: /cerrar sesión/i }));

    expect(logoutMock).toHaveBeenCalledTimes(1);
  });

  it('dado el menu de usuario abierto cuando se hace click en cerrar sesion entonces llama a logout y muestra los datos del usuario', async () => {
    render(
      <Layout>
        <div>hijo</div>
      </Layout>,
    );

    await userEvent.click(screen.getByText('A'));

    expect(screen.getByText('Ana Torres')).toBeInTheDocument();
    expect(screen.getByText('ana.torres@texcore.com')).toBeInTheDocument();

    const opcionesCerrarSesion = screen.getAllByText('Cerrar Sesión');
    await userEvent.click(opcionesCerrarSesion[opcionesCerrarSesion.length - 1]);

    expect(logoutMock).toHaveBeenCalledTimes(1);
  });
});
