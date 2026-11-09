/**
 * HistorialPedidoModal: detalle de la anulación de un pedido.
 *
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): pedido con todos los datos / sin guía, sin quién anuló y sin
 *   fecha; sin pedido.
 */
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HistorialPedidoModal } from './HistorialPedidoModal';
import type { PedidoVenta } from '../../lib/types';

const pedido = (extra: Partial<PedidoVenta>) =>
  ({ id: 12, cliente_nombre: 'Textiles Andinos', motivo_anulacion: 'Cliente canceló', ...extra }) as PedidoVenta;

describe('HistorialPedidoModal', () => {
  it('dado pedido anulado con todos los datos cuando abre entonces los muestra', () => {
    render(<HistorialPedidoModal onClose={vi.fn()} pedido={pedido({
      guia_remision: 'GR-77', anulado_por_nombre: 'Ana Pérez', fecha_anulacion: '2026-10-27T18:23:00Z',
    })} />);
    expect(screen.getByText('GR-77')).toBeInTheDocument();
    expect(screen.getByText('Ana Pérez')).toBeInTheDocument();
    expect(screen.getByText('Cliente canceló')).toBeInTheDocument();
    expect(screen.queryAllByText('—')).toHaveLength(0);
  });

  it('dado pedido sin guía, sin quién anuló y sin fecha cuando abre entonces muestra guiones', () => {
    render(<HistorialPedidoModal onClose={vi.fn()} pedido={pedido({ guia_remision: '', anulado_por_nombre: undefined })} />);
    expect(screen.getAllByText('—')).toHaveLength(3);
  });

  it('dado sin pedido cuando renderiza entonces no abre el diálogo', () => {
    render(<HistorialPedidoModal onClose={vi.fn()} pedido={null} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
