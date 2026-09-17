import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { CorridaContinuaDashboard } from './CorridaContinuaDashboard';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const CORRIDA_ACTIVA = {
  id: 1,
  codigo: 'CORR-2026-001',
  modalidad: 'CONTINUA',
  estado: 'en_proceso',
  turno: 'Mañana',
  fecha_jornada: '2026-09-17',
  area: 1,
  area_nombre: 'Tintorería Continua',
  maquina_principal: 1,
  maquina_principal_nombre: 'Rama 01',
  operaciones_count: 1,
};

const OPERACIONES = [
  {
    id: 10,
    corrida: 1,
    numero_secuencia: 1,
    maquina: 1,
    maquina_nombre: 'Rama 01',
    operario: 2,
    operario_nombre: 'Carlos Perez',
    hora_inicio: '2026-09-17T08:00:00Z',
    estado: 'completada',
    consumos: [
      { id: 1, cantidad_consumida: '100.000', producto_codigo: 'TEL-CRUD' },
    ],
    salidas: [
      { id: 2, cantidad_neta: '95.000', lote_generado_codigo: 'LOT-ACAB-01' },
    ],
    mermas: [
      { id: 3, peso_merma: '5.000' },
    ],
  },
];

describe('CorridaContinuaDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();

    mockGet.mockImplementation((url: string) => {
      if (url.includes('/corridas-produccion/')) {
        return Promise.resolve({ data: { results: [CORRIDA_ACTIVA] } });
      }
      if (url.includes('/operaciones-produccion/')) {
        return Promise.resolve({ data: { results: OPERACIONES } });
      }
      if (url.includes('/areas/')) {
        return Promise.resolve({ data: [{ id: 1, nombre: 'Tintorería Continua' }] });
      }
      if (url.includes('/maquinas/')) {
        return Promise.resolve({ data: [{ id: 1, nombre: 'Rama 01' }] });
      }
      if (url.includes('/bodegas/')) {
        return Promise.resolve({ data: [{ id: 1, nombre: 'Bodega Principal' }] });
      }
      if (url.includes('/productos/')) {
        return Promise.resolve({ data: [{ id: 1, codigo: 'TEL-CRUD', descripcion: 'Tela Cruda' }] });
      }
      return Promise.resolve({ data: { results: [] } });
    });
  });

  it('dado renderizado inicial cuando carga corrida activa entonces muestra codigo y estado', async () => {
    render(<CorridaContinuaDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Producción Continua \(MES\)/i)).toBeDefined();
      expect(screen.getByText(/CORR-2026-001/i)).toBeDefined();
      expect(screen.getByText(/EN_PROCESO/i)).toBeDefined();
    });
  });

  it('dado operaciones existentes cuando se renderiza entonces lista lote generado y cantidades', async () => {
    render(<CorridaContinuaDashboard />);

    await waitFor(() => {
      expect(screen.getByText('LOT-ACAB-01')).toBeDefined();
      expect(screen.getByText(/Carlos Perez/i)).toBeDefined();
    });
  });
});
