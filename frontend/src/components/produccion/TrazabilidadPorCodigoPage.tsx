import React from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../../lib/axios';
import { Trazabilidad } from '../../types/produccion';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { NivelTrazabilidad } from './TrazabilidadProducto';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { estadoHttp } from '../../lib/apiError';

/**
 * Página destino del QR impreso en la etiqueta de un lote (escaneada desde la
 * red interna, ver nginx.conf `location /trazabilidad`). El guard de sesión ya
 * lo resuelve AppContent (App.tsx): si no hay sesión, se muestra Login antes
 * de llegar aquí; tras iniciar sesión, el usuario vuelve a esta misma URL.
 */
export function TrazabilidadPorCodigoPage() {
  const { codigo } = useParams<{ codigo: string }>();
  const { datos: traza, cargando, error } = useCargaRemota(
    () => apiClient.get<Trazabilidad>(`/trazabilidad-lote/${codigo}/`).then(({ data }) => data),
    codigo,
    {
      habilitado: Boolean(codigo),
      mensajeDeError: (err) =>
        estadoHttp(err) === 404
          ? `No se encontró ningún lote con el código "${codigo}".`
          : 'No se pudo cargar la trazabilidad de este lote.',
    },
  );

  return (
    <div className="mx-auto max-w-3xl space-y-3 p-4">
      <Card>
        <CardHeader>
          <CardTitle>Trazabilidad del lote {codigo}</CardTitle>
          <CardDescription>Consulta generada al escanear la etiqueta.</CardDescription>
        </CardHeader>
        <CardContent>
          {cargando && <p className="text-sm text-muted-foreground">Cargando trazabilidad…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>
      {!cargando && !error && traza && <NivelTrazabilidad nivel={traza} esRaiz />}
    </div>
  );
}

export default TrazabilidadPorCodigoPage;
