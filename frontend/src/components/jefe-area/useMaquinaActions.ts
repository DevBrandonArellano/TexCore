import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { getApiErrorMessage } from '../../lib/apiError';
import type { Maquina } from '../../lib/types';

export function useMaquinaActions(fetchDashboardData: () => void) {
  const [isMaquinaDialogOpen, setIsMaquinaDialogOpen] = useState(false);
  const [selectedMaquina, setSelectedMaquina] = useState<Maquina | null>(null);

  const handleEditMaquina = (maquina: Maquina) => {
    setSelectedMaquina(maquina);
    setIsMaquinaDialogOpen(true);
  };

  const handleToggleEstadoMaquina = async (maquina: Maquina) => {
    const nuevoEstado = maquina.estado === 'operativa' ? 'inactiva' : 'operativa';
    try {
      await apiClient.patch(`/maquinas/${maquina.id}/`, { estado: nuevoEstado });
      toast.success(`Máquina ${maquina.nombre} ahora está ${nuevoEstado}.`);
      fetchDashboardData();
    } catch (error) {
      toast.error("Error al cambiar el estado de la máquina.");
    }
  };

  /** El backend exige `justificacion` (ISO 9001: causa del rechazo trazable);
   * RechazarLoteDialog no deja confirmar sin motivo. Devuelve si se rechazó. */
  const handleRechazarLote = async (loteId: number, motivo: string): Promise<boolean> => {
    try {
      await apiClient.post(`/lotes-produccion/${loteId}/rechazar/`, { justificacion: motivo.trim() });
      toast.success("Lote rechazado y movimientos revertidos.");
      fetchDashboardData();
      return true;
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Error al rechazar el lote."));
      return false;
    }
  };

  return {
    isMaquinaDialogOpen,
    setIsMaquinaDialogOpen,
    selectedMaquina,
    setSelectedMaquina,
    handleEditMaquina,
    handleToggleEstadoMaquina,
    handleRechazarLote,
  };
}
