import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

import { AuditoriaDialog } from './AuditoriaDialog';

const mockGet = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
  },
}));

const LOG_1 = {
  id: 1,
  fecha_modificacion: '2026-07-10T15:30:00Z',
  usuario_modificador_nombre: 'Juan Pérez',
  campo_modificado: 'cantidad',
  valor_anterior: '10',
  valor_nuevo: '25',
  razon_cambio: 'Corrección de conteo físico',
};

describe('AuditoriaDialog', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('dado open en false entonces no renderiza el contenido del dialogo', () => {
    render(
      <AuditoriaDialog movimientoId={1} open={false} onClose={vi.fn()} />,
    );

    expect(screen.queryByText('Historial de Cambios')).not.toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado open en true y movimientoId cuando monta entonces consulta la auditoria del movimiento', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });

    render(
      <AuditoriaDialog movimientoId={42} open={true} onClose={vi.fn()} />,
    );

    expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith('/inventory/movimientos/42/auditoria/'),
    );
  });

  it('dado movimientoId nulo cuando abre entonces no realiza ninguna peticion', () => {
    render(
      <AuditoriaDialog movimientoId={null} open={true} onClose={vi.fn()} />,
    );

    expect(screen.getByText('Historial de Cambios')).toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado que la peticion esta en curso entonces muestra los skeletons de carga', async () => {
    let resolveRequest: (value: any) => void = () => {};
    mockGet.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }),
    );

    render(
      <AuditoriaDialog movimientoId={7} open={true} onClose={vi.fn()} />,
    );

    expect(document.querySelectorAll('[data-slot="skeleton"]')).toHaveLength(3);

    resolveRequest({ data: [] });
    await waitFor(() =>
      expect(screen.getByText('No hay historial de cambios registrado.')).toBeInTheDocument(),
    );
  });

  it('dado sin registros de auditoria entonces muestra el mensaje de historial vacio', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });

    render(
      <AuditoriaDialog movimientoId={7} open={true} onClose={vi.fn()} />,
    );

    await waitFor(() =>
      expect(screen.getByText('No hay historial de cambios registrado.')).toBeInTheDocument(),
    );
  });

  it('dado registros de auditoria cuando cargan entonces muestra usuario, campo, valores y razon del cambio', async () => {
    mockGet.mockResolvedValueOnce({ data: [LOG_1] });

    render(
      <AuditoriaDialog movimientoId={7} open={true} onClose={vi.fn()} />,
    );

    await waitFor(() => expect(screen.getByText('Juan Pérez')).toBeInTheDocument());
    expect(screen.getByText('cantidad')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('Corrección de conteo físico')).toBeInTheDocument();
    const expectedFecha = format(new Date(LOG_1.fecha_modificacion), 'dd/MM/yy HH:mm', { locale: es });
    expect(screen.getByText(expectedFecha)).toBeInTheDocument();
  });

  it('dado un error en la peticion entonces deja de cargar y muestra el mensaje de historial vacio', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGet.mockRejectedValueOnce(new Error('network error'));

    render(
      <AuditoriaDialog movimientoId={7} open={true} onClose={vi.fn()} />,
    );

    await waitFor(() =>
      expect(screen.getByText('No hay historial de cambios registrado.')).toBeInTheDocument(),
    );
    expect(consoleErrorSpy).toHaveBeenCalledWith('Error fetching auditoria:', expect.any(Error));

    consoleErrorSpy.mockRestore();
  });
});
