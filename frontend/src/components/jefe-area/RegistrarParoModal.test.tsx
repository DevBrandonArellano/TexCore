/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): el modal abierto / sin categoria seleccionada / categoria seleccionada e
 *   inicio valido / un error del backend.
 * - Caja blanca (CB): ramas de error — un error del backend.
 * - EP: sin máquina; categoría sin inicio; con fin, descripción y planificado; cancelar.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RegistrarParoModal } from './RegistrarParoModal';

const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { post: (...args: unknown[]) => mockPost(...args) },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => toastErrorMock(...args),
    success: (...args: unknown[]) => toastSuccessMock(...args),
  },
}));

global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

describe('RegistrarParoModal', () => {
  const onOpenChange = vi.fn();
  const onRegistrado = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('dado el modal abierto cuando renderiza entonces muestra el selector de categoria (Seis Grandes Perdidas)', () => {
    render(
      <RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={1} maquinaNombre="Máquina A" onRegistrado={onRegistrado} />
    );
    expect(screen.getByText('Registrar Paro de Máquina')).toBeInTheDocument();
    expect(screen.getByText(/Máquina A/)).toBeInTheDocument();
  });

  it('dado sin categoria seleccionada cuando se confirma entonces muestra un toast de error', async () => {
    render(
      <RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={1} maquinaNombre="Máquina A" onRegistrado={onRegistrado} />
    );
    await userEvent.click(screen.getByRole('button', { name: /Registrar Paro/ }));

    expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una categoría (reason code) para el paro.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado categoria seleccionada e inicio valido cuando se confirma entonces envia el POST correcto', async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    render(
      <RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={7} maquinaNombre="Máquina A" onRegistrado={onRegistrado} />
    );

    await userEvent.click(screen.getByRole('combobox'));
    await userEvent.click(await screen.findByRole('option', { name: /Avería/ }));

    const inicioInput = screen.getByLabelText(/Inicio/);
    await userEvent.type(inicioInput, '2026-01-01T08:00');

    await userEvent.click(screen.getByRole('button', { name: /Registrar Paro/ }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith('/paros-maquina/', expect.objectContaining({
        maquina: 7,
        categoria: 'AVERIA',
        inicio: '2026-01-01T08:00',
      }))
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Paro de máquina registrado correctamente.');
    expect(onRegistrado).toHaveBeenCalled();
  });

  it('dado un error del backend cuando falla el post entonces muestra un toast de error', async () => {
    mockPost.mockRejectedValueOnce({ response: { data: { error: { message: 'fin debe ser posterior a inicio' } } } });
    render(
      <RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={7} maquinaNombre="Máquina A" onRegistrado={onRegistrado} />
    );

    await userEvent.click(screen.getByRole('combobox'));
    await userEvent.click(await screen.findByRole('option', { name: /Avería/ }));
    const inicioInput = screen.getByLabelText(/Inicio/);
    await userEvent.type(inicioInput, '2026-01-01T08:00');

    await userEvent.click(screen.getByRole('button', { name: /Registrar Paro/ }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('fin debe ser posterior a inicio'));
  });

  async function elegirAveria() {
    await userEvent.click(screen.getByRole('combobox'));
    await userEvent.click(await screen.findByRole('option', { name: /Avería/ }));
  }

  it('dado sin máquina cuando se confirma entonces no hace nada', async () => {
    render(<RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={null} maquinaNombre="" onRegistrado={onRegistrado} />);
    await userEvent.click(screen.getByRole('button', { name: /Registrar Paro/ }));
    expect(toastErrorMock).not.toHaveBeenCalled();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado categoria sin inicio cuando se confirma entonces pide el inicio', async () => {
    render(<RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={7} maquinaNombre="Máquina A" onRegistrado={onRegistrado} />);
    await elegirAveria();
    await userEvent.click(screen.getByRole('button', { name: /Registrar Paro/ }));
    expect(toastErrorMock).toHaveBeenCalledWith('Indica la fecha/hora de inicio del paro.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado fin, descripcion y planificado cuando se confirma entonces los envia y cierra el modal', async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    render(<RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={7} maquinaNombre="Máquina A" onRegistrado={onRegistrado} />);
    await elegirAveria();
    await userEvent.type(screen.getByLabelText(/Inicio/), '2026-01-01T08:00');
    await userEvent.type(screen.getByLabelText(/Fin/), '2026-01-01T09:00');
    await userEvent.click(screen.getByLabelText(/Paro planificado/));
    await userEvent.type(screen.getByPlaceholderText(/rodamiento/), 'Cambio de correa');
    await userEvent.click(screen.getByRole('button', { name: /Registrar Paro/ }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/paros-maquina/', {
      maquina: 7, categoria: 'AVERIA', inicio: '2026-01-01T08:00', fin: '2026-01-01T09:00',
      planificado: true, descripcion: 'Cambio de correa',
    }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('dado cancelar cuando se pulsa entonces cierra sin registrar', async () => {
    render(<RegistrarParoModal open={true} onOpenChange={onOpenChange} maquinaId={7} maquinaNombre="" onRegistrado={onRegistrado} />);
    expect(screen.queryByText(/ — /)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockPost).not.toHaveBeenCalled();
  });
});

