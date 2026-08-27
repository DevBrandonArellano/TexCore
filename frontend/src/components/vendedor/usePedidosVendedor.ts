import { useState, useMemo } from 'react';
import { toast } from 'sonner';
import apiClient from '../../lib/axios';
import { usePagination } from '../../hooks/usePagination';
import type { PedidoVenta } from '../../lib/types';
import { calculateItemsTotal } from './pedidoUtils';

const ITEMS_PER_PAGE = 20;

interface OrderItem {
  producto: string;
  cantidad: number;
  piezas: number;
  peso: number;
  precio_unitario: number;
  incluye_iva?: boolean;
}

const EMPTY_ORDER_FORM = {
  cliente: '',
  guia_remision: '',
  esta_pagado: false,
  aplica_retencion: false,
  valor_retencion: '0'
};

const EMPTY_NEW_ITEM = {
  producto: '',
  cantidad: 1,
  piezas: 1,
  peso: '',
  precio_unitario: '',
  incluye_iva: true
};

export function usePedidosVendedor(pedidos: PedidoVenta[], orderSearchTerm: string, fetchData: () => void) {
  const [isOrderDialogOpen, setIsOrderDialogOpen] = useState(false);
  const [orderForm, setOrderForm] = useState(EMPTY_ORDER_FORM);
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [newItem, setNewItem] = useState<{
    producto: string;
    cantidad: number;
    piezas: number;
    peso: string;
    precio_unitario: string;
    incluye_iva: boolean;
  }>(EMPTY_NEW_ITEM);

  const [pedidoAnular, setPedidoAnular] = useState<PedidoVenta | null>(null);
  const [pedidoEditar, setPedidoEditar] = useState<PedidoVenta | null>(null);
  const [pedidoHistorial, setPedidoHistorial] = useState<PedidoVenta | null>(null);

  const filteredPedidos = useMemo(() => {
    if (!Array.isArray(pedidos)) return [];
    return pedidos.filter(p =>
      p.cliente_nombre?.toLowerCase().includes(orderSearchTerm.toLowerCase()) ||
      p.guia_remision?.toLowerCase().includes(orderSearchTerm.toLowerCase())
    );
  }, [pedidos, orderSearchTerm]);

  const { currentPage: currentPedidosPage, setCurrentPage: setCurrentPedidosPage, totalPages: totalPedidosPages, paginatedItems: paginatedPedidos } =
    usePagination(filteredPedidos, ITEMS_PER_PAGE, { resetKey: orderSearchTerm });

  const addOrderItem = () => {
    const pesoVal = parseFloat(newItem.peso) || 0;
    const precioVal = parseFloat(newItem.precio_unitario) || 0;

    if (!newItem.producto || pesoVal <= 0 || precioVal <= 0) {
      toast.error('Por favor completa todos los campos del item');
      return;
    }
    setOrderItems([...orderItems, {
      ...newItem,
      peso: pesoVal,
      precio_unitario: precioVal
    }]);
    setNewItem(EMPTY_NEW_ITEM);
  };

  const removeOrderItem = (index: number) => {
    setOrderItems(orderItems.filter((_, i) => i !== index));
  };

  const calculateOrderTotal = () => calculateItemsTotal(orderItems);

  const resetOrderForm = () => {
    setOrderItems([]);
    setOrderForm(EMPTY_ORDER_FORM);
  };

  const handleCreateOrder = async () => {
    if (!orderForm.cliente || orderItems.length === 0) {
      toast.error('Por favor selecciona un cliente y añade al menos un producto');
      return;
    }

    const retencionNum = parseFloat(orderForm.valor_retencion) || 0;
    if (orderForm.aplica_retencion && retencionNum < 0) {
      toast.error('El valor de retención no puede ser negativo');
      return;
    }

    const totalCalculado = calculateOrderTotal();
    if (orderForm.aplica_retencion && retencionNum > totalCalculado) {
      toast.error('El valor de retención no puede superar el total de la factura');
      return;
    }

    try {
      // Map frontend expected format into API exactly
      // Notice the API actually does the IVA logic if its enabled, but just for payload:
      const orderData = {
        ...orderForm,
        cliente: parseInt(orderForm.cliente),
        detalles: orderItems,
        // Agregamos la retención al payload si el backend lo soporta,
        // o lo podemos tratar como un pago automático inmediato por ese monto,
        // dependiendo de la implementación de Django. Por ahora lo pasamos.
        valor_retencion: orderForm.aplica_retencion ? retencionNum : 0
      };

      await apiClient.post('/pedidos-venta/', orderData);
      toast.success('Pedido creado correctamente');
      setIsOrderDialogOpen(false);
      resetOrderForm();
      fetchData();
    } catch (error: any) {
      console.error('Error saving order:', error);
      const errorMsg = error.response?.data?.cliente || error.response?.data?.detail || 'Error al guardar el pedido';
      toast.error(errorMsg);
    }
  };

  const handlePrintOrder = async (pedido: PedidoVenta) => {
    try {
      const response = await apiClient.get(`/pedidos-venta/${pedido.id}/download_pdf/`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pedido_${pedido.guia_remision || pedido.id}.pdf`);
      document.body.appendChild(link);
      link.click();

      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);

    } catch (error) {
      console.error("Error downloading PDF", error);
      toast.error("Error al descargar el PDF de la nota de venta.");
    }
  };

  return {
    isOrderDialogOpen, setIsOrderDialogOpen,
    orderForm, setOrderForm,
    orderItems,
    newItem, setNewItem,
    resetOrderForm,
    pedidoAnular, setPedidoAnular,
    pedidoEditar, setPedidoEditar,
    pedidoHistorial, setPedidoHistorial,
    filteredPedidos, paginatedPedidos,
    currentPedidosPage, setCurrentPedidosPage, totalPedidosPages,
    addOrderItem,
    removeOrderItem,
    calculateOrderTotal,
    handleCreateOrder,
    handlePrintOrder,
  };
}
