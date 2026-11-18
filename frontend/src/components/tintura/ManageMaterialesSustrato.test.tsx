/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): materiales activos e inactivos / crear / renombrar.
 * - Análisis de valores límite (BVA): nombre vacío y de 1 carácter (mínimo 2).
 * - Transición de estados (STT): activo → inactivo → activo.
 * - Caja blanca (CB): ramas de error — un error del servidor.
 * - Auditoría: renombrar, activar y desactivar exigen justificación; crear no.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageMaterialesSustrato } from './ManageMaterialesSustrato';

const mockApi = { listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn() };
vi.mock('../../lib/api/materialesSustratoApi', () => ({
  materialesSustratoApi: {
    listar: (...a: unknown[]) => mockApi.listar(...a),
    crear: (...a: unknown[]) => mockApi.crear(...a),
    actualizar: (...a: unknown[]) => mockApi.actualizar(...a),
  },
}));
const mockToast = { success: vi.fn(), error: vi.fn() };
vi.mock('sonner', () => ({
  toast: { success: (...a: unknown[]) => mockToast.success(...a), error: (...a: unknown[]) => mockToast.error(...a) },
}));

const ALGODON = { id: 1, clave: 'algodon', nombre: 'Algodón', activo: true, sede: 1 };
const LINO = { id: 2, clave: 'lino', nombre: 'Lino', activo: false, sede: 1 };
const user = () => userEvent.setup({ pointerEventsCheck: 0 });

describe('ManageMaterialesSustrato', () => {
  beforeEach(() => {
    Object.values(mockApi).forEach((m) => m.mockReset());
    mockToast.success.mockReset();
    mockToast.error.mockReset();
    mockApi.listar.mockResolvedValue([ALGODON, LINO]);
  });

  it('dado materiales activos e inactivos cuando carga entonces los lista con su estado', async () => {
    render(<ManageMaterialesSustrato />);
    const fila = (await screen.findByText('Algodón')).closest('tr') as HTMLElement;
    expect(within(fila).getByText('Activo')).toBeInTheDocument();
    const filaLino = screen.getByText('Lino').closest('tr') as HTMLElement;
    expect(within(filaLino).getByText('Inactivo')).toBeInTheDocument();
    expect(mockApi.listar).toHaveBeenCalledWith();
  });

  it('dado un nombre válido cuando crea entonces lo envía, avisa y notifica el cambio', async () => {
    mockApi.crear.mockResolvedValue({ id: 3, clave: 'seda', nombre: 'Seda', activo: true, sede: 1 });
    const onCambio = vi.fn();
    render(<ManageMaterialesSustrato onCatalogoCambiado={onCambio} />);
    await screen.findByText('Algodón');

    await user().click(screen.getByRole('button', { name: /Nuevo material/ }));
    await user().type(screen.getByLabelText('Nombre'), '  Seda  ');
    await user().click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockApi.crear).toHaveBeenCalledWith({ nombre: 'Seda' }));
    expect(mockToast.success).toHaveBeenCalledWith('Material creado.');
    expect(onCambio).toHaveBeenCalled();
  });

  it.each(['', 'L'])('dado el nombre "%s" cuando guarda entonces no lo envía y avisa', async (nombre) => {
    render(<ManageMaterialesSustrato />);
    await screen.findByText('Algodón');
    await user().click(screen.getByRole('button', { name: /Nuevo material/ }));
    if (nombre) await user().type(screen.getByLabelText('Nombre'), nombre);
    await user().click(screen.getByRole('button', { name: 'Guardar' }));

    expect(mockApi.crear).not.toHaveBeenCalled();
    expect(mockToast.error).toHaveBeenCalledWith('El nombre debe tener al menos 2 caracteres.');
  });

  it('dado un material cuando lo renombra con justificación entonces envía el nombre y el motivo', async () => {
    mockApi.actualizar.mockResolvedValue({ ...ALGODON, nombre: 'Algodón peinado' });
    render(<ManageMaterialesSustrato />);
    await screen.findByText('Algodón');

    await user().click(screen.getByRole('button', { name: 'Editar Algodón' }));
    const campo = screen.getByLabelText('Nombre');
    await user().clear(campo);
    await user().type(campo, 'Algodón peinado');
    await user().type(screen.getByLabelText('Justificación'), 'Nombre del proveedor');
    await user().click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockApi.actualizar).toHaveBeenCalledWith(
      1, { nombre: 'Algodón peinado', _justificacion_auditoria: 'Nombre del proveedor' },
    ));
    expect(mockToast.success).toHaveBeenCalledWith('Material actualizado.');
  });

  it('dado un material cuando lo renombra sin justificación entonces no lo envía y avisa', async () => {
    render(<ManageMaterialesSustrato />);
    await screen.findByText('Algodón');

    await user().click(screen.getByRole('button', { name: 'Editar Algodón' }));
    await user().type(screen.getByLabelText('Nombre'), ' peinado');
    await user().click(screen.getByRole('button', { name: 'Guardar' }));

    expect(mockApi.actualizar).not.toHaveBeenCalled();
    expect(mockToast.error).toHaveBeenCalledWith('Indique la justificación del cambio: queda en la auditoría.');
  });

  it('dado un material nuevo cuando abre el formulario entonces no pide justificación', async () => {
    render(<ManageMaterialesSustrato />);
    await screen.findByText('Algodón');
    await user().click(screen.getByRole('button', { name: /Nuevo material/ }));
    expect(screen.queryByLabelText('Justificación')).not.toBeInTheDocument();
  });

  it('dado un material activo e inactivo cuando cambia su estado con justificación entonces lo desactiva o activa', async () => {
    mockApi.actualizar.mockResolvedValue({});
    render(<ManageMaterialesSustrato />);
    await screen.findByText('Algodón');

    await user().click(screen.getByRole('button', { name: 'Desactivar Algodón' }));
    await user().type(screen.getByLabelText('Justificación'), 'Ya no se compra');
    await user().click(screen.getByRole('button', { name: 'Confirmar' }));
    await waitFor(() => expect(mockApi.actualizar).toHaveBeenCalledWith(
      1, { activo: false, _justificacion_auditoria: 'Ya no se compra' },
    ));

    await user().click(screen.getByRole('button', { name: 'Activar Lino' }));
    await user().type(screen.getByLabelText('Justificación'), 'Vuelve a usarse');
    await user().click(screen.getByRole('button', { name: 'Confirmar' }));
    await waitFor(() => expect(mockApi.actualizar).toHaveBeenCalledWith(
      2, { activo: true, _justificacion_auditoria: 'Vuelve a usarse' },
    ));
  });

  it('dado un cambio de estado sin justificación cuando confirma entonces no lo envía', async () => {
    render(<ManageMaterialesSustrato />);
    await screen.findByText('Algodón');

    await user().click(screen.getByRole('button', { name: 'Desactivar Algodón' }));
    await user().click(screen.getByRole('button', { name: 'Confirmar' }));

    expect(mockApi.actualizar).not.toHaveBeenCalled();
    expect(mockToast.error).toHaveBeenCalledWith('Indique la justificación del cambio: queda en la auditoría.');
  });

  it('dado un error del servidor cuando crea entonces muestra el mensaje y no cierra el formulario', async () => {
    mockApi.crear.mockRejectedValue({ response: { data: { detail: 'Ya existe un material equivalente.' } } });
    render(<ManageMaterialesSustrato />);
    await screen.findByText('Algodón');

    await user().click(screen.getByRole('button', { name: /Nuevo material/ }));
    await user().type(screen.getByLabelText('Nombre'), 'Algodon');
    await user().click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(mockToast.error).toHaveBeenCalled());
    expect(screen.getByLabelText('Nombre')).toBeInTheDocument();
  });
});
