import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { StockAFechaView } from './StockAFechaView';
import { parcial } from '../../testing/parcial';
import { type Producto } from '../../lib/types';

const mockStock = vi.fn();
vi.mock('../../lib/api/inventarioApi', () => ({
  inventarioApi: { stockAFecha: (...a: unknown[]) => mockStock(...a) },
}));
const mockToastError = vi.fn();
vi.mock('sonner', () => ({ toast: { error: (...a: unknown[]) => mockToastError(...a) } }));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: import('react').ComponentProps<typeof import('../ui/select').Select>) => (
    <SelectCtx.Provider value={onValueChange ?? (() => {})}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectTrigger>) => <div>{children}</div>,
  SelectValue: ({ placeholder }: import('react').ComponentProps<typeof import('../ui/select').SelectValue>) => <span>{placeholder}</span>,
  SelectContent: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectContent>) => <div>{children}</div>,
  SelectItem: ({ children, value }: import('react').ComponentProps<typeof import('../ui/select').SelectItem>) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));
vi.mock('../ui/product-select', () => ({
  ProductSelect: ({ onValueChange }: import('react').ComponentProps<typeof import('../ui/product-select').ProductSelect>) => (
    <button type="button" onClick={() => onValueChange('4')}>elegir-producto</button>
  ),
}));

const PROPS = {
  productos: [parcial<Producto>({ id: 4, codigo: 'MP-4', descripcion: 'Algodón' })],
  bodegas: [{ id: 5, nombre: 'Bodega MP', sede: 1 }, { id: 6, nombre: 'Bodega Tintura', sede: 1 }],
};

describe('StockAFechaView', () => {
  beforeEach(() => {
    mockStock.mockReset();
    mockToastError.mockReset();
  });

  it('dado sin producto cuando consulta entonces avisa y no llama a la API', () => {
    render(<StockAFechaView {...PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: 'Consultar stock' }));
    expect(mockToastError).toHaveBeenCalled();
    expect(mockStock).not.toHaveBeenCalled();
  });

  it('dado producto, fecha y bodega cuando consulta entonces muestra el saldo por bodega y el total', async () => {
    mockStock.mockResolvedValue([
      { bodega_id: 5, bodega: 'Bodega MP', sede: 'Matriz', stock_calculado: '70.000' },
      { bodega_id: 6, bodega: 'Bodega Tintura', sede: 'Matriz', stock_calculado: 30 },
    ]);
    render(<StockAFechaView {...PROPS} />);
    fireEvent.click(screen.getByText('elegir-producto'));
    fireEvent.change(screen.getByLabelText('Fecha de corte'), { target: { value: '2026-09-15' } });
    fireEvent.click(screen.getByRole('button', { name: 'Consultar stock' }));

    expect(await screen.findByText('70.000')).toBeInTheDocument();
    expect(screen.getByText('30.000')).toBeInTheDocument();
    expect(screen.getByText('100.000')).toBeInTheDocument();
    expect(mockStock).toHaveBeenCalledWith({ producto_id: 4, fecha_corte: '2026-09-15' });
  });

  it('dado bodega elegida cuando consulta entonces la envía como filtro', async () => {
    mockStock.mockResolvedValue([]);
    render(<StockAFechaView {...PROPS} />);
    fireEvent.click(screen.getByText('elegir-producto'));
    fireEvent.click(screen.getByText('Bodega Tintura'));
    fireEvent.click(screen.getByRole('button', { name: 'Consultar stock' }));
    await waitFor(() => expect(mockStock).toHaveBeenCalledWith(expect.objectContaining({ bodega_id: 6 })));
    expect(await screen.findByText('Sin stock a esa fecha.')).toBeInTheDocument();
  });

  it('dado error del servidor cuando consulta entonces lo muestra', async () => {
    mockStock.mockRejectedValue({ response: { status: 400, data: { error: 'fecha_corte debe tener formato YYYY-MM-DD.' } } });
    render(<StockAFechaView {...PROPS} />);
    fireEvent.click(screen.getByText('elegir-producto'));
    fireEvent.click(screen.getByRole('button', { name: 'Consultar stock' }));
    await waitFor(() => expect(mockToastError).toHaveBeenCalled());
    expect(String(mockToastError.mock.calls[0][0])).toContain('fecha_corte');
  });
});
