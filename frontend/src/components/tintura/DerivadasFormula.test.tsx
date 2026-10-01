import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DerivadasFormula } from './DerivadasFormula';

const mockDerivadas = vi.fn();
vi.mock('../../lib/api/formulasApi', () => ({
  formulasApi: { derivadas: (...a: unknown[]) => mockDerivadas(...a) },
}));

describe('DerivadasFormula', () => {
  beforeEach(() => mockDerivadas.mockReset());

  it('dado fórmulas derivadas cuando carga entonces muestra código, versión de origen, estado y motivo', async () => {
    mockDerivadas.mockResolvedValue([{
      id: 9, codigo: 'AZ-002', nombre_color: 'Azul petróleo', estado: 'en_pruebas',
      version_origen_numero: 2, motivo_derivacion: 'Cliente pidió tono más verdoso', es_laboratorio: true,
    }]);
    render(<DerivadasFormula formulaId={4} />);
    expect(await screen.findByText('AZ-002')).toBeInTheDocument();
    expect(screen.getByText('Azul petróleo')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
    expect(screen.getByText('En pruebas')).toBeInTheDocument();
    expect(screen.getByText('Cliente pidió tono más verdoso')).toBeInTheDocument();
    expect(mockDerivadas).toHaveBeenCalledWith(4);
  });

  it('dado sin derivadas cuando carga entonces muestra el estado vacío', async () => {
    mockDerivadas.mockResolvedValue([]);
    render(<DerivadasFormula formulaId={4} />);
    expect(await screen.findByText('Ninguna fórmula se ha derivado de esta.')).toBeInTheDocument();
  });

  it('dado error del servidor cuando carga entonces lo indica', async () => {
    mockDerivadas.mockRejectedValueOnce(new Error('500'));
    render(<DerivadasFormula formulaId={4} />);
    expect(await screen.findByText('No se pudieron cargar las fórmulas derivadas.')).toBeInTheDocument();
  });
});
