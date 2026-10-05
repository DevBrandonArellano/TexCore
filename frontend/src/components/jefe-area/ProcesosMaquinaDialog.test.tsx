import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProcesosMaquinaDialog } from './ProcesosMaquinaDialog';

const mockListar = vi.fn();
const mockAsignar = vi.fn();
const mockDeMaquina = vi.fn();
vi.mock('../../lib/api/procesosTintoreriaApi', () => ({
  procesosTintoreriaApi: {
    listar: (...a: unknown[]) => mockListar(...a),
    asignarAMaquina: (...a: unknown[]) => mockAsignar(...a),
  },
}));
vi.mock('../../lib/api/ordenesApi', () => ({
  ordenesApi: { procesosDeMaquina: (...a: unknown[]) => mockDeMaquina(...a) },
}));
const mockToast = { success: vi.fn(), error: vi.fn() };
vi.mock('sonner', () => ({
  toast: { success: (...a: unknown[]) => mockToast.success(...a), error: (...a: unknown[]) => mockToast.error(...a) },
}));

const DESCRUDE = { id: 1, codigo: 'DESCRUDE', nombre: 'Descrude', tipo: 'pre_tratamiento', activo: true };
const LAVADO = { id: 2, codigo: 'LAVADO', nombre: 'Lavado reductivo', tipo: 'lavado', activo: true };
const MAQUINA = { id: 9, nombre: 'Jet 1' };

function montar(maquina: { id: number; nombre: string } | null = MAQUINA) {
  const onClose = vi.fn();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ProcesosMaquinaDialog maquina={maquina} onClose={onClose} />
    </QueryClientProvider>,
  );
  return { onClose };
}

beforeEach(() => {
  [mockListar, mockAsignar, mockDeMaquina, mockToast.success, mockToast.error].forEach((m) => m.mockReset());
  mockListar.mockResolvedValue([DESCRUDE, LAVADO]);
  mockDeMaquina.mockResolvedValue([DESCRUDE]);
});

describe('ProcesosMaquinaDialog', () => {
  it('dado sin maquina cuando renderiza entonces no abre ni consulta', () => {
    montar(null);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(mockListar).not.toHaveBeenCalled();
  });

  it('dado una maquina cuando abre entonces ofrece los procesos activos y marca los asignados', async () => {
    montar();
    expect(await screen.findByLabelText(/DESCRUDE/)).toBeChecked();
    expect(screen.getByLabelText(/LAVADO/)).not.toBeChecked();
    expect(mockListar).toHaveBeenCalledWith({ soloActivos: true });
    expect(mockDeMaquina).toHaveBeenCalledWith(9);
  });

  it('dado cambios en la seleccion cuando guarda entonces reemplaza los procesos y cierra', async () => {
    mockAsignar.mockResolvedValue([LAVADO]);
    const { onClose } = montar();
    await userEvent.click(await screen.findByLabelText(/DESCRUDE/));
    await userEvent.click(screen.getByLabelText(/LAVADO/));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar procesos' }));

    await waitFor(() => expect(mockAsignar).toHaveBeenCalledWith(9, [2]));
    expect(mockToast.success).toHaveBeenCalledWith('Procesos de Jet 1 actualizados.');
    expect(onClose).toHaveBeenCalled();
  });

  it('dado el dialogo abierto cuando pulsa Cancelar o Escape entonces cierra sin guardar', async () => {
    const { onClose } = montar();
    await screen.findByLabelText(/DESCRUDE/);
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onClose).toHaveBeenCalledTimes(1);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(2);
    expect(mockAsignar).not.toHaveBeenCalled();
  });

  it('dado rechazo del servidor cuando guarda entonces muestra el error y no cierra', async () => {
    mockAsignar.mockRejectedValue({ response: { status: 400, data: {
      success: false, error: { code: 400, message: 'procesos: Algún proceso no existe, está inactivo o es de otra sede.' },
    } } });
    const { onClose } = montar();
    await screen.findByLabelText(/DESCRUDE/);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar procesos' }));

    await waitFor(() => expect(mockToast.error).toHaveBeenCalledWith(
      'procesos: Algún proceso no existe, está inactivo o es de otra sede.'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('dado catalogo vacio cuando abre entonces indica que el tintorero debe crear procesos', async () => {
    mockListar.mockResolvedValue([]);
    mockDeMaquina.mockResolvedValue([]);
    montar();
    expect(await screen.findByText(/No hay procesos activos/)).toBeInTheDocument();
  });
});
