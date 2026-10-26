/**
 * ISTQB — Nivel: Componente
 * Técnica : Black-box (partición de equivalencia + valor límite de la página)
 * Cubre   : StockView — stock paginado y filtrado en el servidor (/inventory/stock/,
 *           PaginacionAcotada). La prueba de carga del 2026-10-06 mostró que el listado
 *           completo no cabe en una respuesta.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { FiltrosStock, PaginaStock } from '../../types/inventario';

const listarStockMock = vi.fn();
vi.mock('../../lib/api/inventarioApi', () => ({
  inventarioApi: {
    listarStock: (...args: unknown[]) => listarStockMock(...args),
  },
}));

import { StockView } from './StockView';
import type { StockItem } from './inventoryUtils';

const ITEM_1: StockItem = {
  id: 1, producto: 'Hilo Azul', producto_id: 1, bodega: 'Central', bodega_id: 1,
  lote: 'L-001', lote_id: 5, lote_codigo: 'L-001', cantidad: '100',
};
const ITEM_2: StockItem = {
  id: 2, producto: 'Hilo Rojo', producto_id: 2, bodega: 'Norte', bodega_id: 2,
  lote: null, lote_id: null, lote_codigo: null, cantidad: '50',
};

/** Servidor falso: filtra por `search` y responde el bloque pedido. */
function servidorCon(stock: StockItem[]) {
  listarStockMock.mockImplementation(
    (pagina: number, tamano: number, filtros: FiltrosStock = {}): Promise<PaginaStock> => {
      const texto = (filtros.search ?? '').toLowerCase();
      const filas = stock.filter(f =>
        !texto || [f.producto, f.bodega, f.lote].some(v => (v ?? '').toLowerCase().includes(texto)));
      const inicio = (pagina - 1) * tamano;
      return Promise.resolve({ count: filas.length, next: null, previous: null, results: filas.slice(inicio, inicio + tamano) });
    },
  );
}

function renderStockView(props: React.ComponentProps<typeof StockView> = {}) {
  return render(
    <MemoryRouter>
      <StockView {...props} />
    </MemoryRouter>,
  );
}

const veinticinco = () => Array.from({ length: 25 }, (_, i) => ({ ...ITEM_1, id: i + 1, producto: `Producto ${i + 1}` }));

describe('StockView', () => {
  beforeEach(() => {
    listarStockMock.mockReset();
  });

  it('dado la respuesta pendiente cuando renderiza entonces muestra filas de esqueleto', () => {
    listarStockMock.mockReturnValue(new Promise(() => {}));
    const { container } = renderStockView();
    expect(container.querySelectorAll('[data-slot="skeleton"], .animate-pulse').length).toBeGreaterThan(0);
  });

  it('dado sin stock cuando carga entonces muestra el mensaje de vacio', async () => {
    servidorCon([]);
    renderStockView();
    expect(await screen.findByText('No hay stock para mostrar.')).toBeInTheDocument();
  });

  it('dado stock existente cuando carga entonces lista los items con su lote', async () => {
    servidorCon([ITEM_1, ITEM_2]);
    renderStockView();
    expect(await screen.findByText('Hilo Azul')).toBeInTheDocument();
    expect(screen.getByText('L-001')).toBeInTheDocument();
  });

  it('dado item sin lote cuando carga entonces muestra guion', async () => {
    servidorCon([ITEM_2]);
    renderStockView();
    expect(await screen.findByText('-')).toBeInTheDocument();
  });

  it('dado sede cuando monta entonces pide el primer bloque de 4 paginas de 20 filtrado por sede', async () => {
    servidorCon([]);
    renderStockView({ sedeId: '3' });
    await waitFor(() => {
      expect(listarStockMock).toHaveBeenCalledWith(1, 80, { sede_id: '3', search: '' });
    });
  });

  it('dado busqueda cuando escribe entonces la resuelve el servidor una sola vez al terminar', async () => {
    servidorCon([ITEM_1, ITEM_2]);
    renderStockView();
    await screen.findByText('Hilo Azul');

    await userEvent.type(screen.getByPlaceholderText('Buscar por producto, bodega o lote...'), 'Norte');

    await waitFor(() => expect(screen.queryByText('Hilo Azul')).not.toBeInTheDocument());
    expect(screen.getByText('Hilo Rojo')).toBeInTheDocument();
    const busquedas = listarStockMock.mock.calls.map(([, , filtros]) => filtros.search);
    expect(busquedas).toEqual(['', 'Norte']);
  });

  it('dado error del servidor cuando carga entonces muestra el error en la tabla', async () => {
    listarStockMock.mockRejectedValue(new Error('caido'));
    renderStockView();
    expect(await screen.findByText('No se pudieron cargar los datos.')).toBeInTheDocument();
  });

  it('dado mas de 20 items cuando avanza de pagina entonces muestra el resto sin pedirlo de nuevo', async () => {
    servidorCon(veinticinco());
    renderStockView();

    expect(await screen.findByText('Producto 1')).toBeInTheDocument();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.queryByText('Producto 21')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    expect(screen.getByText('Producto 21')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Anterior/i }));
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    // Las 25 filas llegaron en el primer bloque (80): la paginación no vuelve al servidor.
    expect(listarStockMock).toHaveBeenCalledTimes(1);
  });

  it('dado mas de 20 items cuando escribe una pagina valida en Ir a entonces navega', async () => {
    servidorCon(veinticinco());
    renderStockView();
    await screen.findByText('Producto 1');

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
  });

  it('dado mas de 20 items cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    servidorCon(veinticinco());
    renderStockView();
    await screen.findByText('Producto 1');

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });
});
