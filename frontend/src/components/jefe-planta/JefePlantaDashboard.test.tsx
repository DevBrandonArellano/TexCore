import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { JefePlantaDashboard } from './JefePlantaDashboard';
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
import apiClient from '../../lib/axios';

// Mock ResizeObserver for Radix UI
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

describe('JefePlantaDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mocking API responses for Dashboard Data Fetching
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/ordenes-produccion/') {
        return Promise.resolve({ data: [
          { id: 1, codigo: 'OP-001', estado: 'pendiente', peso_neto_requerido: 100, peso_producido: 0 },
          { id: 2, codigo: 'OP-002', estado: 'en_proceso', peso_neto_requerido: 200, peso_producido: 100 }
        ]});
      }
      if (url === '/productos/') return Promise.resolve({ data: [] });
      if (url === '/formula-colors/') return Promise.resolve({ data: [] });
      if (url === '/sedes/') return Promise.resolve({ data: [] });
      if (url === '/maquinas/') return Promise.resolve({ data: [] });
      if (url === '/areas/') return Promise.resolve({ data: [] });
      if (url === '/bodegas/') return Promise.resolve({ data: [] });
      if (url === '/users/') return Promise.resolve({ data: [] });
      
      return Promise.resolve({ data: [] });
    });
  });

  const renderComponent = () => render(
    <BrowserRouter>
      <JefePlantaDashboard />
    </BrowserRouter>
  );

  it('debe renderizar el título del dashboard y cargar datos', async () => {
    renderComponent();
    
    // Verifica que muestra el título
    expect(screen.getByText('Panel de Jefe de Planta')).toBeInTheDocument();
    
    // Espera a que los KPIs se rendericen basados en la data mockeada
    await waitFor(() => {
      expect(screen.getByText('Pendientes')).toBeInTheDocument();
    });
    
    // También valida que OP-001 aparezca
    expect(screen.getByText('OP-001')).toBeInTheDocument();
    expect(screen.getByText('OP-002')).toBeInTheDocument();
  });
});
