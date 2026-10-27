/**
 * Aviso de progreso de una exportación: un solo toast que nace al hacer clic
 * ("Generando reporte…"), avisa si la espera se alarga, pasa a "Descargando
 * archivo…" y termina en éxito, advertencia o error en el mismo lugar, sin apilar
 * avisos. Complementa el spinner del botón (components/ui/icono-carga.tsx).
 */
import { toast } from 'sonner';
import type { AvanceReporte } from './reporteAsync';

const ESPERA_LARGA_SEGUNDOS = 10;

export function iniciarAvisoReporte() {
  const id = toast.loading('Generando reporte…', { description: 'La descarga empezará automáticamente.' });
  let avisoEsperaLarga = false;

  const cerrar = (mostrar: typeof toast.success, mensaje: string) =>
    mostrar(mensaje, { id, description: undefined });

  return {
    avance({ fase, segundos }: AvanceReporte) {
      if (fase === 'descargando') {
        toast.loading('Descargando archivo…', { id, description: undefined });
      } else if (segundos >= ESPERA_LARGA_SEGUNDOS && !avisoEsperaLarga) {
        avisoEsperaLarga = true;
        toast.loading('Generando reporte…', { id, description: 'Es un reporte grande, puede tardar un poco más.' });
      }
    },
    exito: (mensaje: string) => cerrar(toast.success, mensaje),
    advertencia: (mensaje: string) => cerrar(toast.warning, mensaje),
    error: (mensaje: string) => cerrar(toast.error, mensaje),
  };
}
