import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AdminSedeDashboard } from './AdminSedeDashboard';
import React from 'react';

vi.mock('../ejecutivos/EjecutivosDashboard', () => ({
  EjecutivosDashboard: vi.fn((props: { isAdminSede?: boolean }) => (
    <div data-testid="ejecutivos-dashboard-mock">{String(props.isAdminSede)}</div>
  )),
}));

import { EjecutivosDashboard } from '../ejecutivos/EjecutivosDashboard';

describe('AdminSedeDashboard', () => {
  it('renderiza el componente EjecutivosDashboard mockeado', () => {
    render(<AdminSedeDashboard />);

    expect(screen.getByTestId('ejecutivos-dashboard-mock')).toBeInTheDocument();
  });

  it('pasa isAdminSede={true} como prop a EjecutivosDashboard', () => {
    render(<AdminSedeDashboard />);

    expect(EjecutivosDashboard).toHaveBeenCalledWith(
      expect.objectContaining({ isAdminSede: true }),
      expect.anything()
    );
  });
});
