import React, { useCallback, useEffect, useState } from 'react';
import apiClient from '../../lib/axios';
import { Maquina, Producto } from '../../lib/types';
import { Trazabilidad } from '../../types/produccion';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ArrowRight, ArrowDown, Cog, TrendingDown, PlusCircle, RefreshCw } from 'lucide-react';
import { RegistrarTransformacion } from './RegistrarTransformacion';

/**
 * Reporte/timeline de trazabilidad de una OP: muestra el flujo máquina a máquina
 * (cambio de código + merma por paso) y, encadenado, el recorrido por las
 * siguientes áreas vía las transferencias interárea.
 */
interface TrazabilidadProductoProps {
  ordenId: number;
  /** Permite registrar transformaciones desde el propio timeline (Jefe de Área / Operario). */
  allowRegister?: boolean;
}

export function NivelTrazabilidad({ nivel, esRaiz }: { nivel: Trazabilidad; esRaiz?: boolean }) {
  const pct = parseFloat(nivel.merma_porcentaje);
  return (
    <div className="space-y-3">
      <Card className={esRaiz ? 'border-primary/40' : ''}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <CardTitle className="text-base flex items-center gap-2">
              <Badge variant="secondary" className="font-mono">{nivel.orden_codigo}</Badge>
              {nivel.area && <span className="text-muted-foreground">· {nivel.area}</span>}
            </CardTitle>
            <Badge variant={pct > 10 ? 'destructive' : 'outline'} className="flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              Merma {nivel.merma_total} kg ({nivel.merma_porcentaje}%)
            </Badge>
          </div>
          <CardDescription className="flex items-center gap-2 flex-wrap pt-1">
            <span className="font-mono">{nivel.producto_inicial?.codigo ?? '—'}</span>
            <ArrowRight className="h-3 w-3" />
            <span className="font-mono">{nivel.producto_final?.codigo ?? '—'}</span>
            <span className="text-xs">({nivel.peso_inicial} kg → {nivel.peso_final} kg)</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {(!nivel.pasos || nivel.pasos.length === 0) && (
            <p className="text-sm text-muted-foreground italic">Sin transformaciones registradas todavía.</p>
          )}
          {nivel.pasos?.map((paso) => (
            <div
              key={paso.numero_secuencia}
              className="flex items-center gap-3 rounded-md border p-2 text-sm"
            >
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-xs">
                {paso.numero_secuencia}
              </div>
              <Cog className="h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono">{paso.producto_entrada?.codigo ?? '—'}</span>
                  <ArrowRight className="h-3 w-3" />
                  <span className="font-mono font-medium">{paso.producto_salida?.codigo ?? '—'}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {paso.maquina ?? 'Máquina N/D'}
                  {paso.operario ? ` · ${paso.operario}` : ''}
                  {` · ${paso.peso_entrada} → ${paso.peso_salida} kg`}
                </div>
              </div>
              <Badge
                variant={paso.estado === 'rechazada' ? 'destructive' : 'outline'}
                className="shrink-0"
              >
                −{paso.merma} kg
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      {nivel.siguiente && (
        <>
          <div className="flex justify-center text-muted-foreground">
            <ArrowDown className="h-5 w-5" />
          </div>
          <NivelTrazabilidad nivel={nivel.siguiente} />
        </>
      )}
    </div>
  );
}

export function TrazabilidadProducto({ ordenId, allowRegister = false }: TrazabilidadProductoProps) {
  const [traza, setTraza] = useState<Trazabilidad | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { data } = await apiClient.get<Trazabilidad>(`/ordenes-produccion/${ordenId}/trazabilidad/`);
      setTraza(data);
    } catch {
      setError('No se pudo cargar la trazabilidad de la orden.');
    } finally {
      setCargando(false);
    }
  }, [ordenId]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  useEffect(() => {
    if (!allowRegister) return;
    Promise.all([
      apiClient.get<Maquina[]>('/maquinas/'),
      apiClient.get('/productos/'),
    ])
      .then(([m, p]) => {
        setMaquinas(m.data);
        const prods = (p.data?.results ?? p.data) as Producto[];
        setProductos(prods);
      })
      .catch(() => { /* el diálogo simplemente quedará sin opciones */ });
  }, [allowRegister]);

  // El próximo producto de entrada = última salida, o producto inicial de la OP.
  const pasos = traza?.pasos ?? [];
  const entradaEsperada = traza
    ? (pasos.length > 0
        ? pasos[pasos.length - 1].producto_salida?.codigo
        : traza.producto_inicial?.codigo) ?? null
    : null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <CardTitle>Trazabilidad del Producto</CardTitle>
            <CardDescription>Flujo de transformaciones máquina a máquina y entre áreas.</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={cargar} disabled={cargando}>
              <RefreshCw className="mr-1 h-4 w-4" /> Actualizar
            </Button>
            {allowRegister && (
              <Button size="sm" onClick={() => setDialogOpen(true)}>
                <PlusCircle className="mr-1 h-4 w-4" /> Registrar transformación
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {cargando && <p className="text-sm text-muted-foreground">Cargando trazabilidad…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!cargando && !error && traza && <NivelTrazabilidad nivel={traza} esRaiz />}
      </CardContent>

      {allowRegister && (
        <RegistrarTransformacion
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          ordenId={ordenId}
          maquinas={maquinas}
          productos={productos}
          entradaEsperada={entradaEsperada}
          onSuccess={cargar}
        />
      )}
    </Card>
  );
}

export default TrazabilidadProducto;
