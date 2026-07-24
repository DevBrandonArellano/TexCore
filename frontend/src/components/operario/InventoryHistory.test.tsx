import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InventoryHistory } from './InventoryHistory';
import { Movimiento } from '../../lib/types';

const formatFecha = (dateString: string) =>
  new Intl.DateTimeFormat('es-MX', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateString));

const MOVIMIENTO_1: Movimiento = {
  id: 1,
  fecha: '2026-07-10T15:30:00Z',
  tipo_movimiento: 'entrada',
  producto: 'Hilo Poliester 30/1',
  lote: 'L-001',
  bodega_origen: 'Bodega Central',
  bodega_destino: 'Bodega Tintura',
  documento_ref: null,
  usuario: 'jperez',
  cantidad: '150.00',
};

const MOVIMIENTO_2: Movimiento = {
  id: 2,
  fecha: '2026-07-11T09:00:00Z',
  tipo_movimiento: 'salida',
  producto: 'Colorante Azul',
  lote: null,
  bodega_origen: null,
  bodega_destino: null,
  documento_ref: null,
  usuario: 'jperez',
  cantidad: '5.50',
};

describe('InventoryHistory', () => {
  it('dado sin movimientos cuando renderiza entonces muestra el mensaje de historial vacio', () => {
    render(<InventoryHistory movements={[]} />);

    expect(screen.getByText('No hay movimientos registrados')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('dado movimientos existentes cuando renderiza entonces muestra la tabla con fecha, tipo, producto, origen, destino y cantidad', () => {
    render(<InventoryHistory movements={[MOVIMIENTO_1]} />);

    expect(screen.queryByText('No hay movimientos registrados')).not.toBeInTheDocument();
    expect(screen.getByText(formatFecha(MOVIMIENTO_1.fecha))).toBeInTheDocument();
    expect(screen.getByText('entrada')).toBeInTheDocument();
    expect(screen.getByText('Hilo Poliester 30/1')).toBeInTheDocument();
    expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    expect(screen.getByText('Bodega Tintura')).toBeInTheDocument();
    expect(screen.getByText('150.00')).toBeInTheDocument();
  });

  it('dado un movimiento sin bodega de origen o destino cuando renderiza entonces muestra N/A en ambas columnas', () => {
    render(<InventoryHistory movements={[MOVIMIENTO_2]} />);

    expect(screen.getByText('salida')).toBeInTheDocument();
    expect(screen.getByText('Colorante Azul')).toBeInTheDocument();
    const naCells = screen.getAllByText('N/A');
    expect(naCells).toHaveLength(2);
  });

  it('dado varios movimientos cuando renderiza entonces muestra una fila por cada uno', () => {
    render(<InventoryHistory movements={[MOVIMIENTO_1, MOVIMIENTO_2]} />);

    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3);
    expect(screen.getByText('Hilo Poliester 30/1')).toBeInTheDocument();
    expect(screen.getByText('Colorante Azul')).toBeInTheDocument();
  });
});
