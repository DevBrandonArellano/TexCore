import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useIsMobile } from './use-mobile';

function mockMatchMedia() {
  const listeners: Array<() => void> = [];
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    addEventListener: (_: string, cb: () => void) => listeners.push(cb),
    removeEventListener: (_: string, cb: () => void) => {
      const idx = listeners.indexOf(cb);
      if (idx >= 0) listeners.splice(idx, 1);
    },
  }));
  return { fireChange: () => listeners.forEach((cb) => cb()) };
}

describe('useIsMobile', () => {
  beforeEach(() => {
    mockMatchMedia();
  });

  it('dado un ancho de escritorio cuando monta entonces retorna false', () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1200 });
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it('dado un ancho movil cuando monta entonces retorna true', () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 400 });
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it('dado un cambio de tamaño cuando dispara el evento change entonces actualiza el valor', () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1200 });
    const { fireChange } = mockMatchMedia();
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);

    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 500 });
    act(() => {
      fireChange();
    });
    expect(result.current).toBe(true);
  });
});
