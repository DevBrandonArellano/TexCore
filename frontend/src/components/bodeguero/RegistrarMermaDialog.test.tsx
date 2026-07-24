import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RegistrarMermaDialog } from './RegistrarMermaDialog';
import type { Producto, Bodega } from '../../lib/types';

const mockPost = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    post: (...args: any[]) => mockPost(...args),
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

const PRODUCTOS: Producto[] = [
  { id: 1, codigo: 'PROD-1', descripcion: 'Hilo de Algodón', tipo: 'hilo', unidad_medida: 'kg' } as Producto,
];
const BODEGAS: Bodega[] = [{ id: 1, nombre: 'Bodega Central' } as Bodega];

const selectComboboxOption = async (
  user: ReturnType<typeof userEvent.setup>,
  placeholderText: string,
  optionName: string | RegExp
) => {
  const triggers = screen.getAllByRole('combobox');
  const trigger = triggers.find((el) => el.textContent?.includes(placeholderText));
  if (!trigger) throw new Error(`No combobox found with placeholder "${placeholderText}"`);
  await user.click(trigger);
  const option = await screen.findByRole('option', { name: optionName });
  await user.click(option);
};

function renderComponent(props: Partial<Parameters<typeof RegistrarMermaDialog>[0]> = {}) {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    productos: PRODUCTOS,
    bodegas: BODEGAS,
    onSuccess: vi.fn(),
  };
  return render(<RegistrarMermaDialog {...defaultProps} {...props} />);
}

describe('RegistrarMermaDialog', () => {
  beforeEach(() => {
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado open=false cuando se renderiza entonces no muestra el dialogo', () => {
    renderComponent({ open: false });
    expect(screen.queryByText('Registrar Merma')).not.toBeInTheDocument();
  });

  it('dado el dialogo abierto cuando se renderiza entonces muestra el formulario', () => {
    renderComponent();
    expect(screen.getByRole('heading', { name: 'Registrar Merma' })).toBeInTheDocument();
    expect(screen.getByLabelText('Cantidad')).toBeInTheDocument();
    expect(screen.getByLabelText('Motivo de la Merma')).toBeInTheDocument();
  });

  it('dado campos vacios cuando intenta registrar entonces no llama a la API', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole('button', { name: 'Registrar Merma' }));

    expect(mockPost).not.toHaveBeenCalled();
    expect(toastErrorMock).toHaveBeenCalled();
  });

  it('dado cantidad y bodega pero sin motivo cuando intenta registrar entonces bloquea con toast', async () => {
    const user = userEvent.setup();
    renderComponent();

    await selectComboboxOption(user, 'Selecciona un producto', 'Hilo de Algodón');
    await selectComboboxOption(user, 'Selecciona una bodega', 'Bodega Central');
    await user.type(screen.getByLabelText('Cantidad'), '15');
    await user.click(screen.getByRole('button', { name: 'Registrar Merma' }));

    expect(mockPost).not.toHaveBeenCalled();
    expect(toastErrorMock).toHaveBeenCalledWith('Debes indicar el motivo de la merma.');
  });

  it('dado datos validos cuando registra entonces llama a la API con tipo_movimiento MERMA', async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    const onOpenChange = vi.fn();
    renderComponent({ onSuccess, onOpenChange });

    await selectComboboxOption(user, 'Selecciona un producto', 'Hilo de Algodón');
    await selectComboboxOption(user, 'Selecciona una bodega', 'Bodega Central');
    await user.type(screen.getByLabelText('Cantidad'), '15');
    await user.type(screen.getByLabelText('Motivo de la Merma'), 'Hilo dañado por humedad');
    await user.click(screen.getByRole('button', { name: 'Registrar Merma' }));

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith('/inventory/movimientos/', {
        tipo_movimiento: 'MERMA',
        producto: 1,
        bodega_origen: 1,
        cantidad: 15,
        observaciones: 'Hilo dañado por humedad',
      })
    );
    expect(toastSuccessMock).toHaveBeenCalledWith('Merma registrada — stock descontado.');
    expect(onSuccess).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('dado fallo de la API cuando registra entonces muestra un toast de error', async () => {
    mockPost.mockRejectedValueOnce({ response: { data: { error: 'Stock insuficiente. Disponible: 5' } } });
    const user = userEvent.setup();
    renderComponent();

    await selectComboboxOption(user, 'Selecciona un producto', 'Hilo de Algodón');
    await selectComboboxOption(user, 'Selecciona una bodega', 'Bodega Central');
    await user.type(screen.getByLabelText('Cantidad'), '999');
    await user.type(screen.getByLabelText('Motivo de la Merma'), 'Prueba de error');
    await user.click(screen.getByRole('button', { name: 'Registrar Merma' }));

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith('Error', { description: 'Stock insuficiente. Disponible: 5' })
    );
  });

  it('dado clic en cancelar cuando el usuario cierra el dialogo entonces llama a onOpenChange sin llamar a la API', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderComponent({ onOpenChange });

    await user.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockPost).not.toHaveBeenCalled();
  });
});
