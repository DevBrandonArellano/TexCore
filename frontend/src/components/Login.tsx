import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { useAuth } from '../lib/auth';
import { Package, AlertCircle, Eye, EyeOff } from 'lucide-react';

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

              <div className="space-y-2 relative">
                <Label htmlFor="password">Contraseña</Label>
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Ingresa tu contraseña"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  disabled={isLoading}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute top-1/2 right-2 -translate-y-0.5 h-7 w-7 text-muted-foreground"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
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
                <div className="mt-4 p-4 bg-muted rounded-lg space-y-2">
                  <p className="text-sm text-muted-foreground mb-3">Haz clic para acceder:</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => quickLogin('user_operario', 'password123')}
                    disabled={isLoading}
                  >
                    <span className="font-medium mr-2">Operario:</span> user_operario
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => quickLogin('user_jefe_area', 'password123')}
                    disabled={isLoading}
                  >
                    <span className="font-medium mr-2">Jefe de Área:</span> user_jefe_area
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => quickLogin('user_jefe_planta', 'password123')}
                    disabled={isLoading}
                  >
                    <span className="font-medium mr-2">Jefe de Planta:</span> user_jefe_planta
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => quickLogin('user_admin_sede', 'password123')}
                    disabled={isLoading}
                  >
                    <span className="font-medium mr-2">Admin Sede:</span> user_admin_sede
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => quickLogin('user_ejecutivo', 'password123')}
                    disabled={isLoading}
                  >
                    <span className="font-medium mr-2">Ejecutivo:</span> user_ejecutivo
                  </Button>
                   <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => quickLogin('user_admin_sistemas', 'password123')}
                    disabled={isLoading}
                  >
                    <span className="font-medium mr-2">Admin Sistemas:</span> user_admin_sistemas
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start"
                    onClick={() => quickLogin('admin', 'admin')}
                    disabled={isLoading}
                  >
                    <span className="font-medium mr-2">Super Admin:</span> admin
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
