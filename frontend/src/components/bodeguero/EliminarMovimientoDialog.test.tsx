import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EliminarMovimientoDialog } from './EliminarMovimientoDialog';

const mockDelete = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    delete: (...args: any[]) => mockDelete(...args),
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

const MOVIMIENTO = {
  id: 42,
  producto_nombre: 'Hilo de Algodón',
  tipo_movimiento: 'MERMA',
  cantidad: '15.00',
};

function renderComponent(props: Partial<Parameters<typeof EliminarMovimientoDialog>[0]> = {}) {
  const defaultProps = {
    movimiento: MOVIMIENTO,
    open: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
  };
  return render(<EliminarMovimientoDialog {...defaultProps} {...props} />);
}

describe('EliminarMovimientoDialog', () => {
  beforeEach(() => {
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado un movimiento nulo cuando se renderiza entonces no muestra el dialogo', () => {
    renderComponent({ movimiento: null });
    expect(screen.queryByText('Eliminar Movimiento')).not.toBeInTheDocument();
  });

  it('dado un movimiento existente cuando abre el dialogo entonces muestra su resumen', () => {
    renderComponent();
    expect(screen.getByText(/Hilo de Algodón — MERMA \(15\.00\)/)).toBeInTheDocument();
  });

  it('dado justificacion vacia cuando confirma entonces no llama a la API', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole('button', { name: 'Eliminar y Revertir' }));

    expect(mockDelete).not.toHaveBeenCalled();
    expect(toastErrorMock).toHaveBeenCalledWith(
      'Debes indicar la justificación para eliminar el movimiento.'
    );
  });

  it('dado justificacion valida cuando confirma entonces llama al DELETE con el body correcto', async () => {
    mockDelete.mockResolvedValueOnce({ status: 204 });
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    renderComponent({ onSuccess, onClose });

    await user.type(
      screen.getByLabelText('Justificación (Obligatoria)'),
      'Merma registrada por error de digitación'
    );
    await user.click(screen.getByRole('button', { name: 'Eliminar y Revertir' }));

    await waitFor(() =>
      expect(mockDelete).toHaveBeenCalledWith('/inventory/movimientos/42/', {
        data: { justificacion: 'Merma registrada por error de digitación' },
      })
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Movimiento eliminado — stock revertido.');
    expect(onSuccess).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('dado movimiento_id presente cuando confirma entonces lo usa en vez de id', async () => {
    mockDelete.mockResolvedValueOnce({ status: 204 });
    const user = userEvent.setup();
    renderComponent({ movimiento: { ...MOVIMIENTO, id: 42, movimiento_id: 7 } });

    await user.type(screen.getByLabelText('Justificación (Obligatoria)'), 'Ajuste de prueba');
    await user.click(screen.getByRole('button', { name: 'Eliminar y Revertir' }));

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/inventory/movimientos/7/', expect.anything()));
  });

  it('dado fallo por movimiento ligado a despacho cuando confirma entonces muestra el error del backend', async () => {
    mockDelete.mockRejectedValueOnce({
      response: { data: { error: 'Este movimiento pertenece a un despacho; revierta el despacho completo.' } },
    });
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText('Justificación (Obligatoria)'), 'Intento no permitido');
    await user.click(screen.getByRole('button', { name: 'Eliminar y Revertir' }));

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith(
        'Este movimiento pertenece a un despacho; revierta el despacho completo.'
      )
    );
  });

  it('dado clic en cancelar cuando el usuario cierra el dialogo entonces llama a onClose sin llamar a la API', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderComponent({ onClose });

    await user.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(onClose).toHaveBeenCalled();
    expect(mockDelete).not.toHaveBeenCalled();
  });
});
