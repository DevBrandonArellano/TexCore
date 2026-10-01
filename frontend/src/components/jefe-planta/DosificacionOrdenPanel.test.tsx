import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DosificacionOrdenPanel } from './DosificacionOrdenPanel';

const mockDosificacion = vi.fn();
const mockProcesos = vi.fn();
vi.mock('../../lib/api/ordenesApi', () => ({
  ordenesApi: {
    calcularDosificacion: (...a: unknown[]) => mockDosificacion(...a),
    procesosDeMaquina: (...a: unknown[]) => mockProcesos(...a),
  },
}));
const mockToastError = vi.fn();
vi.mock('sonner', () => ({ toast: { error: (...a: unknown[]) => mockToastError(...a) } }));

const RESULTADO = {
  orden_id: 7, peso: '100.000', litros_bano: '800.00', relacion_bano: '8.00',
  insumos: [
    { producto_id: 1, producto_descripcion: 'Sal industrial', tipo_calculo: 'gr_l', cantidad_kg: '8.000',
      cantidad_gr: '8000.0', concentracion_gr_l: '10.00', porcentaje: null, orden_adicion: 1 },
    { producto_id: 2, producto_descripcion: 'Colorante azul', tipo_calculo: 'pct', cantidad_kg: '1.500',
      cantidad_gr: '1500.0', concentracion_gr_l: null, porcentaje: '1.50', orden_adicion: 2 },
  ],
};

describe('DosificacionOrdenPanel', () => {
  beforeEach(() => {
    mockDosificacion.mockReset();
    mockProcesos.mockReset();
    mockToastError.mockReset();
    mockProcesos.mockResolvedValue([]);
  });

  it('dado litros propuestos cuando calcula entonces muestra los insumos con cantidad y relación', async () => {
    mockDosificacion.mockResolvedValue(RESULTADO);
    render(<DosificacionOrdenPanel ordenId={7} maquinaId={null} litros="800" />);
    fireEvent.click(screen.getByRole('button', { name: 'Ver dosificación' }));
    expect(await screen.findByText('Sal industrial')).toBeInTheDocument();
    expect(screen.getByText('10.00 g/L')).toBeInTheDocument();
    expect(screen.getByText('1.50 %')).toBeInTheDocument();
    expect(screen.getByText('8.000')).toBeInTheDocument();
    expect(screen.getByText(/1:8\.00/)).toBeInTheDocument();
    expect(mockDosificacion).toHaveBeenCalledWith(7, 800);
  });

  it('dado litros vacíos o no positivos cuando calcula entonces avisa y no llama a la API', () => {
    render(<DosificacionOrdenPanel ordenId={7} maquinaId={null} litros="0" />);
    fireEvent.click(screen.getByRole('button', { name: 'Ver dosificación' }));
    expect(mockToastError).toHaveBeenCalled();
    expect(mockDosificacion).not.toHaveBeenCalled();
  });

  it('dado error del servidor cuando calcula entonces lo muestra', async () => {
    mockDosificacion.mockRejectedValue({
      response: { status: 400, data: { litros_bano: ['Los litros de baño (900) superan el volumen de la máquina asignada (800 L).'] } },
    });
    render(<DosificacionOrdenPanel ordenId={7} maquinaId={null} litros="900" />);
    fireEvent.click(screen.getByRole('button', { name: 'Ver dosificación' }));
    await waitFor(() => expect(mockToastError).toHaveBeenCalled());
    expect(String(mockToastError.mock.calls[0])).toContain('superan el volumen');
  });

  it('dado máquina asignada cuando monta entonces lista los procesos de tintorería que ejecuta', async () => {
    mockProcesos.mockResolvedValue([{ id: 4, codigo: 'DESC', nombre: 'Descrude', tipo: 'preparacion', activo: true }]);
    render(<DosificacionOrdenPanel ordenId={7} maquinaId={3} litros="" />);
    expect(await screen.findByText('Descrude')).toBeInTheDocument();
    expect(mockProcesos).toHaveBeenCalledWith(3);
  });

  it('dado sin máquina asignada cuando monta entonces no consulta procesos', () => {
    render(<DosificacionOrdenPanel ordenId={7} maquinaId={null} litros="" />);
    expect(mockProcesos).not.toHaveBeenCalled();
  });
});
