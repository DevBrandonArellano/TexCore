import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DosificacionFormulaPanel } from './DosificacionFormulaPanel';

const mockCalcular = vi.fn();
vi.mock('../../lib/api/formulasApi', () => ({
  formulasApi: { calcularDosificacion: (...a: unknown[]) => mockCalcular(...a) },
}));
const mockToastError = vi.fn();
vi.mock('sonner', () => ({ toast: { error: (...a: unknown[]) => mockToastError(...a) } }));

const RESULTADO = {
  formula_id: 4, formula_nombre: 'Azul marino', formula_version: 2, kg_tela: '120.000',
  relacion_bano: '8.00', volumen_bano_litros: '960.00',
  insumos: [{ producto_id: 1, producto_descripcion: 'Colorante azul', tipo_calculo: 'pct', cantidad_kg: '1.800',
    cantidad_gr: '1800.0', concentracion_gr_l: null, porcentaje: '1.50', orden_adicion: 1 }],
};

describe('DosificacionFormulaPanel', () => {
  beforeEach(() => { mockCalcular.mockReset(); mockToastError.mockReset(); });

  it('dado peso y litros cuando calcula entonces muestra los insumos de la fórmula guardada', async () => {
    mockCalcular.mockResolvedValue(RESULTADO);
    render(<DosificacionFormulaPanel formulaId={4} />);
    fireEvent.change(screen.getByLabelText('Peso de la tela (kg)'), { target: { value: '120' } });
    fireEvent.change(screen.getByLabelText('Litros de baño'), { target: { value: '960' } });
    fireEvent.click(screen.getByRole('button', { name: 'Calcular' }));
    expect(await screen.findByText('Colorante azul')).toBeInTheDocument();
    expect(screen.getByText('1.800')).toBeInTheDocument();
    expect(screen.getByText(/1:8\.00/)).toBeInTheDocument();
    expect(mockCalcular).toHaveBeenCalledWith(4, 120, 960);
  });

  it('dado peso o litros no positivos cuando calcula entonces avisa y no llama a la API', () => {
    render(<DosificacionFormulaPanel formulaId={4} />);
    fireEvent.change(screen.getByLabelText('Peso de la tela (kg)'), { target: { value: '120' } });
    fireEvent.click(screen.getByRole('button', { name: 'Calcular' }));
    expect(mockToastError).toHaveBeenCalled();
    expect(mockCalcular).not.toHaveBeenCalled();
  });

  it('dado error del servidor cuando calcula entonces lo muestra', async () => {
    mockCalcular.mockRejectedValue({ response: { status: 400, data: { peso: ['Debe ser mayor a cero.'] } } });
    render(<DosificacionFormulaPanel formulaId={4} />);
    fireEvent.change(screen.getByLabelText('Peso de la tela (kg)'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Litros de baño'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Calcular' }));
    await waitFor(() => expect(mockToastError).toHaveBeenCalled());
  });
});
