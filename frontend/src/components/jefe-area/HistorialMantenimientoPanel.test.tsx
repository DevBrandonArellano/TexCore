import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HistorialMantenimientoPanel } from './HistorialMantenimientoPanel';

const mockApi = { historial: vi.fn(), imprimir: vi.fn() };
vi.mock('../../lib/api/mantenimientoApi', () => ({
  mantenimientoApi: {
    historial: (...a: unknown[]) => mockApi.historial(...a),
    imprimirHistorial: (...a: unknown[]) => mockApi.imprimir(...a),
  },
}));

const mockToastError = vi.fn();
vi.mock('sonner', () => ({ toast: { error: (...a: unknown[]) => mockToastError(...a) } }));

const MAQUINAS = [
  { id: 1, nombre: 'Tejedora 1' },
  { id: 2, nombre: 'Tintorera 2' },
];

const paro = (cambios: Record<string, unknown> = {}) => ({
  id: 10,
  maquina: 1,
  maquina_nombre: 'Tejedora 1',
  area_nombre: 'Tejeduría',
  inicio: '2026-10-08T13:30:00Z',
  fin: '2026-10-09T01:30:00Z',
  categoria: 'MANTENIMIENTO_PLANIFICADO',
  categoria_display: 'Mantenimiento Planificado',
  planificado: true,
  descripcion: 'Cambio de rodamientos',
  turno: 'Mañana',
  usuario_nombre: 'Jefe de Tejeduría',
  origen: 'manual',
  en_curso: false,
  horas: 12,
  ...cambios,
});

const HISTORIAL = {
  rango: { fecha_desde: '2026-09-14', fecha_hasta: '2026-10-14' },
  resumen: [
    {
      maquina_id: 1,
      maquina_nombre: 'Tejedora 1',
      area_nombre: 'Tejeduría',
      paros: 2,
      horas_total: 13.5,
      horas_planificadas: 12,
      paros_en_curso: 0,
      ultimo_mantenimiento: '2026-10-08T13:30:00Z',
    },
  ],
  totales: { maquinas: 1, paros: 2, horas_total: 13.5, horas_planificadas: 12, paros_en_curso: 0 },
  detalle: { count: 2, next: null, previous: null, results: [
    paro(),
    paro({ id: 11, categoria_display: 'Avería / Falla de Equipo', planificado: false, horas: 1.5, descripcion: 'Rodillo trabado' }),
  ] },
};

const vacio = {
  ...HISTORIAL,
  resumen: [],
  totales: { maquinas: 0, paros: 0, horas_total: 0, horas_planificadas: 0, paros_en_curso: 0 },
  detalle: { count: 0, next: null, previous: null, results: [] },
};

describe('HistorialMantenimientoPanel', () => {
  beforeEach(() => {
    mockApi.historial.mockReset();
    mockApi.imprimir.mockReset();
    mockToastError.mockReset();
  });

  it('dado paros del rango cuando carga entonces muestra totales, resumen y detalle', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);

    expect(await screen.findByText('Cambio de rodamientos')).toBeInTheDocument();
    // 13.50 h aparece dos veces: en los totales del rango y en la fila de la máquina.
    expect(screen.getAllByText('13.50')).toHaveLength(2);
    expect(screen.getAllByText('Tejedora 1').length).toBeGreaterThan(1);
    expect(screen.getByText('Avería / Falla de Equipo')).toBeInTheDocument();
    expect(screen.getByText('Planificado')).toBeInTheDocument();
  });

  it('dado el primer render cuando consulta entonces pide los últimos 30 días', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');

    const [filtros, pagina, tamano] = mockApi.historial.mock.calls[0];
    const dias = (new Date(filtros.fecha_hasta).getTime() - new Date(filtros.fecha_desde).getTime()) / 86_400_000;
    expect(Math.round(dias)).toBe(30);
    expect(pagina).toBe(1);
    expect(tamano).toBe(50);
  });

  it('dado el atajo de mantenimiento cuando se pulsa entonces filtra por esa categoría', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);
    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');

    await userEvent.click(screen.getByRole('button', { name: /Solo mantenimiento/ }));

    await vi.waitFor(() => {
      const ultima = mockApi.historial.mock.calls.at(-1);
      expect(ultima?.[0].categoria).toBe('MANTENIMIENTO_PLANIFICADO');
    });
  });

  it('dado el atajo de averías cuando se pulsa entonces filtra por avería', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);
    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');

    await userEvent.click(screen.getByRole('button', { name: /Solo averías/ }));

    await vi.waitFor(() => {
      expect(mockApi.historial.mock.calls.at(-1)?.[0].categoria).toBe('AVERIA');
    });
  });

  it('dado un cambio de fecha cuando se consulta entonces usa el rango nuevo', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);
    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');

    await userEvent.clear(screen.getByLabelText('Desde'));
    await userEvent.type(screen.getByLabelText('Desde'), '2026-01-15');

    await vi.waitFor(() => {
      expect(mockApi.historial.mock.calls.at(-1)?.[0].fecha_desde).toBe('2026-01-15');
    });
  });

  it('dado un paro en curso cuando se muestra entonces lo marca y cuenta sus horas', async () => {
    mockApi.historial.mockResolvedValue({
      ...HISTORIAL,
      resumen: [{ ...HISTORIAL.resumen[0], paros_en_curso: 1, horas_total: 5 }],
      totales: { ...HISTORIAL.totales, paros_en_curso: 1 },
      detalle: { count: 1, next: null, previous: null, results: [paro({ fin: null, en_curso: true, horas: 5 })] },
    });

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);

    // «En curso» aparece en el encabezado del resumen y en la celda del fin del paro.
    expect((await screen.findAllByText('En curso')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('5.00').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Cambio de rodamientos')).toBeInTheDocument();
  });

  it('dado un paro abierto por el cambio de estado cuando se muestra entonces lo marca como automático', async () => {
    mockApi.historial.mockResolvedValue({
      ...HISTORIAL,
      detalle: { count: 1, next: null, previous: null, results: [paro({ origen: 'estado' })] },
    });

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);

    expect(await screen.findByText('Automático')).toBeInTheDocument();
  });

  it('dado un rango sin paros cuando carga entonces avisa que no hay datos', async () => {
    mockApi.historial.mockResolvedValue(vacio);

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);

    expect(await screen.findByText(/Sin paros registrados/)).toBeInTheDocument();
  });

  it('dado un fallo de carga cuando ocurre entonces muestra el error y permite reintentar', async () => {
    mockApi.historial.mockRejectedValueOnce(new Error('timeout'));
    mockApi.historial.mockResolvedValue(HISTORIAL);

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);

    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByText('Cambio de rodamientos')).toBeInTheDocument();
  });

  it('dado el botón imprimir cuando se pulsa entonces pide el PDF con los filtros vigentes', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);
    mockApi.imprimir.mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }));
    const open = vi.spyOn(window, 'open').mockImplementation(() => null);
    URL.createObjectURL = vi.fn(() => 'blob:historial');

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');
    await userEvent.click(screen.getByRole('button', { name: /Solo averías/ }));
    await userEvent.click(screen.getByRole('button', { name: /Imprimir/ }));

    await vi.waitFor(() => {
      expect(mockApi.imprimir).toHaveBeenCalledWith(expect.objectContaining({ categoria: 'AVERIA' }));
    });
    expect(open).toHaveBeenCalledWith('blob:historial', '_blank');
    open.mockRestore();
  });

  it('dado un fallo al imprimir cuando ocurre entonces avisa y no abre nada', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);
    mockApi.imprimir.mockRejectedValueOnce(new Error('503'));
    const open = vi.spyOn(window, 'open').mockImplementation(() => null);

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');
    await userEvent.click(screen.getByRole('button', { name: /Imprimir/ }));

    await vi.waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith('No se pudo generar el historial en PDF.');
    });
    expect(open).not.toHaveBeenCalled();
    open.mockRestore();
  });

  it('dado más de una página cuando se navega entonces pide la página siguiente', async () => {
    mockApi.historial.mockResolvedValue({
      ...HISTORIAL,
      detalle: { ...HISTORIAL.detalle, count: 120, next: 'http://x/?page=2' },
    });

    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }));

    await vi.waitFor(() => {
      expect(mockApi.historial.mock.calls.at(-1)?.[1]).toBe(2);
    });
  });

  it('dado el selector de máquina cuando se elige una entonces filtra por su id', async () => {
    mockApi.historial.mockResolvedValue(HISTORIAL);
    render(<HistorialMantenimientoPanel maquinas={MAQUINAS} />);
    await screen.findByText('Cambio de rodamientos');

    await userEvent.click(screen.getByLabelText('Máquina'));
    await userEvent.click(within(await screen.findByRole('listbox')).getByText('Tintorera 2'));

    await vi.waitFor(() => {
      expect(mockApi.historial.mock.calls.at(-1)?.[0].maquina).toBe(2);
    });
  });
});
