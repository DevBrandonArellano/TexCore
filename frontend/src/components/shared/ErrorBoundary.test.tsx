import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

function Bomb(): React.ReactElement {
  throw new Error('boom');
}

function Sano() {
  return <p>Contenido hijo</p>;
}

describe('ErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('dado un hijo que renderiza correctamente cuando se monta entonces muestra el contenido sin fallback', () => {
    render(
      <ErrorBoundary>
        <Sano />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Contenido hijo')).toBeInTheDocument();
    expect(screen.queryByText('Error al cargar')).not.toBeInTheDocument();
  });

  it('dado un hijo que lanza un error durante el render cuando se monta entonces captura el error y muestra el fallback por defecto', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Error al cargar')).toBeInTheDocument();
    expect(screen.getByText('boom')).toBeInTheDocument();
    expect(screen.queryByText('Contenido hijo')).not.toBeInTheDocument();
  });

  it('dado un fallback personalizado cuando un hijo lanza un error entonces renderiza el fallback en lugar del contenido por defecto', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary fallback={<p>Fallback personalizado</p>}>
        <Bomb />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Fallback personalizado')).toBeInTheDocument();
    expect(screen.queryByText('Error al cargar')).not.toBeInTheDocument();
  });
});
