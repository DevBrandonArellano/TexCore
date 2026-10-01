import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PanelConsumos } from './PanelConsumos';
import { PanelCosto } from './PanelCosto';

const mockLotes = { consumos: vi.fn(), costo: vi.fn() };
vi.mock('../../../lib/api/lotesApi', () => ({
  lotesApi: {
    consumos: (...a: unknown[]) => mockLotes.consumos(...a),
    costo: (...a: unknown[]) => mockLotes.costo(...a),
  },
}));

const LOTE = { id: 3, codigo_lote: 'LOT-1' };

describe('PanelConsumos y PanelCosto', () => {
  beforeEach(() => { mockLotes.consumos.mockReset(); mockLotes.costo.mockReset(); });

  it('dado lote sin consumos cuando carga entonces muestra el mensaje de vacío', async () => {
    mockLotes.consumos.mockResolvedValueOnce([]);
    render(<PanelConsumos lote={LOTE} />);
    expect(await screen.findByText('El lote no consumió otros lotes en su mezcla.')).toBeInTheDocument();
  });

  it('dado consumo sin código de origen ni lote nuevo cuando carga entonces muestra el id y No', async () => {
    mockLotes.consumos.mockResolvedValueOnce([
      { id: 1, lote_produccion: 3, lote_origen: 8, cantidad_consumida: '5.000', genera_nuevo_lote: false },
    ]);
    render(<PanelConsumos lote={LOTE} />);
    expect(await screen.findByText('8')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
  });

  it('dado costo sin precio esperado cuando carga entonces muestra el total sin margen', async () => {
    mockLotes.costo.mockResolvedValueOnce({
      id: 1, lote_produccion: 3, lote_codigo: 'LOT-1', costo_materia_prima: '10.000', costo_quimicos: '1.000',
      costo_operario: '0.000', costo_maquina: '0.000', otros_costos: '0.000', total_costo: '11.000',
      precio_venta_esperado: null, margen_bruto: null, margen_bruto_pct: null,
      calculado_en: '2026-10-01T10:00:00Z', recalculado_en: null,
    });
    render(<PanelCosto lote={LOTE} />);
    expect(await screen.findByText('11.000')).toBeInTheDocument();
    expect(screen.queryByText(/Margen bruto/)).not.toBeInTheDocument();
  });

  it('dado error del servidor cuando carga el costo entonces lo muestra', async () => {
    mockLotes.costo.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'Sin permiso.' } } });
    render(<PanelCosto lote={LOTE} />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('dado margen sin monto ni precio y un concepto nulo cuando carga entonces usa el guion de respaldo', async () => {
    mockLotes.costo.mockResolvedValueOnce({
      id: 1, lote_produccion: 3, lote_codigo: 'LOT-1', costo_materia_prima: '10.000', costo_quimicos: '1.000',
      costo_operario: '0.000', costo_maquina: '0.000', otros_costos: null, total_costo: '11.000',
      precio_venta_esperado: null, margen_bruto: null, margen_bruto_pct: '0.00',
      calculado_en: '2026-10-01T10:00:00Z', recalculado_en: '2026-10-01T11:00:00Z',
    });
    render(<PanelCosto lote={LOTE} />);
    expect(await screen.findByText(/Margen bruto/)).toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBe(3);
  });
});

