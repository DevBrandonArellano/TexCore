import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AreaMovementsTable } from './AreaMovementsTable';

describe('AreaMovementsTable', () => {
  it('dado el componente cuando se renderiza entonces muestra el título, la descripción y el mensaje de próximamente', () => {
    render(<AreaMovementsTable />);

    expect(screen.getByText('Movimientos del Área')).toBeInTheDocument();
    expect(
      screen.getByText('Este módulo está siendo reconstruido para adaptarse al nuevo sistema de inventario.')
    ).toBeInTheDocument();
    expect(screen.getByText('Próximamente.')).toBeInTheDocument();
  });
});
