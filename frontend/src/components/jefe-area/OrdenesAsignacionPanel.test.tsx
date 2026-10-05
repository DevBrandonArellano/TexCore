import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Maquina, OrdenProduccion, User } from '../../lib/types';
import { OrdenesAsignacionPanel } from './OrdenesAsignacionPanel';

const completarDetallesMock = vi.fn();
vi.mock('../../lib/api/ordenesApi', () => ({
  ordenesApi: { completarDetalles: (...args: unknown[]) => completarDetallesMock(...args) },
}));

// El panel de mezcla tiene sus propias pruebas; aquí solo importa con qué orden se monta.
vi.mock('./ComponenteMezclaPanel', () => ({
  ComponenteMezclaPanel: ({ ordenId, pesoNeto }: { ordenId: number; pesoNeto: number }) => (
    <div data-testid="mezcla-panel">orden {ordenId} · {pesoNeto} kg</div>
  ),
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => toastErrorMock(...args),
    success: (...args: unknown[]) => toastSuccessMock(...args),
  },
}));

const orden = (overrides: Partial<OrdenProduccion>): OrdenProduccion => ({
  id: 1, codigo: 'OP-1', producto: 1, formula_color: 1, peso_neto_requerido: 200,
  estado: 'pendiente', fecha_creacion: '', fecha_modificacion: '', sede: 1,
  inventario_descontado: false, prioridad: 'normal', producto_nombre: 'Hilo crudo',
  ...overrides,
});

function montar(ordenes: OrdenProduccion[]) {
  const onDataRefresh = vi.fn();
  render(
    <OrdenesAsignacionPanel
      ordenes={ordenes}
      maquinas={[{ id: 3, nombre: 'Jet 1' } as Maquina]}
      operarios={[{ id: 4, username: 'operario1' } as User]}
      onDataRefresh={onDataRefresh}
    />,
  );
  return { onDataRefresh };
}

beforeEach(() => vi.clearAllMocks());

describe('OrdenesAsignacionPanel', () => {
  it('dado ordenes de varios estados cuando renderiza entonces solo lista las pendientes', () => {
    montar([orden({ id: 1, codigo: 'OP-1' }), orden({ id: 2, codigo: 'OP-2', estado: 'en_proceso' })]);
    expect(screen.getByText('OP-1')).toBeInTheDocument();
    expect(screen.queryByText('OP-2')).not.toBeInTheDocument();
  });

  it('dado sin ordenes pendientes cuando renderiza entonces muestra el mensaje vacio', () => {
    montar([orden({ estado: 'finalizada' })]);
    expect(screen.getByText(/No hay órdenes pendientes/)).toBeInTheDocument();
  });

  it('dado una orden pendiente cuando abre Componentes de mezcla entonces monta el panel con su id y peso', async () => {
    montar([orden({ id: 7, codigo: 'OP-7', peso_neto_requerido: 350 })]);

    await userEvent.click(screen.getByRole('button', { name: /Componentes de mezcla/i }));

    const hoja = await screen.findByRole('dialog');
    expect(within(hoja).getByText(/Mezcla de OP-7/)).toBeInTheDocument();
    expect(within(hoja).getByTestId('mezcla-panel')).toHaveTextContent('orden 7 · 350 kg');
  });

  it('dado el panel de mezcla abierto cuando lo cierra entonces desaparece', async () => {
    montar([orden({ id: 7, codigo: 'OP-7' })]);
    await userEvent.click(screen.getByRole('button', { name: /Componentes de mezcla/i }));
    await screen.findByRole('dialog');
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('dado asignar sin maquina ni operario cuando hace clic entonces avisa y no llama a la API', async () => {
    montar([orden({})]);
    await userEvent.click(screen.getByRole('button', { name: /Asignar/i }));
    expect(toastErrorMock).toHaveBeenCalledWith('Debes seleccionar una máquina y un operario.');
    expect(completarDetallesMock).not.toHaveBeenCalled();
  });

  it('dado un fallo al asignar cuando la API rechaza entonces muestra el error', async () => {
    completarDetallesMock.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'Máquina ocupada' } } });
    const user = userEvent.setup();
    montar([orden({})]);

    const [comboMaquina, comboOperario] = screen.getAllByRole('combobox');
    await user.click(comboMaquina);
    await user.click(await screen.findByRole('option', { name: 'Jet 1' }));
    await user.click(comboOperario);
    await user.click(await screen.findByRole('option', { name: 'operario1' }));
    await user.click(screen.getByRole('button', { name: /Asignar/i }));

    await waitFor(() => expect(completarDetallesMock).toHaveBeenCalledWith(1, {
      maquina_asignada: 3, operario_asignado: 4, iniciar: true,
    }));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
  });
});
