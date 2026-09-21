import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProductSelect } from './product-select';
import type { Producto } from '../../lib/types';

const MOCK_PRODUCTOS: Producto[] = [
  {
    id: 1,
    codigo: 'HIL-001',
    descripcion: 'Hilo 20/1 Algodón Crudo',
    tipo: 'hilo',
    unidad_medida: 'kg',
  } as Producto,
  {
    id: 2,
    codigo: 'TEL-100',
    descripcion: 'Tela Poliéster Jersey',
    tipo: 'producto_terminado',
    unidad_medida: 'metros',
  } as Producto,
  {
    id: 3,
    codigo: 'MECH-05',
    descripcion: 'Mecha Preparada Algodón',
    tipo: 'producto_intermedio',
    unidad_medida: 'kg',
  } as Producto,
];

describe('ProductSelect', () => {
  it('dado productos cuando renderiza entonces muestra el placeholder', () => {
    render(
      <ProductSelect
        productos={MOCK_PRODUCTOS}
        value=""
        onValueChange={vi.fn()}
        placeholder="Seleccionar material"
      />
    );

    expect(screen.getByText('Seleccionar material')).toBeInTheDocument();
  });

  it('dado un producto seleccionado cuando renderiza entonces muestra codigo y descripcion en el trigger', () => {
    render(
      <ProductSelect
        productos={MOCK_PRODUCTOS}
        value="1"
        onValueChange={vi.fn()}
      />
    );

    expect(screen.getByText('[HIL-001] Hilo 20/1 Algodón Crudo')).toBeInTheDocument();
  });

  it('dado click en el trigger cuando se abre entonces muestra la barra de busqueda', async () => {
    const user = userEvent.setup();
    render(
      <ProductSelect
        productos={MOCK_PRODUCTOS}
        value=""
        onValueChange={vi.fn()}
      />
    );

    const trigger = screen.getByRole('combobox');
    await user.click(trigger);

    expect(
      screen.getByPlaceholderText('Buscar por código o descripción...')
    ).toBeInTheDocument();
    expect(screen.getByText('3 productos disponibles')).toBeInTheDocument();
  });

  it('dado texto de busqueda por codigo cuando el usuario escribe entonces filtra los productos', async () => {
    const user = userEvent.setup();
    render(
      <ProductSelect
        productos={MOCK_PRODUCTOS}
        value=""
        onValueChange={vi.fn()}
      />
    );

    await user.click(screen.getByRole('combobox'));
    const searchInput = screen.getByPlaceholderText('Buscar por código o descripción...');
    await user.type(searchInput, 'TEL');

    expect(screen.getByText('Tela Poliéster Jersey')).toBeInTheDocument();
    expect(screen.queryByText('Hilo 20/1 Algodón Crudo')).not.toBeInTheDocument();
    expect(screen.getByText('1 de 3 productos')).toBeInTheDocument();
  });

  it('dado texto de busqueda por descripcion sin tildes cuando el usuario escribe entonces filtra correctamente', async () => {
    const user = userEvent.setup();
    render(
      <ProductSelect
        productos={MOCK_PRODUCTOS}
        value=""
        onValueChange={vi.fn()}
      />
    );

    await user.click(screen.getByRole('combobox'));
    const searchInput = screen.getByPlaceholderText('Buscar por código o descripción...');
    await user.type(searchInput, 'algodon');

    expect(screen.getByText('Hilo 20/1 Algodón Crudo')).toBeInTheDocument();
    expect(screen.getByText('Mecha Preparada Algodón')).toBeInTheDocument();
    expect(screen.queryByText('Tela Poliéster Jersey')).not.toBeInTheDocument();
  });

  it('dado seleccion de un producto cuando el usuario hace click entonces llama onValueChange', async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    render(
      <ProductSelect
        productos={MOCK_PRODUCTOS}
        value=""
        onValueChange={onValueChange}
      />
    );

    await user.click(screen.getByRole('combobox'));
    const option = await screen.findByRole('option', { name: 'Tela Poliéster Jersey' });
    await user.click(option);

    expect(onValueChange).toHaveBeenCalledWith('2');
  });

  it('dado busqueda sin resultados cuando no coincide entonces muestra mensaje explicativo', async () => {
    const user = userEvent.setup();
    render(
      <ProductSelect
        productos={MOCK_PRODUCTOS}
        value=""
        onValueChange={vi.fn()}
      />
    );

    await user.click(screen.getByRole('combobox'));
    const searchInput = screen.getByPlaceholderText('Buscar por código o descripción...');
    await user.type(searchInput, 'xyz-inexistente');

    expect(
      screen.getByText(/No se encontraron productos para/i)
    ).toBeInTheDocument();
  });
});
