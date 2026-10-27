import { Download, Loader2, type LucideIcon } from 'lucide-react';
import { cn } from './utils';

interface IconoCargaProps {
  cargando: boolean;
  /** Ícono en reposo (por defecto, descarga). */
  icono?: LucideIcon;
  className?: string;
}

/**
 * Ícono de un botón de acción que gira mientras la acción está en curso, para que el
 * usuario sepa que el clic se registró. Va acompañado de `aria-busy` en el botón.
 */
export function IconoCarga({ cargando, icono: Icono = Download, className = 'w-4 h-4' }: IconoCargaProps) {
  if (cargando) {
    return <Loader2 data-testid="icono-cargando" aria-hidden="true" className={cn(className, 'animate-spin')} />;
  }
  return <Icono aria-hidden="true" className={className} />;
}
