import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MateriaPrimaView } from './MateriaPrimaView';

const mockListar = vi.fn();
vi.mock('../../lib/api/inventarioApi', () => ({
  inventarioApi: { listarMateriaPrima: (...a: unknown[]) => mockListar(...a) },
}));
vi.mock('../ui/searchable-select', () => ({
  SearchableSelect: ({ items, onValueChange }: import('react').ComponentProps<typeof import('../ui/searchable-select').SearchableSelect>) => (
    <button type="button" onClick={() => onValueChange(items?.[0]?.value ?? '')}>elegir-proveedor</button>
  ),
}));

const LOTE = {
  id: 1, producto: 4, producto_descripcion: 'Algodón peinado', proveedor: 3, proveedor_nombre: 'Hilos del Sur',
  lote_proveedor: 'HS-0915', fecha_recepcion: '2026-09-15', cantidad_kg: '100.000', costo_unitario: '2.500',
  certificado_calidad: '/media/certificados/2026/09/cert.pdf', numero_documento_entrada: 'FAC-1',
  bodega_recepcion: 5, bodega_nombre: 'Bodega MP', cantidad_consumida: '40.000', cantidad_disponible: 60,
  completamente_consumida: false, sede: 1, fecha_creacion: '2026-09-15T10:00:00Z',
};
const pagina = (results: unknown[]) => ({ count: results.length, next: null, previous: null, results });

describe('MateriaPrimaView', () => {
  beforeEach(() => mockListar.mockReset());

  it('dado lotes recibidos cuando carga entonces muestra proveedor, cantidades, costo y certificado', async () => {
    mockListar.mockResolvedValue(pagina([LOTE]));
    render(<MateriaPrimaView proveedores={[{ id: 3, nombre: 'Hilos del Sur' }]} />);
    expect(await screen.findByText('HS-0915')).toBeInTheDocument();
    expect(screen.getByText('Hilos del Sur')).toBeInTheDocument();
    expect(screen.getByText('100.000')).toBeInTheDocument();
    expect(screen.getByText('60.000')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver certificado' })).toHaveAttribute('href', LOTE.certificado_calidad);
    expect(mockListar).toHaveBeenCalledWith(1, 120, {});
  });

  it('dado sin lotes cuando carga entonces muestra el estado vacío', async () => {
    mockListar.mockResolvedValue(pagina([]));
    render(<MateriaPrimaView proveedores={[]} />);
    expect(await screen.findByText('No hay lotes de materia prima.')).toBeInTheDocument();
  });

  it('dado filtros de proveedor y solo disponibles cuando cambian entonces vuelve a pedir con esos filtros', async () => {
    mockListar.mockResolvedValue(pagina([LOTE]));
    render(<MateriaPrimaView proveedores={[{ id: 3, nombre: 'Hilos del Sur' }]} />);
    await screen.findByText('HS-0915');
    fireEvent.click(screen.getByText('elegir-proveedor'));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Solo disponibles' }));
    await waitFor(() => expect(mockListar).toHaveBeenLastCalledWith(1, 120, { proveedor: 3, disponibles: true }));
  });

  it('dado lote agotado cuando carga entonces lo marca como consumido', async () => {
    mockListar.mockResolvedValue(pagina([{ ...LOTE, cantidad_disponible: 0, completamente_consumida: true }]));
    render(<MateriaPrimaView proveedores={[]} />);
    expect(await screen.findByText('Consumido')).toBeInTheDocument();
  });
});
