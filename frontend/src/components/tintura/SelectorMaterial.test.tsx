/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): material activo / material actual ya inactivo / selector opcional.
 * - Transición de estados (STT): cargando → cargado / cargando → error.
 * - Caja blanca (CB): rama de error al cargar el catálogo.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SelectorMaterial } from './SelectorMaterial';

const mockListar = vi.fn();
vi.mock('../../lib/api/materialesSustratoApi', () => ({
  materialesSustratoApi: { listar: (...a: unknown[]) => mockListar(...a) },
}));

const ALGODON = { id: 1, clave: 'algodon', nombre: 'Algodón', activo: true, sede: 1 };
const SEDA = { id: 2, clave: 'seda', nombre: 'Seda', activo: true, sede: 1 };

describe('SelectorMaterial', () => {
  beforeEach(() => {
    mockListar.mockReset();
    mockListar.mockResolvedValue([ALGODON, SEDA]);
  });

  it('dado materiales activos cuando carga entonces los ofrece y pide solo los activos', async () => {
    render(<SelectorMaterial id="mat" value="algodon" onChange={vi.fn()} />);
    expect(await screen.findByRole('option', { name: 'Seda' })).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveValue('algodon');
    expect(mockListar).toHaveBeenCalledWith({ soloActivos: true });
  });

  it('dado que elige un material cuando cambia entonces notifica su clave', async () => {
    const onChange = vi.fn();
    render(<SelectorMaterial id="mat" value="algodon" onChange={onChange} />);
    await screen.findByRole('option', { name: 'Seda' });
    await userEvent.selectOptions(screen.getByRole('combobox'), 'seda');
    expect(onChange).toHaveBeenCalledWith('seda');
  });

  it('dado un material actual que ya no está activo cuando carga entonces lo conserva como opción', async () => {
    render(<SelectorMaterial id="mat" value="lino" etiquetaActual="Lino" onChange={vi.fn()} />);
    expect(await screen.findByRole('option', { name: 'Lino (inactivo)' })).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveValue('lino');
  });

  it('dado un selector opcional cuando carga entonces ofrece la opción vacía', async () => {
    render(<SelectorMaterial id="mat" value="" opcional="Igual que el origen" onChange={vi.fn()} />);
    expect(await screen.findByRole('option', { name: 'Igual que el origen' })).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveValue('');
  });

  it('dado un error al cargar el catálogo cuando monta entonces lo informa', async () => {
    mockListar.mockRejectedValue(new Error('caído'));
    render(<SelectorMaterial id="mat" value="algodon" onChange={vi.fn()} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar los materiales.');
  });
});
