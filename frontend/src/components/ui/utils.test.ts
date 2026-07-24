import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('cn', () => {
  it('dado clases simples cuando combina entonces las une con espacio', () => {
    expect(cn('a', 'b')).toBe('a b');
  });

  it('dado clases condicionales falsy cuando combina entonces las omite', () => {
    expect(cn('a', false && 'b', undefined, 'c')).toBe('a c');
  });

  it('dado clases tailwind en conflicto cuando combina entonces la ultima gana', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });

  it('dado un array de clases cuando combina entonces las aplana', () => {
    expect(cn(['a', 'b'], 'c')).toBe('a b c');
  });
});
