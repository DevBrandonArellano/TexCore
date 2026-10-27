/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): en reposo / cargando; ícono por defecto / propio.
 */
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { Upload } from 'lucide-react';
import { IconoCarga } from './icono-carga';

describe('IconoCarga', () => {
  it('test_IconoCarga_dado_en_reposo_cuando_se_renderiza_entonces_muestra_el_icono_de_descarga_sin_girar', () => {
    const { container } = render(<IconoCarga cargando={false} />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('class')).toContain('lucide-download');
    expect(svg.getAttribute('class')).not.toContain('animate-spin');
  });

  it('test_IconoCarga_dado_cargando_cuando_se_renderiza_entonces_muestra_un_spinner_que_gira_y_oculto_a_lectores', () => {
    const { container } = render(<IconoCarga cargando />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('class')).toContain('animate-spin');
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(container.querySelector('[data-testid="icono-cargando"]')).not.toBeNull();
  });

  it('test_IconoCarga_dado_icono_propio_y_tamano_cuando_esta_en_reposo_entonces_los_respeta', () => {
    const { container } = render(<IconoCarga cargando={false} icono={Upload} className="w-3 h-3" />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('class')).toContain('lucide-upload');
    expect(svg.getAttribute('class')).toContain('w-3 h-3');
  });
});
