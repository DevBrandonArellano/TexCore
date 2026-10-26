import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// jsdom no implementa estas APIs que Radix UI (dialogs, selects, popovers)
// usa activamente. Centralizado aquí para no duplicarlo en cada *.test.tsx.
global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
};

// Node >= 25 expone su propio `localStorage` global (Web Storage de Node) que,
// sin --localstorage-file, no tiene métodos y tapa al de jsdom:
// "window.localStorage.clear is not a function". CI usa Node 24 y no lo ve, así
// que se garantiza un Storage en memoria completo para cualquier versión de Node.
class MemoryStorage implements Storage {
    private datos = new Map<string, string>();
    get length() { return this.datos.size; }
    clear() { this.datos.clear(); }
    getItem(clave: string) { return this.datos.has(clave) ? this.datos.get(clave)! : null; }
    key(indice: number) { return Array.from(this.datos.keys())[indice] ?? null; }
    removeItem(clave: string) { this.datos.delete(clave); }
    setItem(clave: string, valor: string) { this.datos.set(clave, String(valor)); }
}
for (const nombre of ['localStorage', 'sessionStorage'] as const) {
    if (typeof window[nombre]?.clear !== 'function') {
        Object.defineProperty(window, nombre, { value: new MemoryStorage(), configurable: true, writable: true });
    }
}

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
