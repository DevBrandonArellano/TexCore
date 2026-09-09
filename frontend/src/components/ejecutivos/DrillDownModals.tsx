import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import type { Cliente, PedidoVenta } from '../../lib/types';
import type { ProduccionProductoItem, TendenciaDia } from './types';
import { fmt, toNum, getPedidoTotal } from './utils';

// ---------------------------------------------------------------------------
// Tipos locales compartidos
// ---------------------------------------------------------------------------

export interface StockItem {
  id: number;
  producto: string;
  bodega: string;
  lote: string | null;
  cantidad: string;
}

export interface DeudorExtendido extends Cliente {
  name: string;
  fullName: string;
  deuda: number;
  obj: Cliente;
}

// ---------------------------------------------------------------------------
// Modales de Drill-Down
// ---------------------------------------------------------------------------

interface StockBodegaModalProps {
  bodegaSeleccionada: string | null;
  onClose: () => void;
  stock: StockItem[];
}

export function StockBodegaModal({ bodegaSeleccionada, onClose, stock }: StockBodegaModalProps) {
  const stockFiltrado = stock.filter(s => s.bodega === bodegaSeleccionada);

  return (
    <Dialog open={bodegaSeleccionada !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Stock en Bodega: {bodegaSeleccionada}</DialogTitle>
          <DialogDescription>
            Detalle de todos los productos y cantidades actualmente almacenados en esta bodega.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Producto</TableHead>
                <TableHead>Lote</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stockFiltrado.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>{s.producto}</TableCell>
                  <TableCell>{s.lote || '—'}</TableCell>
                  <TableCell className="text-right font-medium">{fmt(toNum(s.cantidad), 2)}</TableCell>
                </TableRow>
              ))}
              {stockFiltrado.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                    No hay productos en esta bodega.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface PedidosEstadoModalProps {
  estado: string | null;
  onClose: () => void;
  pedidos: PedidoVenta[];
}

export function PedidosEstadoModal({ estado, onClose, pedidos }: PedidosEstadoModalProps) {
  const pedidosFiltrados = pedidos.filter(p => p.estado === estado);

  return (
    <Dialog open={estado !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Pedidos en Estado: <span className="capitalize">{estado}</span></DialogTitle>
          <DialogDescription>
            Listado de pedidos clasificados bajo este estado en el sistema.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cliente</TableHead>
                <TableHead>Vendedor</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Fecha</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pedidosFiltrados.map((p, i) => (
                <TableRow key={i}>
                  <TableCell>{(p as any).cliente_nombre || '—'}</TableCell>
                  <TableCell>{(p as any).vendedor_nombre || '—'}</TableCell>
                  <TableCell className="text-right font-medium">${fmt(getPedidoTotal(p))}</TableCell>
                  <TableCell>{(p.fecha_creacion || p.fecha_pedido) ? String(p.fecha_creacion || p.fecha_pedido).slice(0, 10) : '—'}</TableCell>
                </TableRow>
              ))}
              {pedidosFiltrados.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-4 text-muted-foreground">Sin pedidos</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface VentasVendedorModalProps {
  vendedor: string | null;
  onClose: () => void;
  pedidos: PedidoVenta[];
}

export function VentasVendedorModal({ vendedor, onClose, pedidos }: VentasVendedorModalProps) {
  const pedidosFiltrados = pedidos.filter(p => ((p as any).vendedor_nombre || 'Sin asignar') === vendedor);

  return (
    <Dialog open={vendedor !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Ventas del Vendedor: {vendedor}</DialogTitle>
          <DialogDescription>
            Detalle de los pedidos cerrados o gestionados por este vendedor.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cliente</TableHead>
                <TableHead>Estado Pedido</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Pago</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pedidosFiltrados.map((p, i) => (
                <TableRow key={i}>
                  <TableCell>{(p as any).cliente_nombre || '—'}</TableCell>
                  <TableCell><span className="capitalize">{p.estado}</span></TableCell>
                  <TableCell className="text-right font-medium">${fmt(getPedidoTotal(p))}</TableCell>
                  <TableCell>{p.esta_pagado ? <Badge className="bg-green-500 hover:bg-green-600">Pagado</Badge> : <Badge variant="secondary">Pendiente</Badge>}</TableCell>
                </TableRow>
              ))}
              {pedidosFiltrados.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-4 text-muted-foreground">Sin pedidos</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface ClienteComprasModalProps {
  cliente: string | null;
  onClose: () => void;
  pedidos: PedidoVenta[];
}

export function ClienteComprasModal({ cliente, onClose, pedidos }: ClienteComprasModalProps) {
  const pedidosFiltrados = pedidos.filter(p => ((p as any).cliente_nombre || 'Sin nombre') === cliente);

  return (
    <Dialog open={cliente !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Historial de Compras: {cliente}</DialogTitle>
          <DialogDescription>
            Todos los pedidos correspondientes a este cliente en el periodo actual.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vendedor</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Monto</TableHead>
                <TableHead>Fecha</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pedidosFiltrados.map((p, i) => (
                <TableRow key={i}>
                  <TableCell>{(p as any).vendedor_nombre || '—'}</TableCell>
                  <TableCell><span className="capitalize">{p.estado}</span></TableCell>
                  <TableCell className="text-right font-medium">${fmt(getPedidoTotal(p))}</TableCell>
                  <TableCell>{(p.fecha_creacion || p.fecha_pedido) ? String(p.fecha_creacion || p.fecha_pedido).slice(0, 10) : '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface ClienteDeudorModalProps {
  clienteNombre: string | null;
  onClose: () => void;
  topDeudores: DeudorExtendido[];
}

export function ClienteDeudorModal({ clienteNombre, onClose, topDeudores }: ClienteDeudorModalProps) {
  const c = topDeudores.find(x => x.fullName === clienteNombre)?.obj;

  return (
    <Dialog open={clienteNombre !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Perfil de Riesgo Financiero</DialogTitle>
          <DialogDescription>Detalle de la deuda para acciones de cobranza.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          {c && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border">
                <p className="text-sm font-semibold text-slate-500">Razón Social</p>
                <p className="text-base font-bold">{c.nombre_razon_social}</p>
              </div>
              <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-800">
                <p className="text-sm font-semibold text-red-500">Deuda Actual</p>
                <p className="text-2xl font-black text-red-600">${fmt(toNum(c.saldo_pendiente))}</p>
              </div>
              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border">
                <p className="text-sm font-semibold text-slate-500">Límite de Crédito</p>
                <p className="text-base">${fmt(toNum((c as any).limite_credito))}</p>
              </div>
              <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg border">
                <p className="text-sm font-semibold text-slate-500">Riesgo (Deuda / Límite)</p>
                <p className="text-base">
                  {toNum((c as any).limite_credito) > 0 ? `${fmt((toNum(c.saldo_pendiente) / toNum((c as any).limite_credito)) * 100, 1)}%` : 'Sin límite definido'}
                </p>
              </div>
            </div>
          )}
          <div className="mt-4 pt-4 border-t flex justify-end">
            <Button variant="outline" onClick={onClose}>Cerrar</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface ProductoHistorialModalProps {
  producto: ProduccionProductoItem | null;
  historial: TendenciaDia[];
  cargando: boolean;
  onClose: () => void;
}

/** CU-EJ-09: historial diario de kg producidos de UN producto — drill-down desde la tabla de producción. */
export function ProductoHistorialModal({ producto, historial, cargando, onClose }: ProductoHistorialModalProps) {
  return (
    <Dialog open={producto !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Historial de Producción: {producto?.producto_nombre}</DialogTitle>
          <DialogDescription>
            Código {producto?.producto_codigo} — Total del rango: {producto ? fmt(toNum(producto.kg_total), 1) : '0'} kg
            en {producto?.num_lotes ?? 0} lotes
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto mt-4">
          {cargando ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground">Cargando historial…</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Kg Producidos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historial.map((h, i) => (
                  <TableRow key={i}>
                    <TableCell>{h.fecha}</TableCell>
                    <TableCell className="text-right font-medium">{fmt(h.kg, 1)}</TableCell>
                  </TableRow>
                ))}
                {historial.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2} className="text-center py-8 text-muted-foreground">
                      Sin producción diaria registrada para este producto.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
