import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SharedKPIChart } from './SharedKPIChart';

const DATA = [
  { name: 'Ene', ventas: 100, costos: 60 },
  { name: 'Feb', ventas: 150, costos: 90 },
];
const CONFIG = [{ dataKey: 'ventas', name: 'Ventas' }, { dataKey: 'costos', name: 'Costos' }];

describe('SharedKPIChart', () => {
  it('dado datos vacios cuando renderiza entonces muestra mensaje de sin datos', () => {
    render(<SharedKPIChart type="bar" data={[]} config={CONFIG} />);
    expect(screen.getByText('Sin datos disponibles')).toBeInTheDocument();
  });

  it('dado data null cuando renderiza entonces muestra mensaje de sin datos', () => {
    render(<SharedKPIChart type="bar" data={null as any} config={CONFIG} />);
    expect(screen.getByText('Sin datos disponibles')).toBeInTheDocument();
  });

  it('dado type bar con datos cuando renderiza entonces no muestra el mensaje de vacio', () => {
    const { container } = render(<SharedKPIChart type="bar" data={DATA} config={CONFIG} />);
    expect(screen.queryByText('Sin datos disponibles')).not.toBeInTheDocument();
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });

  it('dado type line con datos cuando renderiza entonces no lanza excepcion', () => {
    const { container } = render(<SharedKPIChart type="line" data={DATA} config={CONFIG} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });

  it('dado type area con datos cuando renderiza entonces no lanza excepcion', () => {
    const { container } = render(<SharedKPIChart type="area" data={DATA} config={CONFIG} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });

  it('dado type pie con datos cuando renderiza entonces no lanza excepcion', () => {
    const { container } = render(<SharedKPIChart type="pie" data={DATA} config={CONFIG} />);
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });

  it('dado un height personalizado cuando renderiza entonces lo aplica al contenedor', () => {
    const { container } = render(<SharedKPIChart type="bar" data={DATA} config={CONFIG} height={400} />);
    const responsiveDiv = container.querySelector('.recharts-responsive-container') as HTMLElement;
    expect(responsiveDiv.style.height).toBe('400px');
  });

  it('dado un tipo no reconocido cuando renderiza entonces no lanza excepcion', () => {
    expect(() => render(<SharedKPIChart type={'desconocido' as any} data={DATA} config={CONFIG} />)).not.toThrow();
  });
});
