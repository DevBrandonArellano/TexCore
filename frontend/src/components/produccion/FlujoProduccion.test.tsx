/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): carga inicial / sin ordenes / error al cargar / ordenes sin etapas
 *   configuradas / orden con etapas configuradas para su area.
 * - Caja blanca (CB): ramas de error — error al cargar; el componente se desmonta antes de la respuesta.
 * - EP: respuestas sin paginar; estados finalizada / desconocido; orden sin lotes; dos etapas ordenadas.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import { FlujoProduccion } from './FlujoProduccion';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({ toast: { error: (...args: unknown[]) => toastErrorMock(...args) } }));

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

function mockFetch(ordenes: unknown[], etapas: unknown[] = []) {
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

  it('dado respuestas sin paginar y orden finalizada sin lotes cuando carga entonces las muestra', async () => {
    mockGet.mockImplementation((url: string) => Promise.resolve({
      data: url === '/ordenes-produccion/' ? [{ ...ORDEN_SIN_ETAPAS, estado: 'finalizada', lotes: undefined }] : [],
    }));
    render(<FlujoProduccion />);
    await waitFor(() => expect(screen.getByText('FINALIZADA')).toBeInTheDocument());
    expect(screen.getByText('0 / 100 kg')).toBeInTheDocument();
  });

  it('dado estado desconocido cuando carga entonces lo muestra sin icono de estado', async () => {
    mockFetch([{ ...ORDEN_SIN_ETAPAS, estado: 'cancelada' }]);
    render(<FlujoProduccion />);
    const badge = await screen.findByText('CANCELADA');
    expect(badge.querySelector('svg')).toBeNull();
  });

  it('dado dos etapas desordenadas del area cuando carga entonces las ordena y une con una flecha', async () => {
    const segunda = { ...ETAPA, id: 6, orden: 2, nombre: 'Paletizado' };
    mockFetch([ORDEN_CON_ETAPAS], [segunda, ETAPA]);
    render(<FlujoProduccion />);
    const primera = await screen.findByText('1. Empacado');
    const posterior = screen.getByText('2. Paletizado');
    expect(primera.compareDocumentPosition(posterior) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(document.querySelectorAll('.lucide-arrow-down')).toHaveLength(1);
  });

  it('dado desmontaje antes de la respuesta cuando llega o falla entonces no avisa ni actualiza', async () => {
    let fallar: (e: Error) => void = () => {};
    mockGet.mockReturnValue(new Promise((_r, rej) => { fallar = rej; }));
    const { unmount } = render(<FlujoProduccion />);
    unmount();
    await act(async () => { fallar(new Error('red')); });
    expect(toastErrorMock).not.toHaveBeenCalled();
  });
});

