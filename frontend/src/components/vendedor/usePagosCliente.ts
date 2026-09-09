import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import type { Cliente, PagoCliente } from '../../lib/types';

const EMPTY_PAGO_FORM = {
  monto: '',
  metodo_pago: 'transferencia',
  comprobante: '',
  notas: '',
  es_anticipo: false
};

export function usePagosCliente(
  selectedCliente: Cliente | null,
  setSelectedCliente: (c: Cliente | null) => void,
  fetchData: () => void,
) {
  const [isPagoDialogOpen, setIsPagoDialogOpen] = useState(false);
  const [pagoForm, setPagoForm] = useState(EMPTY_PAGO_FORM);

  const [pagoRevertir, setPagoRevertir] = useState<PagoCliente | null>(null);
  const [pagoReversionJustificacion, setPagoReversionJustificacion] = useState('');
  const [pagoReversionLoading, setPagoReversionLoading] = useState(false);

  const handleCreatePago = async () => {
    if (!selectedCliente || !pagoForm.monto || parseFloat(pagoForm.monto) <= 0) {
      toast.error('Por favor ingresa un monto válido');
      return;
    }

    try {
      const pagoData = {
        cliente: selectedCliente.id,
        monto: parseFloat(pagoForm.monto),
        metodo_pago: pagoForm.metodo_pago,
        comprobante: pagoForm.comprobante,
        notas: pagoForm.notas,
        es_anticipo: pagoForm.es_anticipo
      };

      await apiClient.post('/pagos-cliente/', pagoData);
      toast.success(pagoForm.es_anticipo ? 'Anticipo registrado correctamente' : 'Pago registrado correctamente');
      setIsPagoDialogOpen(false);
      setPagoForm(EMPTY_PAGO_FORM);

      // Refresh selected client data to show new balance/payment
      const updatedClient = await apiClient.get(`/clientes/${selectedCliente.id}/`);
      setSelectedCliente(updatedClient.data);
      fetchData();
    } catch (error: any) {
      console.error('Error recording payment:', error);
      // El backend valida monto vs saldo: mostrar su mensaje (ej. sobrepago sin marca de anticipo)
      const backendMsg = error.response?.data?.monto || error.response?.data?.error?.fields?.monto;
      toast.error(Array.isArray(backendMsg) ? backendMsg[0] : (backendMsg || 'Error al registrar el pago'));
    }
  };

  const handleInitiatePagoReversion = (pago: PagoCliente) => {
    setPagoRevertir(pago);
    setPagoReversionJustificacion('');
  };

  const handleConfirmPagoReversion = async () => {
    if (!pagoRevertir || !pagoReversionJustificacion.trim()) {
      toast.error('Por favor ingresa una justificación válida');
      return;
    }

    setPagoReversionLoading(true);
    try {
      await apiClient.post(`/pagos-cliente/${pagoRevertir.id}/revertir/`, {
        justificacion: pagoReversionJustificacion.trim()
      });

      toast.success('Pago revertido correctamente. Deuda del cliente restaurada.');
      setPagoRevertir(null);
      setPagoReversionJustificacion('');

      // Refresh selected client data
      if (selectedCliente) {
        const updatedClient = await apiClient.get(`/clientes/${selectedCliente.id}/`);
        setSelectedCliente(updatedClient.data);
        fetchData();
      }
    } catch (error: any) {
      const msg = error?.response?.data?.error || error?.response?.data?.justificacion || 'Error al revertir el pago';
      toast.error(msg);
    } finally {
      setPagoReversionLoading(false);
    }
  };

  return {
    isPagoDialogOpen, setIsPagoDialogOpen,
    pagoForm, setPagoForm,
    handleCreatePago,
    pagoRevertir, setPagoRevertir,
    pagoReversionJustificacion, setPagoReversionJustificacion,
    pagoReversionLoading,
    handleInitiatePagoReversion,
    handleConfirmPagoReversion,
  };
}
