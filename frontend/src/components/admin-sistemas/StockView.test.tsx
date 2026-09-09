import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { StockView } from './StockView';
import type { StockItem } from './inventoryUtils';

// Sin test propio hasta ahora.

const ITEM_1: StockItem = {
  id: 1, producto: 'Hilo Azul', producto_id: 1, bodega: 'Central', bodega_id: 1,
  lote: 'L-001', lote_id: 5, lote_codigo: 'L-001', cantidad: '100',
};
const ITEM_2: StockItem = {
  id: 2, producto: 'Hilo Rojo', producto_id: 2, bodega: 'Norte', bodega_id: 2,
  lote: null, lote_id: null, lote_codigo: null, cantidad: '50',
};

function renderStockView(stock: StockItem[] = [], loading = false) {
  return render(
    <MemoryRouter>
      <StockView stock={stock} loading={loading} />
    </MemoryRouter>,
  );
}

describe('StockView', () => {
  it('dado loading en true cuando renderiza entonces muestra filas de esqueleto', () => {
    renderStockView([ITEM_1], true);
    expect(screen.queryByText('Hilo Azul')).not.toBeInTheDocument();
  });

  it('dado sin stock cuando renderiza entonces muestra el mensaje de vacio', () => {
    renderStockView([]);
    expect(screen.getByText('No hay stock para mostrar.')).toBeInTheDocument();
  });

  it('dado stock existente cuando renderiza entonces lista los items con su lote', () => {
    renderStockView([ITEM_1, ITEM_2]);
    expect(screen.getByText('Hilo Azul')).toBeInTheDocument();
    expect(screen.getByText('L-001')).toBeInTheDocument();
  });

  it('dado item sin lote cuando renderiza entonces muestra guion', () => {
    renderStockView([ITEM_2]);
    expect(screen.getByText('-')).toBeInTheDocument();
  });

  it('dado busqueda por producto cuando escribe entonces filtra la lista', async () => {
    renderStockView([ITEM_1, ITEM_2]);
    await userEvent.type(screen.getByPlaceholderText('Buscar por producto, bodega o lote...'), 'Azul');
    expect(screen.getByText('Hilo Azul')).toBeInTheDocument();
    expect(screen.queryByText('Hilo Rojo')).not.toBeInTheDocument();
  });

  it('dado busqueda por bodega cuando escribe entonces filtra la lista', async () => {
    renderStockView([ITEM_1, ITEM_2]);
    await userEvent.type(screen.getByPlaceholderText('Buscar por producto, bodega o lote...'), 'Norte');
    expect(screen.getByText('Hilo Rojo')).toBeInTheDocument();
    expect(screen.queryByText('Hilo Azul')).not.toBeInTheDocument();
  });

  it('dado busqueda por lote cuando escribe entonces filtra la lista', async () => {
    renderStockView([ITEM_1, ITEM_2]);
    await userEvent.type(screen.getByPlaceholderText('Buscar por producto, bodega o lote...'), 'L-001');
    expect(screen.getByText('Hilo Azul')).toBeInTheDocument();
    expect(screen.queryByText('Hilo Rojo')).not.toBeInTheDocument();
  });

  it('dado mas de 20 items cuando avanza de pagina cuando pagina entonces muestra el resto', async () => {
    const items = Array.from({ length: 25 }, (_, i) => ({ ...ITEM_1, id: i + 1, producto: `Producto ${i + 1}` }));
    renderStockView(items);

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('Producto 1')).toBeInTheDocument();
    expect(screen.queryByText('Producto 21')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Producto 21')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Anterior/i }));
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado mas de 20 items cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const items = Array.from({ length: 25 }, (_, i) => ({ ...ITEM_1, id: i + 1, producto: `Producto ${i + 1}` }));
    renderStockView(items);

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
  });

  it('dado mas de 20 items cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const items = Array.from({ length: 25 }, (_, i) => ({ ...ITEM_1, id: i + 1, producto: `Producto ${i + 1}` }));
    renderStockView(items);

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });
});
