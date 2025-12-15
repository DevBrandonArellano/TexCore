import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../lib/auth';
import { InventoryForm } from './InventoryForm';
import { InventoryHistory } from './InventoryHistory';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';
import { Card, CardContent, CardHeader } from '../ui/card';

// Nuevo tipo que corresponde al MovimientoInventarioSerializer del backend
export interface Movimiento {
  id: number;
  fecha: string;
  tipo_movimiento: string;
  producto: string; // StringRelatedField
  lote: string | null; // StringRelatedField
  bodega_origen: string | null; // StringRelatedField
  bodega_destino: string | null; // StringRelatedField
  cantidad: string; // DecimalField se recibe como string
  documento_ref: string | null;
  usuario: string; // StringRelatedField
}

export function OperarioDashboard() {
  const { profile } = useAuth();
  const [movements, setMovements] = useState<Movimiento[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMovements = useCallback(async () => {
    if (!profile) return;
    setLoading(true);
    try {
      // Apuntar al nuevo endpoint, que ya filtra por usuario en el backend
      const response = await apiClient.get<Movimiento[]>('/inventory/movimientos/');
      setMovements(response.data);
    } catch (error) {
      console.error('Error fetching movements:', error);
      toast.error('Error al cargar el historial de movimientos');
    } finally {
      setLoading(false);
    }
  }, [profile]);

  useEffect(() => {
    fetchMovements();
  }, [fetchMovements]);

  const handleMovementCreated = (newMovement: Movimiento) => {
    // Re-fetch para obtener la lista más actualizada
    fetchMovements();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Panel de Operario</h1>
        <p className="text-muted-foreground">
          Registra movimientos de inventario y consulta tu historial.
        </p>
      </div>
      <div className="grid gap-8 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <InventoryForm onMovementCreated={handleMovementCreated} />
        </div>
        <div className="lg:col-span-3">
          {loading ? (
            <Card>
              <CardHeader>
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-64" />
              </CardHeader>
              <CardContent className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </CardContent>
            </Card>
          ) : (
            <InventoryHistory movements={movements} />
          )}
        </div>
      </div>
    </div>
  );
}