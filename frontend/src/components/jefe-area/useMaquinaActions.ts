import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { Maquina } from '../../lib/types';

export function useMaquinaActions(fetchDashboardData: () => void) {
  const [isMaquinaDialogOpen, setIsMaquinaDialogOpen] = useState(false);
  const [selectedMaquina, setSelectedMaquina] = useState<Partial<Maquina> | null>(null);

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

  const handleRechazarLote = async (loteId: number) => {
    // El backend exige `justificacion` no vacía (ISO 9001: causa del rechazo
    // trazable). Pedimos el motivo y lo enviamos; sin motivo se aborta.
    //
    // NOTA: el plan de refactor (docs/superpowers/plans/2026-08-21-division-dashboards-frontend.md,
    // Fase 4) pedía homologar window.alert/window.prompt a toast aquí. Se dejó
    // window.alert/window.prompt tal cual porque JefeAreaDashboard.test.tsx
    // (3 tests, líneas 686-742) hace `vi.spyOn(window, 'alert')` y asserta los
    // mensajes exactos vía window.alert — cambiar a toast rompería esos tests
    // sin que el plan lo contemplara. Cero cambios de comportamiento tiene
    // prioridad sobre este fix cosmético; queda pendiente de decisión explícita.
    const motivo = window.prompt(
      "Motivo del rechazo del lote (requerido). Esta acción revertirá los movimientos de inventario:"
    );
    if (motivo === null) return; // el usuario canceló
    if (!motivo.trim()) {
      window.alert("Debes indicar un motivo para rechazar el lote.");
      return;
    }

    try {
      await apiClient.post(`/lotes-produccion/${loteId}/rechazar/`, { justificacion: motivo.trim() });
      window.alert("Lote rechazado y movimientos revertidos.");
      fetchDashboardData(); // Refresh
    } catch (error) {
      console.error("Error rechazando lote", error);
      window.alert("Error al rechazar el lote.");
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
