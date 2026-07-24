import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Login } from './Login';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

const mockLogin = vi.fn();

vi.mock('../lib/auth', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

function renderLogin() {
  return render(
    <BrowserRouter>
      <Login />
    </BrowserRouter>
  );
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('dado el formulario cuando se renderiza entonces muestra los campos de usuario y contraseña', () => {
    renderLogin();

    expect(screen.getByLabelText('Usuario')).toBeInTheDocument();
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeInTheDocument();
  });

  it('dado un envio vacio cuando se hace submit entonces muestra un error de validacion y no llama a login', async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(screen.getByText('Por favor ingresa usuario y contraseña')).toBeInTheDocument();
    });
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('dado solo el usuario cuando se hace submit sin contraseña entonces muestra un error de validacion y no llama a login', async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText('Usuario'), 'user_vendedor');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(screen.getByText('Por favor ingresa usuario y contraseña')).toBeInTheDocument();
    });
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('dado credenciales validas cuando se hace submit entonces llama a login con el usuario y contraseña correctos', async () => {
    mockLogin.mockResolvedValue(true);
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText('Usuario'), 'user_vendedor');
    await user.type(screen.getByLabelText('Contraseña'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user_vendedor', 'password123');
    });
    expect(screen.queryByText('Usuario o contraseña incorrectos')).not.toBeInTheDocument();
    expect(screen.queryByText('Por favor ingresa usuario y contraseña')).not.toBeInTheDocument();
  });

  it('dado credenciales invalidas cuando login falla entonces muestra un mensaje de error y no navega', async () => {
    mockLogin.mockResolvedValue(false);
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText('Usuario'), 'user_vendedor');
    await user.type(screen.getByLabelText('Contraseña'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(screen.getByText('Usuario o contraseña incorrectos')).toBeInTheDocument();
    });
    expect(mockLogin).toHaveBeenCalledWith('user_vendedor', 'wrong-password');
    expect(screen.getByLabelText('Usuario')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeInTheDocument();
  });

  it('dado un intento de login en curso cuando login esta pendiente entonces deshabilita el formulario', async () => {
    let resolveLogin: (value: boolean) => void = () => {};
    mockLogin.mockReturnValue(
      new Promise<boolean>((resolve) => {
        resolveLogin = resolve;
      })
    );
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText('Usuario'), 'user_vendedor');
    await user.type(screen.getByLabelText('Contraseña'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Ingresando...' })).toBeDisabled();
    });
    expect(screen.getByLabelText('Usuario')).toBeDisabled();
    expect(screen.getByLabelText('Contraseña')).toBeDisabled();

    resolveLogin(true);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Ingresar' })).toBeInTheDocument();
    });
  });

  it('dado el boton de mostrar contraseña cuando se hace clic entonces alterna el tipo del input', async () => {
    const user = userEvent.setup();
    renderLogin();

    const passwordInput = screen.getByLabelText('Contraseña');
    expect(passwordInput).toHaveAttribute('type', 'password');

    await user.click(screen.getByRole('button', { name: 'Mostrar contraseña' }));
    expect(passwordInput).toHaveAttribute('type', 'text');

    await user.click(screen.getByRole('button', { name: 'Ocultar contraseña' }));
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('dado el boton de credenciales de demo cuando se selecciona un usuario rapido entonces llama a login con esas credenciales', async () => {
    mockLogin.mockResolvedValue(true);
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole('button', { name: /Ver credenciales de demo/i }));
    await user.click(screen.getByRole('button', { name: /Vendedor:/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user_vendedor', 'password123');
    });
  });
});
