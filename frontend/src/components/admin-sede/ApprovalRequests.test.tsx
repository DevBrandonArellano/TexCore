import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ApprovalRequests } from './ApprovalRequests';

describe('ApprovalRequests', () => {
  it('dado el componente cuando se renderiza entonces muestra el título', () => {
    render(<ApprovalRequests />);

    expect(screen.getByText('Solicitudes de Aprobación')).toBeInTheDocument();
  });

  it('dado el componente cuando se renderiza entonces muestra la descripción del módulo en reconstrucción', () => {
    render(<ApprovalRequests />);

    expect(
      screen.getByText('Este módulo está siendo reconstruido para adaptarse al nuevo sistema de inventario.')
    ).toBeInTheDocument();
  });

  it('dado el componente cuando se renderiza entonces muestra el texto "Próximamente"', () => {
    render(<ApprovalRequests />);

    expect(screen.getByText('Próximamente.')).toBeInTheDocument();
  });
});
