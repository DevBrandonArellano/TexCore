import { useState, useMemo } from 'react';
import type { Cliente, PedidoVenta } from '../../lib/types';
import { abreviar, toNum } from './utils';

const getPedidoTotal = (p: PedidoVenta) =>
  toNum(p.total) || (p.detalles?.reduce(
    (s: number, d: any) => s + toNum(d.peso) * toNum(d.precio_unitario), 0
  ) ?? 0);

export function useVentasEjecutivo() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
  const [modalEstadoPedido, setModalEstadoPedido] = useState<string | null>(null);
  const [modalVendedor, setModalVendedor] = useState<string | null>(null);
  const [modalClienteCompras, setModalClienteCompras] = useState<string | null>(null);
  const [modalClienteDeudor, setModalClienteDeudor] = useState<string | null>(null);

  const ventasPorVendedor = useMemo(() => {
    const map = new Map<string, number>();
    pedidos.forEach((p) => {
      const v = (p as any).vendedor_nombre || 'Sin asignar';
      map.set(v, (map.get(v) ?? 0) + getPedidoTotal(p));
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name: abreviar(name, 18), fullName: name, value: Math.round(value * 100) / 100 }))
      .sort((a, b) => b.value - a.value).slice(0, 10);
  }, [pedidos]);

  const topClientesGerencial = useMemo(() => {
    const map = new Map<string, number>();
    pedidos.forEach((p) => {
      const c = (p as any).cliente_nombre || 'Sin nombre';
      map.set(c, (map.get(c) ?? 0) + getPedidoTotal(p));
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name: abreviar(name), fullName: name, value: Math.round(value * 100) / 100 }))
      .sort((a, b) => b.value - a.value).slice(0, 8);
  }, [pedidos]);

  const topDeudores = useMemo(() =>
    clientes
      .map(c => ({ name: abreviar(c.nombre_razon_social), fullName: c.nombre_razon_social, deuda: toNum(c.saldo_pendiente), obj: c }))
      .filter(c => c.deuda > 0)
      .sort((a, b) => b.deuda - a.deuda).slice(0, 8),
    [clientes]);

  const distribucionPago = useMemo(() => {
    let pagado = 0, pendiente = 0;
    pedidos.forEach((p) => {
      const t = getPedidoTotal(p);
      if (p.esta_pagado) pagado += t; else pendiente += t;
    });
    return [
      { name: 'Pagado', value: Math.round(pagado * 100) / 100, color: '#10b981' },
      { name: 'Pendiente', value: Math.round(pendiente * 100) / 100, color: '#f59e0b' },
    ].filter(d => d.value > 0);
  }, [pedidos]);

  const funnelData = useMemo(() => {
    const counts = { pendiente: 0, despachado_parcial: 0, despachado: 0, facturado: 0 };
    pedidos.forEach(p => { if (counts[p.estado] !== undefined) counts[p.estado]++; });
    return [
      { estado: 'Pendientes', key: 'pendiente', total: counts.pendiente, fill: '#f59e0b' },
      { estado: 'Parciales', key: 'despachado_parcial', total: counts.despachado_parcial, fill: '#f97316' },
      { estado: 'Despachados', key: 'despachado', total: counts.despachado, fill: '#3b82f6' },
      { estado: 'Facturados', key: 'facturado', total: counts.facturado, fill: '#10b981' },
    ];
  }, [pedidos]);

  const totalVentas = useMemo(() => pedidos.reduce((a, p) => a + getPedidoTotal(p), 0), [pedidos]);
  const cuentasPorCobrar = useMemo(() => clientes.reduce((a, c) => a + toNum(c.saldo_pendiente), 0), [clientes]);
  const carteraVencida = useMemo(() => clientes.reduce((a, c) => a + toNum((c as any).cartera_vencida), 0), [clientes]);
  const limiteCartera = useMemo(() => clientes.reduce((a, c) => a + toNum((c as any).limite_credito), 0), [clientes]);

  // Semáforo: cartera vencida supera el 40% del límite de crédito total
  const alertaCartera = limiteCartera > 0 && carteraVencida / limiteCartera > 0.4;

  return {
    clientes,
    setClientes,
    pedidos,
    setPedidos,
    modalEstadoPedido,
    setModalEstadoPedido,
    modalVendedor,
    setModalVendedor,
    modalClienteCompras,
    setModalClienteCompras,
    modalClienteDeudor,
    setModalClienteDeudor,
    ventasPorVendedor,
    topClientesGerencial,
    topDeudores,
    distribucionPago,
    funnelData,
    totalVentas,
    cuentasPorCobrar,
    carteraVencida,
    limiteCartera,
    alertaCartera,
  };
}
