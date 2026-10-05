import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageProcesosTintoreria } from './ManageProcesosTintoreria';

const mockApi = { listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn() };
vi.mock('../../lib/api/procesosTintoreriaApi', () => ({
  procesosTintoreriaApi: {
    listar: (...a: unknown[]) => mockApi.listar(...a),
    crear: (...a: unknown[]) => mockApi.crear(...a),
    actualizar: (...a: unknown[]) => mockApi.actualizar(...a),
  },
}));
const mockToast = { success: vi.fn(), error: vi.fn() };
vi.mock('sonner', () => ({
  toast: { success: (...a: unknown[]) => mockToast.success(...a), error: (...a: unknown[]) => mockToast.error(...a) },
}));

// Polyfills para Radix Select en jsdom
global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

const DESCRUDE = {
  id: 1, codigo: 'DESCRUDE', nombre: 'Descrude', tipo: 'pre_tratamiento', tipo_display: 'Pre-Tratamiento',
  descripcion: '', activo: true, sede: 1,
};
const LAVADO = {
  id: 2, codigo: 'LAVADO', nombre: 'Lavado reductivo', tipo: 'lavado', tipo_display: 'Lavado',
  descripcion: '', activo: false, sede: 1,
};
const user = () => userEvent.setup({ pointerEventsCheck: 0 });

describe('ManageProcesosTintoreria', () => {
  beforeEach(() => {
    Object.values(mockApi).forEach((m) => m.mockReset());
    mockToast.success.mockReset();
    mockToast.error.mockReset();
    mockApi.listar.mockResolvedValue([DESCRUDE, LAVADO]);
  });

  it('dado procesos activos e inactivos cuando carga entonces los lista con su estado', async () => {
    render(<ManageProcesosTintoreria />);
    const fila = (await screen.findByText('DESCRUDE')).closest('tr') as HTMLElement;
    expect(within(fila).getByText('Activo')).toBeInTheDocument();
    const filaLavado = screen.getByText('LAVADO').closest('tr') as HTMLElement;
    expect(within(filaLavado).getByText('Inactivo')).toBeInTheDocument();
    // Incluye inactivos: el catálogo completo de la sede.
    expect(mockApi.listar).toHaveBeenCalledWith();
  });

  it('dado código vacío cuando crea entonces avisa y no llama a la API', async () => {
    const u = user();
    render(<ManageProcesosTintoreria />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: /Nuevo proceso/ }));
    await u.type(screen.getByLabelText('Nombre'), 'Jabonado');
    await u.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(mockToast.error).toHaveBeenCalledWith('El código y el nombre son requeridos.');
    expect(mockApi.crear).not.toHaveBeenCalled();
  });

  it('dado código, nombre y tipo cuando crea entonces envía el código en mayúsculas y recarga', async () => {
    const u = user();
    mockApi.crear.mockResolvedValue({ ...DESCRUDE, id: 3 });
    render(<ManageProcesosTintoreria />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: /Nuevo proceso/ }));
    await u.type(screen.getByLabelText('Código'), ' jabonado ');
    await u.type(screen.getByLabelText('Nombre'), 'Jabonado');
    await u.click(screen.getByRole('combobox', { name: 'Tipo' }));
    await u.click(await screen.findByRole('option', { name: 'Lavado' }));
    await u.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockApi.crear).toHaveBeenCalledWith({
      codigo: 'JABONADO', nombre: 'Jabonado', tipo: 'lavado', descripcion: '',
    }));
    await waitFor(() => expect(mockApi.listar).toHaveBeenCalledTimes(2));
    expect(mockToast.success).toHaveBeenCalledWith('Proceso creado.');
  });

  it('dado un proceso cuando edita entonces el código queda bloqueado y solo envía los cambios permitidos', async () => {
    const u = user();
    mockApi.actualizar.mockResolvedValue(DESCRUDE);
    render(<ManageProcesosTintoreria />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: 'Editar DESCRUDE' }));

    expect(screen.getByLabelText('Código')).toBeDisabled();
    await u.clear(screen.getByLabelText('Nombre'));
    await u.type(screen.getByLabelText('Nombre'), 'Descrude alcalino');
    await u.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockApi.actualizar).toHaveBeenCalledWith(1, {
      nombre: 'Descrude alcalino', tipo: 'pre_tratamiento', descripcion: '',
    }));
  });

  it('dado un proceso activo cuando lo desactiva entonces envía activo false y recarga', async () => {
    const u = user();
    mockApi.actualizar.mockResolvedValue({ ...DESCRUDE, activo: false });
    render(<ManageProcesosTintoreria />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: 'Desactivar DESCRUDE' }));
    await waitFor(() => expect(mockApi.actualizar).toHaveBeenCalledWith(1, { activo: false }));
    await waitFor(() => expect(mockApi.listar).toHaveBeenCalledTimes(2));
  });

  it('dado un cambio guardado cuando termina entonces avisa al panel para refrescar las recetas', async () => {
    const u = user();
    const onCatalogoCambiado = vi.fn();
    mockApi.actualizar.mockResolvedValue({ ...DESCRUDE, activo: false });
    render(<ManageProcesosTintoreria onCatalogoCambiado={onCatalogoCambiado} />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: 'Desactivar DESCRUDE' }));
    await waitFor(() => expect(onCatalogoCambiado).toHaveBeenCalledTimes(1));
  });

  it('dado un error del servidor cuando desactiva entonces muestra el mensaje y no avisa al panel', async () => {
    const u = user();
    const onCatalogoCambiado = vi.fn();
    mockApi.actualizar.mockRejectedValue({ response: { status: 403, data: {
      success: false, error: { code: 403, message: 'No tiene permiso para realizar esta acción.' },
    } } });
    render(<ManageProcesosTintoreria onCatalogoCambiado={onCatalogoCambiado} />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: 'Desactivar DESCRUDE' }));
    await waitFor(() => expect(mockToast.error).toHaveBeenCalledWith('No tiene permiso para realizar esta acción.'));
    expect(onCatalogoCambiado).not.toHaveBeenCalled();
  });

  it('dado una descripcion escrita cuando crea entonces la envia recortada', async () => {
    const u = user();
    mockApi.crear.mockResolvedValue({ ...DESCRUDE, id: 4 });
    render(<ManageProcesosTintoreria />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: /Nuevo proceso/ }));
    await u.type(screen.getByLabelText('Código'), 'SUAVIZADO');
    await u.type(screen.getByLabelText('Nombre'), 'Suavizado');
    await u.type(screen.getByLabelText('Descripción'), '  Con silicona  ');
    await u.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(mockApi.crear).toHaveBeenCalledWith(
      expect.objectContaining({ descripcion: 'Con silicona' })));
  });

  it('dado el formulario abierto cuando pulsa Cancelar entonces cierra sin llamar a la API', async () => {
    const u = user();
    render(<ManageProcesosTintoreria />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: /Nuevo proceso/ }));
    await u.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(mockApi.crear).not.toHaveBeenCalled();
  });

  it('dado un proceso inactivo cuando lo activa entonces envía activo true', async () => {
    const u = user();
    mockApi.actualizar.mockResolvedValue({ ...LAVADO, activo: true });
    render(<ManageProcesosTintoreria />);
    await screen.findByText('LAVADO');
    await u.click(screen.getByRole('button', { name: 'Activar LAVADO' }));
    await waitFor(() => expect(mockApi.actualizar).toHaveBeenCalledWith(2, { activo: true }));
  });

  it('dado código repetido cuando el servidor rechaza entonces muestra el error y no cierra el formulario', async () => {
    const u = user();
    mockApi.crear.mockRejectedValue({ response: { status: 400, data: {
      success: false, error: { code: 400, message: 'codigo: Ya existe un proceso con codigo "DESCRUDE" en esta sede.' },
    } } });
    render(<ManageProcesosTintoreria />);
    await screen.findByText('DESCRUDE');
    await u.click(screen.getByRole('button', { name: /Nuevo proceso/ }));
    await u.type(screen.getByLabelText('Código'), 'DESCRUDE');
    await u.type(screen.getByLabelText('Nombre'), 'Otro');
    await u.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockToast.error).toHaveBeenCalledWith(
      'codigo: Ya existe un proceso con codigo "DESCRUDE" en esta sede.'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
