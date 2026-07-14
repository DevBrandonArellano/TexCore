import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// jsdom no implementa estas APIs que Radix UI (dialogs, selects, popovers)
// usa activamente. Centralizado aquí para no duplicarlo en cada *.test.tsx.
global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
};

global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

if (!window.matchMedia) {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    }));
}
