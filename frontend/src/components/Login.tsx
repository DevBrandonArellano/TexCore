import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { useAuth } from '../lib/auth';
import { Package, AlertCircle, Eye, EyeOff } from 'lucide-react';

const DEMO_USERS: Array<{ label: string; user: string; pass: string }> = [
  { label: 'Operario', user: 'user_operario', pass: 'password123' },
  { label: 'Bodeguero', user: 'user_bodeguero', pass: 'password123' },
  { label: 'Vendedor', user: 'user_vendedor', pass: 'password123' },
  { label: 'Jefe de Área', user: 'user_jefe_area', pass: 'password123' },
  { label: 'Jefe de Planta', user: 'user_jefe_planta', pass: 'password123' },
  { label: 'Admin Sede', user: 'user_admin_sede', pass: 'password123' },
  { label: 'Ejecutivo', user: 'user_ejecutivo', pass: 'password123' },
  { label: 'Admin Sistemas', user: 'user_admin_sistemas', pass: 'password123' },
  { label: 'Empaquetador', user: 'user_empaquetado', pass: 'password123' },
  { label: 'Despacho', user: 'user_despacho', pass: 'password123' },
  { label: 'Tintorero', user: 'user_tintorero', pass: 'password123' },
  { label: 'Super Admin', user: 'admin', pass: 'admin' },
];

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showCredentials, setShowCredentials] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (!username || !password) {
      setError('Por favor ingresa usuario y contraseña');
      setIsLoading(false);
      return;
    }

    const success = await login(username, password);
    if (!success) {
      setError('Usuario o contraseña incorrectos');
    }
    // If login is successful, the component will unmount, so no need to set loading to false.
    // If it fails, we set it to false to allow another attempt.
    setIsLoading(false);
  };

  const quickLogin = async (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setIsLoading(true);
    const success = await login(user, pass);
    if (!success) {
      setError('Usuario o contraseña incorrectos');
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-xl mb-4">
            <Package className="w-8 h-8 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-bold text-primary mb-2">TexCore</h1>
          <p className="text-muted-foreground">Sistema de Gestión de Inventarios</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Iniciar Sesión</CardTitle>
            <CardDescription>Ingresa tus credenciales para acceder al sistema</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Usuario</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Ingresa tu usuario"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Contraseña</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Ingresa tu contraseña"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7 text-muted-foreground"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={isLoading}
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Ingresando...' : 'Ingresar'}
              </Button>
            </form>

            <div className="mt-6">
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => setShowCredentials(!showCredentials)}
                disabled={isLoading}
              >
                {showCredentials ? 'Ocultar' : 'Ver'} credenciales de demo
              </Button>

              {showCredentials && (
                <div className="mt-4 p-4 bg-muted rounded-lg space-y-2 max-h-60 overflow-y-auto">
                  <p className="text-sm text-muted-foreground mb-3">Haz clic para acceder:</p>
                  {DEMO_USERS.map((demo) => (
                    <Button
                      key={demo.user}
                      variant="outline"
                      size="sm"
                      className="w-full justify-start"
                      onClick={() => quickLogin(demo.user, demo.pass)}
                      disabled={isLoading}
                    >
                      <span className="font-medium mr-2">{demo.label}:</span> {demo.user}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
