import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MovementApproval } from './MovementApproval';

describe('MovementApproval', () => {
  it('dado el componente cuando se renderiza entonces muestra el título y la descripción de estado inactivo', () => {
    render(<MovementApproval />);

    expect(screen.getByText('Aprobación de Movimientos')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Este módulo no está activo actualmente. Todos los movimientos se procesan de forma inmediata para agilizar la operación.'
      )
    ).toBeInTheDocument();
  });

  it('dado el componente cuando se renderiza entonces muestra el texto explicativo sobre la aprobación manual deshabilitada', () => {
    render(<MovementApproval />);

    expect(
      screen.getByText(
        'La lógica de aprobación manual ha sido deshabilitada para evitar cuellos de botella operativos.'
      )
    ).toBeInTheDocument();
  });
});
