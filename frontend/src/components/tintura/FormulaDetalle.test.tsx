import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FormulaDetalle } from './FormulaDetalle';
import type { FormulaColor, ProcesoTintoreria } from '../../lib/types';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const PROCESOS: ProcesoTintoreria[] = [
  { id: 1, codigo: 'TINTURA', nombre: 'Tintura Principal', tipo: 'colorante', activo: true },
];

const FORMULA: FormulaColor = {
  id: 7,
  codigo: 'PES-T0191',
  nombre_color: 'AZUL',
  tipo_sustrato: 'poliester',
  version: 1,
  version_oficial: 1,
  estado: 'aprobada',
  fases: [
    {
      id: 1, proceso: 1, proceso_nombre: 'Tintura Principal', orden: 1, temperatura: 90, tiempo: 60,
      detalles: [
        { id: 1, producto: 5, producto_descripcion: 'Colorante Rojo', tipo_calculo: 'gr_l', concentracion_gr_l: '5.000', porcentaje: null, orden_adicion: 1, notas: '' } as any,
      ],
    },
  ],
};

function renderDetalle(overrides: Partial<React.ComponentProps<typeof FormulaDetalle>> = {}) {
  mockGet.mockImplementation((url: string) => {
    if (url.includes('/ordenes-produccion/historial/')) return Promise.resolve({ data: [] });
    if (url.includes('/versiones/')) return Promise.resolve({ data: [] });
    return Promise.reject(new Error('url no esperada: ' + url));
  });
  const props: React.ComponentProps<typeof FormulaDetalle> = {
    formula: FORMULA,
    procesos: PROCESOS,
    onVolver: vi.fn(),
    onEditar: vi.fn(),
    onCrearVersion: vi.fn().mockResolvedValue(true),
    onMarcarOficial: vi.fn().mockResolvedValue(true),
    onDerivar: vi.fn().mockResolvedValue(true),
    ...overrides,
  };
  return { ...render(<FormulaDetalle {...props} />), props };
}

describe('FormulaDetalle', () => {
  beforeEach(() => { mockGet.mockReset(); });

  it('dado una formula cuando renderiza entonces muestra codigo, nombre y version oficial', () => {
    renderDetalle();
    expect(screen.getByText('PES-T0191')).toBeInTheDocument();
    expect(screen.getByText('AZUL')).toBeInTheDocument();
    expect(screen.getByText('Oficial v1')).toBeInTheDocument();
  });

  it('dado una formula sin oficial cuando renderiza entonces indica que no tiene', () => {
    renderDetalle({ formula: { ...FORMULA, version_oficial: null } });
    expect(screen.getByText('Sin oficial')).toBeInTheDocument();
  });

  it('dado la pestana receta activa por defecto cuando renderiza entonces muestra las fases y sus insumos', () => {
    renderDetalle();
    expect(screen.getByText(/Fase 1: Tintura Principal/)).toBeInTheDocument();
    expect(screen.getByText('Colorante Rojo')).toBeInTheDocument();
  });

  it('dado click en editar receta cuando hace click entonces llama a onEditar con la formula', async () => {
    const onEditar = vi.fn();
    renderDetalle({ onEditar });
    await userEvent.click(screen.getByRole('button', { name: /Editar receta/i }));
    expect(onEditar).toHaveBeenCalledWith(FORMULA);
  });

  it('dado click en volver cuando hace click entonces llama a onVolver', async () => {
    const onVolver = vi.fn();
    renderDetalle({ onVolver });
    await userEvent.click(screen.getByRole('button', { name: /Volver/i }));
    expect(onVolver).toHaveBeenCalled();
  });

  it('dado una formula derivada cuando renderiza entonces muestra su origen', () => {
    renderDetalle({
      formula: {
        ...FORMULA, formula_origen: 3, formula_origen_codigo: 'ORIG-001', version_origen: 2,
        version_origen_numero: 2, motivo_derivacion: 'Cambio de sustrato',
      },
    });
    expect(screen.getByText(/Derivada de/)).toBeInTheDocument();
    expect(screen.getByText(/ORIG-001/)).toBeInTheDocument();
  });

  it('dado click en la pestana ordenes cuando carga entonces consulta el historial filtrado por la formula', async () => {
    renderDetalle();
    await userEvent.click(screen.getByRole('tab', { name: 'Órdenes' }));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/ordenes-produccion/historial/?formula_color=7'));
    expect(await screen.findByText(/Ninguna orden de producción/)).toBeInTheDocument();
  });

  it('dado ordenes existentes cuando abre la pestana ordenes entonces las lista', async () => {
    renderDetalle();
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/ordenes-produccion/historial/')) {
        return Promise.resolve({
          data: [{ id: 1, codigo: 'OP-001', estado: 'en_proceso', peso_neto_requerido: '100.00', litros_bano: '1000.00', version_formula: 2 }],
        });
      }
      return Promise.reject(new Error('url no esperada: ' + url));
    });
    await userEvent.click(screen.getByRole('tab', { name: 'Órdenes' }));

    expect(await screen.findByText('OP-001')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
  });

  it('dado respuesta paginada de ordenes cuando abre la pestana entonces extrae el arreglo results', async () => {
    renderDetalle();
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/ordenes-produccion/historial/')) {
        return Promise.resolve({
          data: { results: [{ id: 2, codigo: 'OP-002', estado: 'pendiente', peso_neto_requerido: null, litros_bano: null, version_formula: null }] },
        });
      }
      return Promise.reject(new Error('url no esperada: ' + url));
    });
    await userEvent.click(screen.getByRole('tab', { name: 'Órdenes' }));

    expect(await screen.findByText('OP-002')).toBeInTheDocument();
  });

  it('dado error al cargar el historial de ordenes cuando falla entonces muestra la lista vacia', async () => {
    renderDetalle();
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/ordenes-produccion/historial/')) return Promise.reject(new Error('500'));
      return Promise.reject(new Error('url no esperada: ' + url));
    });
    await userEvent.click(screen.getByRole('tab', { name: 'Órdenes' }));

    expect(await screen.findByText(/Ninguna orden de producción/)).toBeInTheDocument();
  });

  it('dado una formula sin fases cuando renderiza entonces indica que no tiene fases', () => {
    renderDetalle({ formula: { ...FORMULA, fases: [] } });
    expect(screen.getByText('Esta fórmula todavía no tiene fases.')).toBeInTheDocument();
  });

  it('dado una fase sin proceso_nombre cuando renderiza entonces resuelve el nombre desde el catalogo', () => {
    renderDetalle({
      formula: {
        ...FORMULA,
        fases: [{ ...FORMULA.fases![0], proceso_nombre: undefined } as any],
      },
    });
    expect(screen.getByText(/Fase 1: Tintura Principal/)).toBeInTheDocument();
  });

  it('dado un insumo calculado por porcentaje cuando renderiza entonces muestra el porcentaje', () => {
    renderDetalle({
      formula: {
        ...FORMULA,
        fases: [{
          ...FORMULA.fases![0],
          detalles: [{ id: 2, producto: 6, producto_descripcion: 'Fijador', tipo_calculo: 'pct', concentracion_gr_l: null, porcentaje: '2.5', orden_adicion: 1, notas: '' } as any],
        }],
      },
    });
    expect(screen.getByText('2.5%')).toBeInTheDocument();
  });
});
