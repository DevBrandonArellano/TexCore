/**
 * useMaquinaActions: editar, activar/desactivar y rechazar lotes desde el panel del Jefe de Área.
 *
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): máquina operativa / inactiva; petición exitosa / con error.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useMaquinaActions } from './useMaquinaActions';
import type { Maquina } from '../../lib/types';

const mockPatch = vi.fn();
const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { patch: (...a: unknown[]) => mockPatch(...a), post: (...a: unknown[]) => mockPost(...a) },
}));
const { mockToast } = vi.hoisted(() => ({ mockToast: { success: vi.fn(), error: vi.fn(), loading: vi.fn() } }));
vi.mock('sonner', () => ({ toast: mockToast }));

const maquina = (estado: string) => ({ id: 7, nombre: 'Jet 1', estado }) as unknown as Maquina;

describe('useMaquinaActions', () => {
  beforeEach(() => {
    mockPatch.mockReset();
    mockPost.mockReset();
    mockToast.success.mockReset();
    mockToast.error.mockReset();
  });

  it('dado máquina operativa cuando alterna entonces la pasa a inactiva y recarga', async () => {
    const recargar = vi.fn();
    mockPatch.mockResolvedValueOnce({});
    const { result } = renderHook(() => useMaquinaActions(recargar));
    await act(() => result.current.handleToggleEstadoMaquina(maquina('operativa')));
    expect(mockPatch).toHaveBeenCalledWith('/maquinas/7/', { estado: 'inactiva' });
    expect(mockToast.success).toHaveBeenCalledWith('Máquina Jet 1 ahora está inactiva.');
    expect(recargar).toHaveBeenCalled();
  });

  it('dado máquina inactiva cuando alterna entonces la pasa a operativa', async () => {
    mockPatch.mockResolvedValueOnce({});
    const { result } = renderHook(() => useMaquinaActions(vi.fn()));
    await act(() => result.current.handleToggleEstadoMaquina(maquina('inactiva')));
    expect(mockPatch).toHaveBeenCalledWith('/maquinas/7/', { estado: 'operativa' });
  });

  it('dado error del servidor cuando alterna entonces avisa sin recargar', async () => {
    const recargar = vi.fn();
    mockPatch.mockRejectedValueOnce(new Error('500'));
    const { result } = renderHook(() => useMaquinaActions(recargar));
    await act(() => result.current.handleToggleEstadoMaquina(maquina('operativa')));
    expect(mockToast.error).toHaveBeenCalledWith('Error al cambiar el estado de la máquina.');
    expect(recargar).not.toHaveBeenCalled();
  });

  it('dado editar una máquina cuando se llama entonces la selecciona y abre el diálogo', () => {
    const { result } = renderHook(() => useMaquinaActions(vi.fn()));
    act(() => result.current.handleEditMaquina(maquina('operativa')));
    expect(result.current.selectedMaquina?.id).toBe(7);
    expect(result.current.isMaquinaDialogOpen).toBe(true);
  });

  it('dado rechazo exitoso o con error cuando rechaza un lote entonces devuelve si se rechazó', async () => {
    const { result } = renderHook(() => useMaquinaActions(vi.fn()));
    mockPost.mockResolvedValueOnce({});
    await expect(result.current.handleRechazarLote(3, '  mancha  ')).resolves.toBe(true);
    expect(mockPost).toHaveBeenCalledWith('/lotes-produccion/3/rechazar/', { justificacion: 'mancha' });
    mockPost.mockRejectedValueOnce(new Error('400'));
    await expect(result.current.handleRechazarLote(3, 'x')).resolves.toBe(false);
  });
});
