import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ImageWithFallback } from './ImageWithFallback';

describe('ImageWithFallback', () => {
  it('dado un src y alt válidos cuando se renderiza entonces muestra la imagen normal con esos valores', () => {
    render(<ImageWithFallback src="https://example.com/foto.png" alt="Foto de prueba" />);

    const img = screen.getByRole('img', { name: 'Foto de prueba' });
    expect(img).toHaveAttribute('src', 'https://example.com/foto.png');
    expect(img).toHaveAttribute('alt', 'Foto de prueba');
  });

  it('dado que la imagen falla al cargar cuando se dispara el evento error entonces se muestra el placeholder con data-original-url apuntando al src original', () => {
    const originalSrc = 'https://example.com/no-existe.png';
    render(<ImageWithFallback src={originalSrc} alt="Foto de prueba" />);

    const img = screen.getByRole('img', { name: 'Foto de prueba' });
    fireEvent.error(img);

    const fallbackImg = screen.getByAltText('Error loading image');
    expect(fallbackImg).toBeInTheDocument();
    expect(fallbackImg).toHaveAttribute('data-original-url', originalSrc);
    expect(screen.queryByAltText('Foto de prueba')).not.toBeInTheDocument();
  });

  it('dado un className cuando la imagen se renderiza normalmente entonces la clase se aplica al elemento img', () => {
    render(
      <ImageWithFallback
        src="https://example.com/foto.png"
        alt="Foto de prueba"
        className="mi-clase-custom"
      />
    );

    const img = screen.getByRole('img', { name: 'Foto de prueba' });
    expect(img).toHaveClass('mi-clase-custom');
  });

  it('dado un className cuando la imagen falla al cargar entonces la clase se aplica al contenedor del fallback', () => {
    render(
      <ImageWithFallback
        src="https://example.com/no-existe.png"
        alt="Foto de prueba"
        className="mi-clase-custom"
      />
    );

    const img = screen.getByRole('img', { name: 'Foto de prueba' });
    fireEvent.error(img);

    const fallbackImg = screen.getByAltText('Error loading image');
    const wrapper = fallbackImg.parentElement?.parentElement;
    expect(wrapper).toHaveClass('mi-clase-custom');
  });
});
