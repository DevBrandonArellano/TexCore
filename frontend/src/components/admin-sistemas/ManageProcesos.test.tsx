import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageProcesos } from './ManageProcesos';

const mockApi = { listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn() };
vi.mock('../../lib/api/procesosApi', () => ({
  procesosApi: {
    listar: (...a: unknown[]) => mockApi.listar(...a),
    crear: (...a: unknown[]) => mockApi.crear(...a),
    actualizar: (...a: unknown[]) => mockApi.actualizar(...a),
    eliminar: (...a: unknown[]) => mockApi.eliminar(...a),
  },
}));
const mockToast = { success: vi.fn(), error: vi.fn() };
vi.mock('sonner', () => ({ toast: { success: (...a: unknown[]) => mockToast.success(...a), error: (...a: unknown[]) => mockToast.error(...a) } }));

const TEJIDO = { id: 1, name: 'Tejido', description: 'Tejido de punto' };
const user = () => userEvent.setup({ pointerEventsCheck: 0 });

describe('ManageProcesos', () => {
  beforeEach(() => {
    Object.values(mockApi).forEach((m) => m.mockReset());
    mockToast.success.mockReset();
    mockToast.error.mockReset();
    mockApi.listar.mockResolvedValue([TEJIDO]);
  });

  it('dado procesos en el catálogo cuando carga entonces los lista con su descripción', async () => {
    render(<ManageProcesos />);
    expect(await screen.findByText('Tejido')).toBeInTheDocument();
    expect(screen.getByText('Tejido de punto')).toBeInTheDocument();
  });

  it('dado nombre vacío cuando crea entonces avisa y no llama a la API', async () => {
    const u = user();
    render(<ManageProcesos />);
    await screen.findByText('Tejido');
    await u.click(screen.getByRole('button', { name: /Nuevo proceso/ }));
    await u.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(mockToast.error).toHaveBeenCalled();
    expect(mockApi.crear).not.toHaveBeenCalled();
  });

  it('dado nombre y descripción cuando crea entonces lo guarda y recarga el catálogo', async () => {
    const u = user();
    mockApi.crear.mockResolvedValue({ id: 2, name: 'Teñido', description: '' });
    render(<ManageProcesos />);
    await screen.findByText('Tejido');
    await u.click(screen.getByRole('button', { name: /Nuevo proceso/ }));
    await u.type(screen.getByLabelText('Nombre'), 'Teñido');
    await u.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(mockApi.crear).toHaveBeenCalledWith({ name: 'Teñido', description: '' }));
    await waitFor(() => expect(mockApi.listar).toHaveBeenCalledTimes(2));
    expect(mockToast.success).toHaveBeenCalled();
  });

  it('dado un proceso cuando edita entonces envía los cambios', async () => {
    const u = user();
    mockApi.actualizar.mockResolvedValue({ ...TEJIDO, name: 'Tejido circular' });
    render(<ManageProcesos />);
    await screen.findByText('Tejido');
    await u.click(screen.getByRole('button', { name: 'Editar Tejido' }));
    const nombre = screen.getByLabelText('Nombre');
    await u.clear(nombre);
    await u.type(nombre, 'Tejido circular');
    await u.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(mockApi.actualizar).toHaveBeenCalledWith(1, { name: 'Tejido circular', description: 'Tejido de punto' }));
  });

  it('dado un proceso en uso cuando se confirma la eliminación entonces muestra el motivo del servidor', async () => {
    const u = user();
    mockApi.eliminar.mockRejectedValueOnce({
      response: { status: 409, data: { error: { message: 'No se puede eliminar: está en uso por operaciones.' } } },
    });
    render(<ManageProcesos />);
    await screen.findByText('Tejido');
    await u.click(screen.getByRole('button', { name: 'Eliminar Tejido' }));
    const dialogo = await screen.findByRole('alertdialog');
    await u.click(within(dialogo).getByRole('button', { name: 'Eliminar' }));
    await waitFor(() => expect(mockApi.eliminar).toHaveBeenCalledWith(1));
    await waitFor(() => expect(mockToast.error).toHaveBeenCalled());
    expect(String(mockToast.error.mock.calls[0])).toContain('en uso');
  });
});
