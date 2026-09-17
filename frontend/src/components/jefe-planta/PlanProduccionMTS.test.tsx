import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PlanProduccionMTS } from './PlanProduccionMTS';
import apiClient from '../../lib/axios';

vi.mock('../../lib/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockPlanes = [
  {
    id: 1,
    codigo: 'PLAN-MTS-2026-001',
    sede: 1,
    sede_nombre: 'Sede Principal',
    fecha_inicio: '2026-06-01',
    fecha_fin: '2026-06-07',
    estado: 'borrador',
    supervisor: 10,
    supervisor_nombre: 'Carlos Supervisor',
    detalles: [
      {
        id: 101,
        plan: 1,
        producto_objetivo: 20,
        producto_objetivo_codigo: 'TELA-JERSEY-01',
        producto_objetivo_descripcion: 'Tela Jersey 100% Algodón',
        producto_objetivo_unidad: 'kg',
        cantidad_planificada: '100.0000',
        cantidad_ejecutada: '20.0000',
        cantidad_aceptada: '20.0000',
        cantidad_segunda: '0.0000',
        saldo_pendiente: '80.0000',
        desviacion_porcentaje: '-80.00',
        cumplimiento_porcentaje: '20.00',
        estado: 'en_proceso',
      },
    ],
    fecha_creacion: '2026-06-01T08:00:00Z',
    fecha_modificacion: '2026-06-01T08:00:00Z',
  },
];

const mockNecesidades = [
  {
    sede_id: 1,
    sede_nombre: 'Sede Principal',
    producto_id: 30,
    producto_codigo: 'HILO-24-1',
    producto_descripcion: 'Hilo Algodón 24/1 Crudo',
    tipo: 'hilo',
    unidad_medida: 'kg',
    stock_actual: '25.00',
    stock_minimo: '100.00',
    deficit: '75.00',
  },
];

describe('PlanProduccionMTS Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url.includes('/planes-produccion/necesidades-reposicion/')) {
        return Promise.resolve({ data: mockNecesidades });
      }
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({ data: mockPlanes });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it('dado que el componente se monta cuando carga datos entonces muestra el plan y su renglón de detalle', async () => {
    render(
      <PlanProduccionMTS
        sedes={[{ id: 1, nombre: 'Sede Principal', location: 'Quito', status: 'activo' }]}
        bodegas={[{ id: 1, nombre: 'Bodega Central', sede: 1 }]}
      />
    );

    expect(screen.getByText(/Planificación y Producción Contra Stock \(MTS\)/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument();
      expect(screen.getByText('TELA-JERSEY-01')).toBeInTheDocument();
      expect(screen.getByText('Tela Jersey 100% Algodón')).toBeInTheDocument();
      expect(screen.getByText(/Aprobar Plan/i)).toBeInTheDocument();
    });
  });

  it('dado clic en Aprobar Plan cuando confirma entonces invoca el endpoint de aprobación', async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: { ...mockPlanes[0], estado: 'aprobado' } });

    render(
      <PlanProduccionMTS
        sedes={[{ id: 1, nombre: 'Sede Principal', location: 'Quito', status: 'activo' }]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument();
    });

    const botonAprobar = screen.getByText(/Aprobar Plan/i);
    fireEvent.click(botonAprobar);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/planes-produccion/1/aprobar/');
    });
  });

  it('dado clic en la pestaña Alertas de Stock cuando cambia entonces visualiza los déficits de reposición', async () => {
    render(
      <PlanProduccionMTS
        sedes={[{ id: 1, nombre: 'Sede Principal', location: 'Quito', status: 'activo' }]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Alertas de Stock Mínimo/i)).toBeInTheDocument();
    });

    const tabAlertas = screen.getByRole('button', { name: /Alertas de Stock Mínimo/i });
    fireEvent.click(tabAlertas);

    await waitFor(() => {
      expect(screen.getByText('HILO-24-1')).toBeInTheDocument();
      expect(screen.getByText('Hilo Algodón 24/1 Crudo')).toBeInTheDocument();
      expect(screen.getByText('75.00 kg')).toBeInTheDocument();
    });
  });
});
