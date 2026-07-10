import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('./axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

function Probe() {
  const { profile, isAuthenticated, isLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="role">{profile?.role ?? 'none'}</span>
      <button onClick={() => login('user', 'pass')}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe('AuthProvider / useAuth', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it('dado que useAuth se usa fuera de AuthProvider cuando se llama entonces lanza error', () => {
    const Bare = () => {
      useAuth();
      return null;
    };
    expect(() => render(<Bare />)).toThrow('useAuth must be used within an AuthProvider');
  });

  it('dado sesion valida cuando monta entonces carga el perfil y deja de cargar', async () => {
    mockGet.mockResolvedValueOnce({ data: { user: { id: 1, username: 'ana' }, role: 'vendedor' } });

    renderWithProvider();

    await waitFor(() => expect(screen.getByTestId('authenticated').textContent).toBe('true'));
    expect(screen.getByTestId('role').textContent).toBe('vendedor');
    expect(mockGet).toHaveBeenCalledWith('/profile/');
  });

  it('dado sin sesion valida cuando monta entonces queda no autenticado', async () => {
    mockGet.mockRejectedValueOnce(new Error('401'));

    renderWithProvider();

    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));
    expect(screen.getByTestId('authenticated').textContent).toBe('false');
  });

  it('dado login exitoso cuando se llama entonces guarda el perfil retornado', async () => {
    mockGet.mockRejectedValueOnce(new Error('401'));
    mockPost.mockResolvedValueOnce({ data: { user: { id: 2, username: 'luis' }, role: 'jefe_area' } });

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    await act(async () => {
      screen.getByText('login').click();
    });

    await waitFor(() => expect(screen.getByTestId('role').textContent).toBe('jefe_area'));
    expect(mockPost).toHaveBeenCalledWith('/token/', { username: 'user', password: 'pass' });
  });

  it('dado login fallido cuando se llama entonces mantiene el perfil en null', async () => {
    mockGet.mockRejectedValueOnce(new Error('401'));
    mockPost.mockRejectedValueOnce(new Error('credenciales inválidas'));

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'));

    await act(async () => {
      screen.getByText('login').click();
    });

    expect(screen.getByTestId('authenticated').textContent).toBe('false');
  });

  it('dado logout cuando se llama entonces limpia el perfil aunque el request falle', async () => {
    mockGet.mockResolvedValueOnce({ data: { user: { id: 1, username: 'ana' }, role: 'vendedor' } });
    mockPost.mockRejectedValueOnce(new Error('network error'));

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('authenticated').textContent).toBe('true'));

    await act(async () => {
      screen.getByText('logout').click();
    });

    await waitFor(() => expect(screen.getByTestId('authenticated').textContent).toBe('false'));
  });

  it('dado evento auth:session-expired cuando se dispara entonces limpia el perfil', async () => {
    mockGet.mockResolvedValueOnce({ data: { user: { id: 1, username: 'ana' }, role: 'vendedor' } });

    renderWithProvider();
    await waitFor(() => expect(screen.getByTestId('authenticated').textContent).toBe('true'));

    act(() => {
      window.dispatchEvent(new CustomEvent('auth:session-expired'));
    });

    await waitFor(() => expect(screen.getByTestId('authenticated').textContent).toBe('false'));
  });
});
