import { useState, useMemo } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { usePagination } from '../../hooks/usePagination';
import type { Cliente } from '../../lib/types';
import { datosDeError } from '../../lib/apiError';

const ITEMS_PER_PAGE = 20;

const EMPTY_CLIENTE_FORM = {
  ruc_cedula: '',
  nombre_razon_social: '',
  direccion_envio: '',
  nivel_precio: 'normal' as 'normal' | 'mayorista',
  tiene_beneficio: false,
  saldo_pendiente: '0.000',
  limite_credito: '0.000',
  plazo_credito_dias: 0,
  cartera_vencida: '0.000',
  _justificacion_auditoria: ''
};

export function useClientesVendedor(clientes: Cliente[], searchTerm: string, fetchData: () => void) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingCliente, setEditingCliente] = useState<Cliente | null>(null);
  const [formData, setFormData] = useState(EMPTY_CLIENTE_FORM);

  const [selectedCliente, setSelectedCliente] = useState<Cliente | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const filteredClientes = useMemo(() => {
    if (!Array.isArray(clientes)) return [];
    return clientes.filter(c =>
      c.nombre_razon_social.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.ruc_cedula.includes(searchTerm)
    );
  }, [clientes, searchTerm]);

  const { currentPage: currentClientesPage, setCurrentPage: setCurrentClientesPage, totalPages: totalClientesPages, paginatedItems: paginatedClientes } =
    usePagination(filteredClientes, ITEMS_PER_PAGE, { resetKey: searchTerm });

  const resetClienteForm = () => {
    setEditingCliente(null);
    setFormData(EMPTY_CLIENTE_FORM);
  };

  const handleCreateOrUpdateCliente = async () => {
    try {
      // El saldo y la cartera los calcula el servidor; la justificación solo aplica al editar.
      const { saldo_pendiente: _saldo, cartera_vencida: _cartera, _justificacion_auditoria, ...datosCliente } = formData;
      const datosNumericos = {
        ...datosCliente,
        limite_credito: parseFloat(formData.limite_credito),
        plazo_credito_dias: parseInt(String(formData.plazo_credito_dias)),
      };

      if (editingCliente) {
        await apiClient.put(`/clientes/${editingCliente.id}/`, { ...datosNumericos, _justificacion_auditoria });
        toast.success('Cliente actualizado correctamente');
      } else {
        await apiClient.post('/clientes/', datosNumericos);
        toast.success('Cliente registrado correctamente');
      }
      setIsDialogOpen(false);
      resetClienteForm();
      fetchData();
    } catch (error) {
      console.error('Error saving cliente:', error);
      const data = datosDeError(error) as Record<string, unknown> | string | undefined;
      if (data) {
        if (typeof data === 'object' && typeof data.detail === 'string') {
          toast.error(data.detail);
        } else if (typeof data === 'object') {
          const messages = Object.entries(data).map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`).join('\\n');
          toast.error('Error de validación', { description: messages || 'Revisa los campos enviados.' });
        } else {
          toast.error('Error al guardar el cliente');
        }
      } else {
        toast.error('Error de conexión o servidor al guardar el cliente');
      }
    }
  };

  const openEditDialog = (cliente: Cliente) => {
    setEditingCliente(cliente);
    setFormData({
      ruc_cedula: cliente.ruc_cedula,
      nombre_razon_social: cliente.nombre_razon_social,
      direccion_envio: cliente.direccion_envio,
      nivel_precio: cliente.nivel_precio,
      tiene_beneficio: cliente.tiene_beneficio,
      saldo_pendiente: cliente.saldo_pendiente.toString(),
      limite_credito: cliente.limite_credito.toString(),
      plazo_credito_dias: cliente.plazo_credito_dias || 0,
      cartera_vencida: cliente.cartera_vencida?.toString() || '0.000',
      _justificacion_auditoria: ''
    });
    setIsDialogOpen(true);
  };

  const handleInactivarCliente = async (cliente: Cliente) => {
    if (!window.confirm(`¿Estás seguro de que deseas inactivar al cliente ${cliente.nombre_razon_social}?`)) {
      return;
    }

    try {
      await apiClient.patch(`/clientes/${cliente.id}/`, {
        is_active: false,
        _justificacion_auditoria: 'Inactivación del cliente desde el panel comercial'
      });
      toast.success('Cliente inactivado correctamente');
      fetchData();
    } catch (error) {
      console.error('Error inactivating cliente:', error);
      toast.error('Error al inactivar el cliente');
    }
  };

  const openClienteDetail = async (cliente: Cliente) => {
    try {
      // Fetch the detailed client object that includes the `pedidos` and `pagos` arrays which are omitted in list views
      const res = await apiClient.get(`/clientes/${cliente.id}/`);
      setSelectedCliente(res.data);
    } catch (e) {
      console.error("Error fetching client details", e);
      setSelectedCliente(cliente); // Fallback
    }
    setIsDetailOpen(true);
  };

  return {
    isDialogOpen, setIsDialogOpen,
    editingCliente,
    formData, setFormData,
    resetClienteForm,
    selectedCliente, setSelectedCliente,
    isDetailOpen, setIsDetailOpen,
    filteredClientes, paginatedClientes,
    currentClientesPage, setCurrentClientesPage, totalClientesPages,
    handleCreateOrUpdateCliente,
    openEditDialog,
    handleInactivarCliente,
    openClienteDetail,
  };
}
