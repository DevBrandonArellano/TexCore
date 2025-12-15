import React from 'react';
import { useAuth } from '../lib/auth';
import { Button } from './ui/button';
import { LogOut, Package } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Avatar, AvatarFallback } from './ui/avatar';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { profile, logout } = useAuth();

  if (!profile) return null;

  const { user } = profile;

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      operario: 'Operario',
      jefe_area: 'Jefe de Área',
      jefe_planta: 'Jefe de Planta',
      admin_sede: 'Administrador de Sede',
      ejecutivo: 'Ejecutivo',
      admin_sistemas: 'Administrador de Sistemas'
    };
    return labels[role] || role;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 bg-primary rounded-lg">
              <Package className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-primary">TexCore</h2>
              <p className="text-xs text-muted-foreground">{getRoleLabel(profile.role || '')}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Botón de Cerrar Sesión visible en desktop */}
            <Button 
              variant="outline" 
              className="hidden sm:flex items-center gap-2"
              onClick={logout}
            >
              <LogOut className="h-4 w-4" />
              <span>Cerrar Sesión</span>
            </Button>

            {/* Menu de usuario (visible siempre) */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                  <Avatar>
                    <AvatarFallback>{getInitials(user.first_name)}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p>{user.first_name} {user.last_name}</p>
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Cerrar Sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6 md:py-8">
        {children}
      </main>
    </div>
  );
}
