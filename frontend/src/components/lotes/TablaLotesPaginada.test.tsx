import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { TablaLotesPaginada } from './TablaLotesPaginada';

vi.mock('../../lib/auth', () => ({ useAuth: () => ({ profile: { role: 'jefe_planta' } }) }));

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({ default: { get: (...args: unknown[]) => mockGet(...args) } }));

const LOTE = {
  id: 1, orden_produccion: 2, codigo_lote: 'L-1', peso_neto_producido: 40, operario: 3, maquina: 4,
  maquina_nombre: 'TIN-01', operario_nombre: 'op1', turno: 'Dia', hora_inicio: '', hora_final: '',
};
const pagina = (results: unknown[]) => ({ data: { count: results.length, next: null, previous: null, results } });

describe('TablaLotesPaginada', () => {
  beforeEach(() => mockGet.mockReset());

  it('dado sin lotes cuando carga entonces muestra el estado vacío sin controles', async () => {
    mockGet.mockResolvedValue(pagina([]));
    render(<TablaLotesPaginada />);
    expect(await screen.findByText('No hay lotes registrados.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Ir a la página')).not.toBeInTheDocument();
  });

  it('dado filtros y acciones extra cuando carga entonces los envía y pinta la acción por fila', async () => {
    mockGet.mockResolvedValue(pagina([LOTE]));
    render(<TablaLotesPaginada filtros={{ sede_id: 7 }} accionesExtra={(l) => <span>extra-{l.codigo_lote}</span>} />);
    expect(await screen.findByText('extra-L-1')).toBeInTheDocument();
    expect(screen.getByText('TIN-01')).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/', {
      params: { ordering: '-hora_final', sede_id: 7, page: 1, page_size: 120 },
    });
  });

  it('dado cambio de versión cuando rerenderiza entonces vuelve a pedir la página visible', async () => {
    mockGet.mockResolvedValue(pagina([LOTE]));
    const { rerender } = render(<TablaLotesPaginada version={0} />);
    await screen.findByText('L-1');
    rerender(<TablaLotesPaginada version={1} />);
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it('dado cambio de filtros cuando rerenderiza entonces consulta con los filtros nuevos', async () => {
    mockGet.mockResolvedValue(pagina([LOTE]));
    const { rerender } = render(<TablaLotesPaginada filtros={{ sede_id: 1 }} />);
    await screen.findByText('L-1');
    rerender(<TablaLotesPaginada filtros={{ sede_id: 2 }} />);
    await waitFor(() => expect(mockGet).toHaveBeenLastCalledWith('/lotes-produccion/', {
      params: { ordering: '-hora_final', sede_id: 2, page: 1, page_size: 120 },
    }));
  });
});
