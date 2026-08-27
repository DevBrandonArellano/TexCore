import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NuevaVentaDialog } from './NuevaVentaDialog';
import type { Cliente, Producto } from '../../lib/types';

// Sin test propio hasta ahora.
const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const CLIENTE_CREDITO: Cliente = {
  id: 1, nombre_razon_social: 'Cliente Crédito', limite_credito: 1000,
  plazo_credito_dias: 30, cartera_vencida: 0,
} as any;
const CLIENTE_CONTADO: Cliente = {
  id: 2, nombre_razon_social: 'Cliente Contado', limite_credito: 500,
  plazo_credito_dias: 0, cartera_vencida: 0,
} as any;
const CLIENTE_MOROSO: Cliente = {
  id: 3, nombre_razon_social: 'Cliente Moroso', limite_credito: 500,
  plazo_credito_dias: 30, cartera_vencida: 200,
} as any;
const PRODUCTO_1: Producto = { id: 10, descripcion: 'Hilo Azul', precio_base: 5 } as any;

function baseProps(overrides: Partial<React.ComponentProps<typeof NuevaVentaDialog>> = {}) {
  return {
    isOpen: true,
    onOpenChange: vi.fn(),
    clientes: [CLIENTE_CREDITO, CLIENTE_CONTADO, CLIENTE_MOROSO],
    productos: [PRODUCTO_1],
    orderForm: { cliente: '', guia_remision: '', esta_pagado: false, aplica_retencion: false, valor_retencion: '0' },
    setOrderForm: vi.fn(),
    orderItems: [],
    newItem: { producto: '', cantidad: 1, piezas: 1, peso: '', precio_unitario: '', incluye_iva: true },
    setNewItem: vi.fn(),
    addOrderItem: vi.fn(),
    removeOrderItem: vi.fn(),
    onSubmit: vi.fn(),
    ...overrides,
  };
}

describe('NuevaVentaDialog', () => {
  it('dado sin cliente seleccionado cuando renderiza entonces no muestra el panel de detalle del cliente', () => {
    render(<NuevaVentaDialog {...baseProps()} />);
    expect(screen.queryByText(/Plazo de Crédito Autorizado/)).not.toBeInTheDocument();
  });

  it('dado un cliente a credito con cartera al dia cuando selecciona entonces muestra el plazo autorizado', () => {
    render(<NuevaVentaDialog {...baseProps({ orderForm: { cliente: '1', guia_remision: '', esta_pagado: false, aplica_retencion: false, valor_retencion: '0' } })} />);
    expect(screen.getByText(/Plazo de Crédito Autorizado: 30 Días/)).toBeInTheDocument();
  });

  it('dado un cliente de contado cuando selecciona entonces el plazo se muestra como Contado', () => {
    render(<NuevaVentaDialog {...baseProps({ orderForm: { cliente: '2', guia_remision: '', esta_pagado: false, aplica_retencion: false, valor_retencion: '0' } })} />);
    expect(screen.getByText(/Plazo de Crédito Autorizado: Contado/)).toBeInTheDocument();
  });

  it('dado un cliente con cartera vencida cuando selecciona entonces muestra la alerta de cartera vencida', () => {
    render(<NuevaVentaDialog {...baseProps({ orderForm: { cliente: '3', guia_remision: '', esta_pagado: false, aplica_retencion: false, valor_retencion: '0' } })} />);
    expect(screen.getByText('Cliente con Cartera Vencida')).toBeInTheDocument();
  });

  it('dado cliente de contado con pedido no pagado cuando renderiza entonces muestra la advertencia de seguridad', () => {
    render(<NuevaVentaDialog {...baseProps({ orderForm: { cliente: '2', guia_remision: '', esta_pagado: false, aplica_retencion: false, valor_retencion: '0' } })} />);
    expect(screen.getByText(/Atención de Seguridad/)).toBeInTheDocument();
  });

  it('dado cliente de contado con pedido ya pagado cuando renderiza entonces no muestra la advertencia de seguridad', () => {
    render(<NuevaVentaDialog {...baseProps({ orderForm: { cliente: '2', guia_remision: '', esta_pagado: true, aplica_retencion: false, valor_retencion: '0' } })} />);
    expect(screen.queryByText(/Atención de Seguridad/)).not.toBeInTheDocument();
  });

  it('dado seleccionar un producto cuando cambia entonces precarga el precio base', async () => {
    const setNewItem = vi.fn();
    render(<NuevaVentaDialog {...baseProps({ setNewItem })} />);
    await userEvent.click(screen.getByText('Hilo Azul'));
    expect(setNewItem).toHaveBeenCalledWith(expect.objectContaining({ producto: '10', precio_unitario: '5' }));
  });

  it('dado items agregados cuando renderiza entonces muestra la tabla con el total del pedido', () => {
    render(<NuevaVentaDialog {...baseProps({
      orderItems: [{ producto: '10', cantidad: 1, piezas: 1, peso: 10, precio_unitario: 5, incluye_iva: true }],
    })} />);
    expect(screen.getAllByText('$57.500').length).toBeGreaterThan(0); // 50 + 15% IVA (fila y total coinciden con 1 solo item)
  });

  it('dado un item sin IVA cuando renderiza la tabla entonces muestra el guion en la columna IVA', () => {
    render(<NuevaVentaDialog {...baseProps({
      orderItems: [{ producto: '10', cantidad: 1, piezas: 1, peso: 10, precio_unitario: 5, incluye_iva: false }],
    })} />);
    expect(screen.getByText('-')).toBeInTheDocument();
  });

  it('dado click en eliminar item cuando se activa entonces llama removeOrderItem con el indice', async () => {
    const removeOrderItem = vi.fn();
    render(<NuevaVentaDialog {...baseProps({
      orderItems: [{ producto: '10', cantidad: 1, piezas: 1, peso: 10, precio_unitario: 5, incluye_iva: true }],
      removeOrderItem,
    })} />);
    const botones = screen.getAllByRole('button');
    const delBtn = botones.find((b) => b.className.includes('text-destructive'));
    await userEvent.click(delBtn!);
    expect(removeOrderItem).toHaveBeenCalledWith(0);
  });

  it('dado activar retencion cuando cambia el switch entonces resetea el valor de retencion a 0', async () => {
    const setOrderForm = vi.fn();
    render(<NuevaVentaDialog {...baseProps({
      orderItems: [{ producto: '10', cantidad: 1, piezas: 1, peso: 10, precio_unitario: 5, incluye_iva: false }],
      setOrderForm,
    })} />);
    const switches = screen.getAllByRole('switch');
    await userEvent.click(switches[1]); // el segundo switch es "aplica_retencion"
    expect(setOrderForm).toHaveBeenCalledWith(expect.objectContaining({ aplica_retencion: true }));
  });

  it('dado retencion aplicada con valor mayor a cero cuando renderiza entonces muestra el total menos retencion', () => {
    render(<NuevaVentaDialog {...baseProps({
      orderItems: [{ producto: '10', cantidad: 1, piezas: 1, peso: 10, precio_unitario: 5, incluye_iva: false }],
      orderForm: { cliente: '', guia_remision: '', esta_pagado: false, aplica_retencion: true, valor_retencion: '10' },
    })} />);
    expect(screen.getByText('TOTAL A COBRAR (Menos Retención):')).toBeInTheDocument();
    expect(screen.getByText('$40.000')).toBeInTheDocument();
  });

  it('dado retencion aplicada en cero cuando renderiza entonces no muestra el total con retencion', () => {
    render(<NuevaVentaDialog {...baseProps({
      orderItems: [{ producto: '10', cantidad: 1, piezas: 1, peso: 10, precio_unitario: 5, incluye_iva: false }],
      orderForm: { cliente: '', guia_remision: '', esta_pagado: false, aplica_retencion: true, valor_retencion: '0' },
    })} />);
    expect(screen.queryByText('TOTAL A COBRAR (Menos Retención):')).not.toBeInTheDocument();
  });

  it('dado click en cancelar y guardar cuando se activan entonces llaman a sus props', async () => {
    const onOpenChange = vi.fn();
    const onSubmit = vi.fn();
    render(<NuevaVentaDialog {...baseProps({ onOpenChange, onSubmit })} />);
    await userEvent.click(screen.getByRole('button', { name: /Cancelar/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    await userEvent.click(screen.getByRole('button', { name: /Finalizar y Guardar/i }));
    expect(onSubmit).toHaveBeenCalled();
  });
});
