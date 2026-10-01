import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReporteEficienciaArea } from './ReporteEficienciaArea';

const mockApi = { reporte: vi.fn(), desempeno: vi.fn() };
vi.mock('../../lib/api/indicadoresApi', () => ({
  indicadoresApi: {
    reporteEficienciaArea: (...a: unknown[]) => mockApi.reporte(...a),
    desempenoOperario: (...a: unknown[]) => mockApi.desempeno(...a),
  },
}));

const REPORTE = {
  area_id: 4, area_nombre: 'Tintorería', fecha_reporte: '2026-10-01',
  maquinas: [{ maquina_id: 1, maquina_nombre: 'TIN-01', capacidad_maxima: '500.00', produccion_total: '400.000', eficiencia: '80.00' }],
  operarios: [{ operario_id: 7, username: 'op1', total_lotes: 4, produccion_total_kg: '400.000',
    promedio_kg_por_lote: '100.00', horas_trabajadas_aprox: 8, productividad_kg_hora: 50 }],
  produccion_total_area: '400.000', eficiencia_promedio_area: '80.00',
};
const DESEMPENO = {
  operario: 'op1', produccion_hoy_kg: '400.000', lotes_hoy: 4,
  ultimos_lotes: [{ id: 1, codigo_lote: 'LOT-77', peso_neto_producido: '100.000', hora_final: '2026-10-01T15:00:00Z',
    maquina_nombre: 'TIN-01', turno: 'Dia' }],
};

describe('ReporteEficienciaArea', () => {
  beforeEach(() => { mockApi.reporte.mockReset(); mockApi.desempeno.mockReset(); });

  it('dado reporte del día cuando carga entonces muestra máquinas, operarios y totales del área', async () => {
    mockApi.reporte.mockResolvedValueOnce(REPORTE);
    render(<ReporteEficienciaArea areaId={4} />);
    expect(await screen.findByText('TIN-01')).toBeInTheDocument();
    expect(screen.getByText('80.00 %')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'op1' })).toBeInTheDocument();
    expect(screen.getByText('50 kg/h')).toBeInTheDocument();
    expect(mockApi.reporte).toHaveBeenCalledWith(4);
  });

  it('dado clic en un operario cuando abre su desempeño entonces muestra su producción y últimos lotes', async () => {
    mockApi.reporte.mockResolvedValueOnce(REPORTE);
    mockApi.desempeno.mockResolvedValueOnce(DESEMPENO);
    render(<ReporteEficienciaArea areaId={4} />);
    await userEvent.click(await screen.findByRole('button', { name: 'op1' }));
    const dialogo = await screen.findByRole('dialog');
    expect(await within(dialogo).findByText('LOT-77')).toBeInTheDocument();
    expect(within(dialogo).getByText(/4 lotes/)).toBeInTheDocument();
    expect(mockApi.desempeno).toHaveBeenCalledWith(7);
  });

  it('dado área sin producción hoy cuando carga entonces lo indica', async () => {
    mockApi.reporte.mockResolvedValueOnce({ ...REPORTE, maquinas: [], operarios: [] });
    render(<ReporteEficienciaArea areaId={4} />);
    expect(await screen.findByText('Sin producción registrada hoy en el área.')).toBeInTheDocument();
  });

  it('dado error del servidor cuando carga entonces lo muestra', async () => {
    mockApi.reporte.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'Sin permiso.' } } });
    render(<ReporteEficienciaArea areaId={4} />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
