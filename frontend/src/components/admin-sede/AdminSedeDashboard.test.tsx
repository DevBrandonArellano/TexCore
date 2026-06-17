import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AdminSedeDashboard } from './AdminSedeDashboard';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

// Mocks
vi.mock('axios', () => {
  const mockAxiosInstance = { 
    get: vi.fn(() => Promise.resolve({ data: [] })), 
    post: vi.fn(() => Promise.resolve({ data: [] })), 
    patch: vi.fn(() => Promise.resolve({ data: [] })), 
    delete: vi.fn(() => Promise.resolve({ data: [] })), 
    put: vi.fn(() => Promise.resolve({ data: [] })),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() }
    }
  };
  return {
    default: {
      ...mockAxiosInstance,
      create: vi.fn(() => mockAxiosInstance)
    }
  };
});

// Mock Auth
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: { user: { id: 1, role: 'admin' } } })
}));

// Mock ResizeObserver for Radix UI
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
global.HTMLElement.prototype.scrollIntoView = vi.fn();
global.HTMLElement.prototype.hasPointerCapture = vi.fn();
global.HTMLElement.prototype.releasePointerCapture = vi.fn();

describe('AdminSedeDashboard Smoke Test', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () => render(
    <BrowserRouter>
      <AdminSedeDashboard />
    </BrowserRouter>
  );

  it('se renderiza sin crashear', async () => {
    // Si crashea lanzará una excepción. Con el render basta para validar humo.
    expect(() => renderComponent()).not.toThrow();
  });
});
