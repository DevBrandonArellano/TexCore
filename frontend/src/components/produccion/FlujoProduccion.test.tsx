import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { FlujoProduccion } from './FlujoProduccion';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({ toast: { error: (...args: any[]) => toastErrorMock(...args) } }));

const ORDEN_SIN_ETAPAS = {
  id: 1,
  codigo: 'OP-0001',
  estado: 'pendiente',
  area: { id: 1, nombre: 'Tintura' },
  peso_neto_requerido: 100,
  producto_entrada: { descripcion: 'Hilo crudo' },
  lotes: [],
};

const ORDEN_CON_ETAPAS = {
  id: 2,
  codigo: 'OP-0002',
  estado: 'en_proceso',
  area: { id: 2, nombre: 'Empaque' },
  peso_neto_requerido: 200,
  producto_entrada: { descripcion: 'Tela procesada' },
  lotes: [{ codigo_lote: 'L1', peso_neto_producido: 80 }],
};

const ETAPA = {
  id: 5,
  area: 2,
  nombre: 'Empacado',
  orden: 1,
  maquina: { nombre: 'Empacadora 1' },
  bodega_entrada: { nombre: 'Bodega PT' },
  bodega_salida: { nombre: 'Bodega Final' },
};

function mockFetch(ordenes: any[], etapas: any[] = []) {
  mockGet.mockImplementation((url: string) => {
    if (url === '/ordenes-produccion/') return Promise.resolve({ data: { results: ordenes } });
    if (url === '/etapas-produccion/') return Promise.resolve({ data: { results: etapas } });
    return Promise.resolve({ data: { results: [] } });
  });
}

describe('FlujoProduccion', () => {
  beforeEach(() => {
    mockGet.mockReset();
    toastErrorMock.mockReset();
  });

  it('dado carga inicial cuando monta entonces muestra estado de carga', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<FlujoProduccion />);
    expect(screen.getByText('Cargando flujo...')).toBeInTheDocument();
  });

  it('dado sin ordenes cuando carga entonces muestra mensaje vacio', async () => {
    mockFetch([]);
    render(<FlujoProduccion />);
    await waitFor(() => expect(screen.getByText('No hay órdenes de producción')).toBeInTheDocument());
  });

  it('dado error al cargar cuando falla el fetch entonces muestra toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    render(<FlujoProduccion />);
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar flujo de producción'));
  });

  it('dado ordenes sin etapas configuradas cuando carga entonces muestra la orden sin timeline de etapas', async () => {
    mockFetch([ORDEN_SIN_ETAPAS]);
    render(<FlujoProduccion />);

    await waitFor(() => expect(screen.getByText('OP-0001')).toBeInTheDocument());
    expect(screen.getByText('PENDIENTE')).toBeInTheDocument();
    expect(screen.getByText('Tintura')).toBeInTheDocument();
    expect(screen.getByText('0 / 100 kg')).toBeInTheDocument();
  });

  it('dado orden con etapas configuradas para su area cuando carga entonces muestra el timeline de etapas', async () => {
    mockFetch([ORDEN_CON_ETAPAS], [ETAPA]);
    render(<FlujoProduccion />);

    await waitFor(() => expect(screen.getByText('OP-0002')).toBeInTheDocument());
    expect(screen.getByText('EN_PROCESO')).toBeInTheDocument();
    expect(screen.getByText('80 / 200 kg')).toBeInTheDocument();
    expect(screen.getByText('1. Empacado')).toBeInTheDocument();
    expect(screen.getByText('Empacadora 1')).toBeInTheDocument();
    expect(screen.getByText('Bodega PT')).toBeInTheDocument();
    expect(screen.getByText('Bodega Final')).toBeInTheDocument();
  });

  it('dado mas de 10 ordenes cuando carga entonces solo muestra las primeras 10', async () => {
    const muchasOrdenes = Array.from({ length: 15 }, (_, i) => ({
      ...ORDEN_SIN_ETAPAS,
      id: i + 1,
      codigo: `OP-${String(i + 1).padStart(4, '0')}`,
    }));
    mockFetch(muchasOrdenes);
    render(<FlujoProduccion />);

    await waitFor(() => expect(screen.getByText('OP-0001')).toBeInTheDocument());
    expect(screen.queryByText('OP-0011')).not.toBeInTheDocument();
  });
});
