import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { AlertCircle, CheckCircle2, Clock, Zap, Package, ArrowDown } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';

interface Etapa {
  id: number;
  area: number;
  nombre: string;
  orden: number;
  maquina: { nombre: string };
  bodega_entrada: { nombre: string };
  bodega_salida: { nombre: string };
}

interface OrdenProduccion {
  id: number;
  codigo: string;
  estado: string;
  area: { id: number; nombre: string };
  peso_neto_requerido: number;
  producto_entrada?: { descripcion: string };
  lotes?: { codigo_lote: string; peso_neto_producido: number }[];
}

export function FlujoProduccion() {
  const [ordenes, setOrdenes] = useState<OrdenProduccion[]>([]);
  const [etapasPorArea, setEtapasPorArea] = useState<Map<number, Etapa[]>>(new Map());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [ordenesRes, etapasRes] = await Promise.all([
        apiClient.get('/ordenes-produccion/'),
        apiClient.get('/etapas-produccion/')
      ]);

      const allOrdenes = ordenesRes.data.results || ordenesRes.data;
      setOrdenes(allOrdenes.slice(0, 10)); // Últimas 10 órdenes

      const allEtapas = etapasRes.data.results || etapasRes.data;
      const etapaMap = new Map<number, Etapa[]>();
      allEtapas.forEach((etapa: Etapa) => {
        if (!etapaMap.has(etapa.area)) {
          etapaMap.set(etapa.area, []);
        }
        etapaMap.get(etapa.area)!.push(etapa);
      });
      setEtapasPorArea(etapaMap);
    } catch (error) {
      toast.error('Error al cargar flujo de producción');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const getEstadoColor = (estado: string) => {
    switch (estado) {
      case 'pendiente': return 'bg-gray-100 text-gray-800 border-gray-300';
      case 'en_proceso': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'finalizada': return 'bg-green-100 text-green-800 border-green-300';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getEstadoIcon = (estado: string) => {
    switch (estado) {
      case 'pendiente': return <Clock className="w-4 h-4" />;
      case 'en_proceso': return <Zap className="w-4 h-4" />;
      case 'finalizada': return <CheckCircle2 className="w-4 h-4" />;
      default: return null;
    }
  };

  if (loading) {
    return <div className="text-center py-8">Cargando flujo...</div>;
  }

  return (
    <div className="space-y-6">
      <Card className="border-2 border-purple-200">
        <CardHeader>
          <CardTitle className="text-lg">Flujo de Producción General</CardTitle>
        </CardHeader>
        <CardContent className="space-y-8">
          {ordenes.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No hay órdenes de producción</p>
            </div>
          ) : (
            ordenes.map((orden, idx) => (
              <div key={orden.id} className="relative">
                {/* Header de la Orden */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <h3 className="font-bold text-lg">{orden.codigo}</h3>
                      <Badge className={`${getEstadoColor(orden.estado)} border`}>
                        {getEstadoIcon(orden.estado)}
                        <span className="ml-1">{orden.estado.toUpperCase()}</span>
                      </Badge>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">{orden.area.nombre}</p>
                      <p className="text-sm text-gray-600">
                        {orden.producto_entrada?.descripcion}
                      </p>
                    </div>
                  </div>

                  {/* Progreso de Peso */}
                  <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-purple-600 h-full transition-all"
                      style={{
                        width: `${Math.min(
                          ((orden.lotes?.reduce((sum, l) => sum + l.peso_neto_producido, 0) || 0) /
                            orden.peso_neto_requerido) * 100,
                          100
                        )}%`
                      }}
                    />
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {orden.lotes?.reduce((sum, l) => sum + l.peso_neto_producido, 0) || 0} / {orden.peso_neto_requerido} kg
                  </p>
                </div>

                {/* Etapas de la Orden */}
                {etapasPorArea.has(orden.area.id) && (
                  <div className="ml-8">
                    <div className="border-l-2 border-dashed border-gray-300 pl-6 space-y-4">
                      {Array.from(etapasPorArea.get(orden.area.id) || [])
                        .sort((a, b) => a.orden - b.orden)
                        .map((etapa, etapaIdx) => (
                          <div key={etapa.id} className="relative">
                            <div className="absolute -left-9 top-1 w-4 h-4 bg-white border-2 border-purple-400 rounded-full" />

                            <div className="bg-gradient-to-r from-purple-50 to-transparent border border-purple-200 rounded p-3">
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-semibold text-gray-900">
                                  {etapa.orden}. {etapa.nombre}
                                </h4>
                                <span className="text-xs font-mono text-gray-500">
                                  {etapa.maquina.nombre}
                                </span>
                              </div>

                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="bg-green-50 rounded px-2 py-1 border border-green-200">
                                  <p className="text-gray-600">Entrada</p>
                                  <p className="font-medium text-green-700 text-xs">
                                    {etapa.bodega_entrada.nombre}
                                  </p>
                                </div>
                                <div className="bg-orange-50 rounded px-2 py-1 border border-orange-200">
                                  <p className="text-gray-600">Salida</p>
                                  <p className="font-medium text-orange-700 text-xs">
                                    {etapa.bodega_salida.nombre}
                                  </p>
                                </div>
                              </div>
                            </div>

                            {etapaIdx < (etapasPorArea.get(orden.area.id) || []).length - 1 && (
                              <div className="flex justify-center py-1">
                                <ArrowDown className="w-4 h-4 text-purple-400" />
                              </div>
                            )}
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {idx < ordenes.length - 1 && (
                  <div className="my-6 border-t-2 border-dotted border-gray-300" />
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
