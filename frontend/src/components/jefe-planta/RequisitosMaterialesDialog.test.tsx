import React from 'react';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { RequisitosMaterialesDialog } from './RequisitosMaterialesDialog';
import apiClient from '../../lib/axios';
import type { OrdenProduccion, RequisitosOrden } from '../../lib/types';
import { parcial } from '../../testing/parcial';

vi.mock('../../lib/axios', () => ({ default: { get: vi.fn() } }));
const toastError = vi.fn();
vi.mock('sonner', () => ({ toast: { error: (...a: unknown[]) => toastError(...a) } }));

const ORDEN = parcial<OrdenProduccion>({ id: 3, codigo: 'OP-0042' });

const REQUISITOS: RequisitosOrden = {
  orden_codigo: 'OP-0042',
  peso_total_op: '100.00',
  peso_pendiente: '60.00',
  requisitos: [
    { producto_id: 1, producto_codigo: 'MP-ALG', producto_nombre: 'Algodón crudo', tipo: 'materia_prima',
      cantidad_requerida: '60.000', unidad: 'kg', es_base: true, ya_descontado: false,
      stock_disponible: '80.000', faltante: '0' },
    { producto_id: 2, producto_codigo: 'Q-IGU', producto_nombre: 'Igualante', tipo: 'quimico',
      cantidad_requerida: '1.600', unidad: 'kg', es_base: false, ya_descontado: false,
      stock_disponible: '1.000', faltante: '0.600' },
    { producto_id: 3, producto_codigo: 'C-AZ', producto_nombre: 'Colorante azul', tipo: 'quimico',
      cantidad_requerida: '1.500', unidad: 'kg', es_base: false, ya_descontado: true,
      stock_disponible: '0.000', faltante: '0' },
  ],
  advertencias: ['Q-OTRO: se mide en l, no en kg; no se incluye en el cálculo (OP OP-0042).'],
};

function abrir(datos: RequisitosOrden = REQUISITOS) {
  (apiClient.get as Mock).mockResolvedValue({ data: datos });
  render(<RequisitosMaterialesDialog open onOpenChange={vi.fn()} orden={ORDEN} />);
}

const fila = async (nombre: string) => (await screen.findByText(nombre)).closest('tr') as HTMLElement;

describe('RequisitosMaterialesDialog', () => {
  beforeEach(() => {
    (apiClient.get as Mock).mockReset();
    toastError.mockReset();
  });

  it('dado una orden cuando se abre entonces consulta sus requisitos y muestra el peso requerido y el pendiente', async () => {
    abrir();
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/ordenes-produccion/3/requisitos_materiales/'));
    expect((await screen.findByText('Peso requerido')).nextSibling).toHaveTextContent('100 kg');
    expect(screen.getByText('Pendiente de producir').nextSibling).toHaveTextContent('60 kg');
  });

  it('dado un material con stock suficiente cuando se muestra entonces lo indica', async () => {
    abrir();
    const algodon = await fila('Algodón crudo');
    expect(within(algodon).getByText('80')).toBeInTheDocument();
    expect(within(algodon).getByText('Suficiente')).toBeInTheDocument();
  });

  it('dado un material con stock insuficiente cuando se muestra entonces señala lo que falta', async () => {
    abrir();
    const igualante = await fila('Igualante');
    expect(within(igualante).getByText('Falta 0,6 kg')).toBeInTheDocument();
  });

  it('dado un químico ya descargado cuando se muestra entonces lo marca como descontado', async () => {
    abrir();
    expect(within(await fila('Colorante azul')).getByText('Ya descontado')).toBeInTheDocument();
  });

  it('dado advertencias del cálculo cuando se muestra entonces las lista', async () => {
    abrir();
    expect(await screen.findByText(/Q-OTRO: se mide en l/)).toBeInTheDocument();
  });

  it('dado una orden de producción continua cuando se muestra entonces indica que no tiene peso requerido', async () => {
    abrir({ ...REQUISITOS, peso_total_op: null, peso_pendiente: null, requisitos: [] });
    expect(await screen.findAllByText('Sin peso requerido')).toHaveLength(2);
  });

  it('dado un error al consultar cuando se abre entonces avisa', async () => {
    (apiClient.get as Mock).mockRejectedValueOnce({ response: { status: 500 } });
    render(<RequisitosMaterialesDialog open onOpenChange={vi.fn()} orden={ORDEN} />);
    await waitFor(() => expect(toastError).toHaveBeenCalled());
  });
});
