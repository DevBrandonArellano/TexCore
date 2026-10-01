import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RecetaVersionDialog } from './RecetaVersionDialog';

const mockVersion = vi.fn();
vi.mock('../../lib/api/formulasApi', () => ({
  formulasApi: { version: (...a: unknown[]) => mockVersion(...a) },
}));

const VERSION = {
  id: 20, numero: 2, es_oficial: true, motivo: 'Aprobada', observaciones: '', fecha: '2026-09-20T10:00:00Z',
  creada_por: 1, creada_por_nombre: 'tintorero1',
  snapshot: {
    formula: { codigo: 'AZ-001', nombre_color: 'Azul marino' },
    fases: [{
      orden: 1, proceso_codigo: 'TIN', proceso_nombre: 'Tintura', proceso_tipo: 'colorante', ciclo: null,
      temperatura: 80, tiempo: 45,
      detalles: [{ producto_id: 1, producto_codigo: 'C-1', producto_descripcion: 'Colorante azul',
        tipo_calculo: 'pct', concentracion_gr_l: null, porcentaje: '1.50', orden_adicion: 1 }],
    }],
  },
};

describe('RecetaVersionDialog', () => {
  beforeEach(() => mockVersion.mockReset());

  it('dado una versión cuando se abre entonces muestra su receta congelada', async () => {
    mockVersion.mockResolvedValue(VERSION);
    render(<RecetaVersionDialog formulaId={4} numero={2} onClose={vi.fn()} />);
    expect(await screen.findByText('Fase 1: Tintura')).toBeInTheDocument();
    expect(screen.getByText('Colorante azul')).toBeInTheDocument();
    expect(screen.getByText('1.50%')).toBeInTheDocument();
    expect(screen.getByText(/80°C/)).toBeInTheDocument();
    expect(mockVersion).toHaveBeenCalledWith(4, 2);
  });

  it('dado sin número cuando se renderiza entonces no consulta ni abre', () => {
    render(<RecetaVersionDialog formulaId={4} numero={null} onClose={vi.fn()} />);
    expect(mockVersion).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('dado error del servidor cuando se abre entonces lo indica', async () => {
    mockVersion.mockRejectedValueOnce(new Error('500'));
    render(<RecetaVersionDialog formulaId={4} numero={2} onClose={vi.fn()} />);
    expect(await screen.findByText('No se pudo cargar la receta de esta versión.')).toBeInTheDocument();
  });
});
