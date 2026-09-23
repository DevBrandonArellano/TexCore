import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { Button } from './button';

describe('Button', () => {
  it('dado un ref cuando se renderiza entonces se adjunta al elemento button del DOM', () => {
    const ref = createRef<HTMLButtonElement>();
    render(<Button ref={ref}>Click</Button>);

    // Button se usa como hijo `asChild` de triggers de Radix (DropdownMenu,
    // Select, Dialog, Tooltip) que dependen de este ref para calcular la
    // posición del contenido flotante (@floating-ui). Sin forwardRef, React
    // descarta el ref silenciosamente y el popover queda fuera de pantalla
    // sin ningún error visible en consola.
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    expect(ref.current).toBe(screen.getByRole('button', { name: 'Click' }));
  });

  it('dado asChild con un elemento nativo cuando se renderiza entonces el ref llega al elemento real', () => {
    const ref = createRef<HTMLAnchorElement>();
    render(
      <Button asChild ref={ref as any}>
        <a href="/somewhere">Link</a>
      </Button>
    );

    expect(ref.current).toBeInstanceOf(HTMLAnchorElement);
  });
});
