import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditarMovimientoDialog } from './EditarMovimientoDialog';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
    put: (...args: any[]) => mockPut(...args),
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

const MOVIMIENTO_1 = {
  movimiento_id: 3,
  producto_nombre: 'Algodón Crudo',
  entrada: 50,
  documento_ref: 'DOC-1',
};

function renderComponent(props: Partial<Parameters<typeof EditarMovimientoDialog>[0]> = {}) {
  const defaultProps = {
    movimiento: MOVIMIENTO_1,
    open: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
  };
  return render(<EditarMovimientoDialog {...defaultProps} {...props} />);
}

describe('EditarMovimientoDialog', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
    mockPut.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado un movimiento nulo cuando se renderiza entonces no muestra el dialogo', () => {
    renderComponent({ movimiento: null });
    expect(screen.queryByText('Editar Entrada de Inventario')).not.toBeInTheDocument();
  });

  it('dado un movimiento existente cuando abre el dialogo entonces precarga los campos', () => {
    renderComponent();

    expect(screen.getByLabelText('Producto')).toHaveValue('Algodón Crudo');
    expect(screen.getByLabelText('Cantidad (Entrada)')).toHaveValue(50);
    expect(screen.getByLabelText('Documento de Referencia')).toHaveValue('DOC-1');
    expect(screen.getByLabelText('Razón del Cambio (Obligatorio)')).toHaveValue('');
  });

  it('dado razon vacia cuando intenta guardar entonces el campo requerido bloquea el envio y no llama a la API', async () => {
    renderComponent();

    await userEvent.click(screen.getByRole('button', { name: 'Guardar Cambios' }));

    expect(mockPut).not.toHaveBeenCalled();
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it('dado razon con menos de 10 caracteres cuando intenta guardar entonces muestra error de validacion y no llama a la API', async () => {
    renderComponent();

    await userEvent.type(screen.getByLabelText('Razón del Cambio (Obligatorio)'), 'corta');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar Cambios' }));

    expect(toastErrorMock).toHaveBeenCalledWith(
      'Debes proporcionar una razón detallada del cambio (mínimo 10 caracteres).',
    );
    expect(mockPut).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando guarda entonces llama a la API con el payload correcto y muestra exito', async () => {
    mockPut.mockResolvedValueOnce({ data: {} });
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    renderComponent({ onSuccess, onClose });

    await userEvent.clear(screen.getByLabelText('Cantidad (Entrada)'));
    await userEvent.type(screen.getByLabelText('Cantidad (Entrada)'), '75.5');
    await userEvent.type(screen.getByLabelText('Documento de Referencia'), '-ACTUALIZADO');
    await userEvent.type(
      screen.getByLabelText('Razón del Cambio (Obligatorio)'),
      'Corrección por conteo físico',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Guardar Cambios' }));

    await waitFor(() =>
      expect(mockPut).toHaveBeenCalledWith('/inventory/movimientos/3/', {
        cantidad: 75.5,
        documento_ref: 'DOC-1-ACTUALIZADO',
        razon_cambio: 'Corrección por conteo físico',
      }),
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Movimiento actualizado con éxito');
    expect(onSuccess).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('dado movimiento con id generico cuando guarda entonces usa el id como fallback en la URL', async () => {
    mockPut.mockResolvedValueOnce({ data: {} });
    renderComponent({ movimiento: { id: 9, cantidad: 10, producto: 'Lana' } });

    await userEvent.type(
      screen.getByLabelText('Razón del Cambio (Obligatorio)'),
      'Ajuste manual de inventario',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Guardar Cambios' }));

    await waitFor(() =>
      expect(mockPut).toHaveBeenCalledWith('/inventory/movimientos/9/', expect.objectContaining({
        cantidad: 10,
      })),
    );
  });

  it('dado fallo de la API cuando guarda entonces muestra un toast de error con el mensaje del servidor', async () => {
    mockPut.mockRejectedValueOnce({ response: { data: { error: 'Stock insuficiente' } } });
    renderComponent();

    await userEvent.type(
      screen.getByLabelText('Razón del Cambio (Obligatorio)'),
      'Corrección por conteo físico',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Guardar Cambios' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Stock insuficiente'));
  });

  it('dado fallo de la API sin mensaje especifico cuando guarda entonces muestra un toast de error generico', async () => {
    mockPut.mockRejectedValueOnce(new Error('network error'));
    renderComponent();

    await userEvent.type(
      screen.getByLabelText('Razón del Cambio (Obligatorio)'),
      'Corrección por conteo físico',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Guardar Cambios' }));

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar el movimiento'),
    );
  });

  it('dado clic en cancelar cuando el usuario cierra el dialogo entonces llama a onClose sin llamar a la API', async () => {
    const onClose = vi.fn();
    renderComponent({ onClose });

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(onClose).toHaveBeenCalled();
    expect(mockPut).not.toHaveBeenCalled();
  });
});
