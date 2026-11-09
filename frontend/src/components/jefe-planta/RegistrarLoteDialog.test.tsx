/**
 * RegistrarLoteDialog: registro de un lote de producción desde la orden (Jefe de Planta).
 *
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): formulario completo / sin código o peso / sin horas;
 *   respuesta exitosa / con error.
 * - Análisis de valores límite (BVA): hora final igual a la de inicio (rechazada) y un minuto
 *   después (aceptada).
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RegistrarLoteDialog } from './RegistrarLoteDialog';
import type { Maquina, OrdenProduccion } from '../../lib/types';

const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({ default: { post: (...a: unknown[]) => mockPost(...a) } }));
const { mockToast } = vi.hoisted(() => ({ mockToast: { success: vi.fn(), error: vi.fn(), loading: vi.fn() } }));
vi.mock('sonner', () => ({ toast: mockToast }));

const ORDEN = { id: 5, codigo: 'OP-5', producto_nombre: 'Tela azul', maquina_asignada: 2 } as unknown as OrdenProduccion;
const MAQUINAS = [{ id: 2, nombre: 'Jet 2' }] as unknown as Maquina[];

function montar() {
  const onLotCreated = vi.fn();
  const onOpenChange = vi.fn();
  render(<RegistrarLoteDialog open orden={ORDEN} maquinas={MAQUINAS} onLotCreated={onLotCreated} onOpenChange={onOpenChange} />);
  const escribir = (id: string, valor: string) => fireEvent.change(document.getElementById(id)!, { target: { value: valor } });
  const registrar = () => fireEvent.click(screen.getByRole('button', { name: 'Registrar Lote' }));
  return { onLotCreated, onOpenChange, escribir, registrar };
}

describe('RegistrarLoteDialog', () => {
  beforeEach(() => {
    mockPost.mockReset();
    mockToast.success.mockReset();
    mockToast.error.mockReset();
  });

  it('dado sin código ni peso cuando registra entonces pide los campos sin llamar al servidor', () => {
    const { registrar } = montar();
    registrar();
    expect(mockToast.error).toHaveBeenCalledWith('El código del lote y el peso producido son requeridos.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado hora de inicio vacía cuando registra entonces pide las horas', () => {
    const { escribir, registrar } = montar();
    escribir('codigo_lote', 'L-1');
    escribir('peso_neto_producido', '50');
    escribir('hora_inicio', '');
    registrar();
    expect(mockToast.error).toHaveBeenCalledWith('La hora de inicio y la hora final son requeridas.');
  });

  it('dado hora final igual a la de inicio cuando registra entonces la rechaza', () => {
    const { escribir, registrar } = montar();
    escribir('codigo_lote', 'L-1');
    escribir('peso_neto_producido', '50');
    escribir('hora_inicio', '2026-10-27T13:00');
    escribir('hora_final', '2026-10-27T13:00');
    registrar();
    expect(mockToast.error).toHaveBeenCalledWith('La hora final debe ser posterior a la hora de inicio.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado datos válidos un minuto después cuando registra entonces envía en ISO, avisa y cierra', async () => {
    mockPost.mockResolvedValueOnce({});
    const { escribir, registrar, onLotCreated, onOpenChange } = montar();
    escribir('codigo_lote', 'L-1');
    escribir('peso_neto_producido', '50');
    escribir('hora_inicio', '2026-10-27T13:00');
    escribir('hora_final', '2026-10-27T13:01');
    registrar();
    await waitFor(() => expect(onLotCreated).toHaveBeenCalled());
    expect(mockPost).toHaveBeenCalledWith('/ordenes-produccion/5/registrar-lote/', expect.objectContaining({
      codigo_lote: 'L-1', peso_neto_producido: '50', maquina: '2',
      hora_inicio: new Date('2026-10-27T13:00').toISOString(), hora_final: new Date('2026-10-27T13:01').toISOString(),
    }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('dado error del servidor cuando registra entonces muestra su mensaje y no cierra', async () => {
    mockPost.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'Código de lote duplicado.' } } });
    const { escribir, registrar, onOpenChange } = montar();
    escribir('codigo_lote', 'L-1');
    escribir('peso_neto_producido', '50');
    registrar();
    await waitFor(() => expect(mockToast.error).toHaveBeenCalled());
    expect(mockToast.error.mock.calls[0][0]).toContain('Código de lote duplicado.');
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it('dado cancelar cuando se pulsa entonces cierra sin registrar', () => {
    const { onOpenChange } = montar();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockPost).not.toHaveBeenCalled();
  });
});
