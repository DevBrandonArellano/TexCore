import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { AlertTriangle, PackageOpen } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { getApiErrorMessage } from '../../lib/apiError';
import { configuracionEmpaqueApi, type ConfiguracionEmpaque } from '../../lib/api/configuracionEmpaqueApi';

const MIN_JUSTIFICACION = 10;

interface ConfiguracionEmpaqueViewProps {
  /** Sede a configurar (Administrador de Sistemas). Sin ella, la del usuario. */
  sedeId?: string;
}

const aTexto = (valor: number | null) => (valor == null ? '' : String(valor));

/**
 * Equivalencias de empaque de la sede (TEX-43): 1 baño = N fundas, 1 funda = M conos.
 * Sin configuración, producción no puede convertir baños o fundas a conos (CA-3).
 */
export function ConfiguracionEmpaqueView({ sedeId }: ConfiguracionEmpaqueViewProps) {
  const [config, setConfig] = useState<ConfiguracionEmpaque | null>(null);
  const [fundas, setFundas] = useState('');
  const [conos, setConos] = useState('');
  const [justificacion, setJustificacion] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    let vigente = true;
    configuracionEmpaqueApi
      .obtener(sedeId)
      .then((datos) => {
        if (!vigente) return;
        setConfig(datos);
        setFundas(aTexto(datos.fundas_por_bano));
        setConos(aTexto(datos.conos_por_funda));
      })
      .catch((err) => {
        if (vigente) setError(getApiErrorMessage(err, 'No se pudo cargar la configuración de empaque.'));
      });
    return () => {
      vigente = false;
    };
  }, [sedeId]);

  const fundasNum = Number(fundas);
  const conosNum = Number(conos);
  const valido = Number.isInteger(fundasNum) && fundasNum >= 1 && Number.isInteger(conosNum) && conosNum >= 1;

  const guardar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valido) {
      setError('Las equivalencias deben ser números enteros mayores o iguales a 1.');
      return;
    }
    if (justificacion.trim().length < MIN_JUSTIFICACION) {
      setError(`La justificación debe tener al menos ${MIN_JUSTIFICACION} caracteres.`);
      return;
    }
    setError(null);
    setGuardando(true);
    try {
      const datos = await configuracionEmpaqueApi.guardar(
        { fundas_por_bano: fundasNum, conos_por_funda: conosNum, justificacion: justificacion.trim() }, sedeId);
      setConfig(datos);
      setJustificacion('');
      toast.success('Equivalencias de empaque guardadas.');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'No se pudieron guardar las equivalencias.'));
    } finally {
      setGuardando(false);
    }
  };

  if (!config && !error) {
    return <Skeleton className="h-48 w-full" />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PackageOpen className="w-5 h-5" /> Equivalencias de empaque{config ? ` — ${config.sede_nombre}` : ''}
        </CardTitle>
        <CardDescription>
          Cuántas fundas tiene un baño y cuántos conos tiene una funda en esta sede. Producción las usa para
          convertir los lotes registrados por baño o por funda.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {config && !config.configurada && (
          <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            La sede {config.sede_nombre} no tiene configuradas las equivalencias de empaque: hasta registrarlas,
            producción no puede registrar lotes por baño o funda.
          </div>
        )}
        {valido && (
          <p className="font-semibold">{`1 baño = ${fundasNum} fundas = ${fundasNum * conosNum} conos`}</p>
        )}
        <form onSubmit={guardar} className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="empaque-fundas">Fundas por baño</Label>
            <Input id="empaque-fundas" type="number" min={1} step={1} value={fundas}
              onChange={(e) => setFundas(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="empaque-conos">Conos por funda</Label>
            <Input id="empaque-conos" type="number" min={1} step={1} value={conos}
              onChange={(e) => setConos(e.target.value)} />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="empaque-justificacion">Justificación</Label>
            <Input id="empaque-justificacion" value={justificacion} placeholder="Motivo del cambio (queda en la auditoría)"
              onChange={(e) => setJustificacion(e.target.value)} />
          </div>
          {error && <p className="text-sm text-destructive sm:col-span-2">{error}</p>}
          <div className="sm:col-span-2">
            <Button type="submit" disabled={guardando}>Guardar equivalencias</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
