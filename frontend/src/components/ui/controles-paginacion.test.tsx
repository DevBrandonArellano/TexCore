import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ControlesPaginacion } from './controles-paginacion';

function renderControles(props: Partial<React.ComponentProps<typeof ControlesPaginacion>> = {}) {
  const setCurrentPage = vi.fn();
  render(<ControlesPaginacion currentPage={2} totalPages={5} setCurrentPage={setCurrentPage} {...props} />);
  return setCurrentPage;
}

describe('ControlesPaginacion', () => {
  it('dado primera página cuando renderiza entonces Anterior está deshabilitado', () => {
    renderControles({ currentPage: 1 });
    expect(screen.getByRole('button', { name: /anterior/i })).toBeDisabled();
  });

  it('dado última página cuando renderiza entonces Siguiente está deshabilitado', () => {
    renderControles({ currentPage: 5 });
    expect(screen.getByRole('button', { name: /siguiente/i })).toBeDisabled();
  });

  it('dado página intermedia cuando pulsa Siguiente y Anterior entonces avanza y retrocede', async () => {
    const set = renderControles();
    await userEvent.click(screen.getByRole('button', { name: /siguiente/i }));
    await userEvent.click(screen.getByRole('button', { name: /anterior/i }));
    expect(set.mock.calls).toEqual([[3], [1]]);
  });

  it('dado número válido en Ir a cuando pulsa Enter entonces navega', () => {
    const set = renderControles();
    const input = screen.getByLabelText('Ir a la página');
    fireEvent.change(input, { target: { value: '4' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(set).toHaveBeenCalledWith(4);
  });

  it('dado número fuera de rango en Ir a cuando sale del campo entonces no navega', () => {
    const set = renderControles();
    const input = screen.getByLabelText('Ir a la página');
    fireEvent.change(input, { target: { value: '9' } });
    fireEvent.blur(input);
    expect(set).not.toHaveBeenCalled();
  });

  it('dado total y carga cuando renderiza entonces muestra el total, el indicador y bloquea la navegación', () => {
    renderControles({ total: 300, cargando: true });
    expect(screen.getByText(/300 registros/)).toBeInTheDocument();
    expect(screen.getByLabelText('Cargando')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /anterior/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /siguiente/i })).toBeDisabled();
  });

  it('dado una etiqueta de total cuando renderiza entonces la usa', () => {
    renderControles({ total: 12, etiquetaTotal: 'movimientos' });
    expect(screen.getByText(/12 movimientos/)).toBeInTheDocument();
  });
});
