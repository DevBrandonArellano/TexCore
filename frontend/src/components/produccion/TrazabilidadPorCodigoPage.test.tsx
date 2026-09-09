import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { TrazabilidadPorCodigoPage } from './TrazabilidadPorCodigoPage';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

const NIVEL = {
  orden_codigo: 'OP-0001',
  area: 'Tintura',
  merma_total: '0.000',
  merma_porcentaje: '0.00',
  producto_inicial: { codigo: 'HILO-001' },
  producto_final: { codigo: 'HILO-001' },
  peso_inicial: '100.000',
  peso_final: '100.000',
  pasos: [],
  siguiente: null,
};

function renderPagina(codigo = 'LOT-0001') {
  return render(
    <MemoryRouter initialEntries={[`/trazabilidad/${codigo}`]}>
      <Routes>
        <Route path="/trazabilidad/:codigo" element={<TrazabilidadPorCodigoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TrazabilidadPorCodigoPage', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('dado carga inicial cuando monta entonces consulta por el codigo de la URL', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    renderPagina('LOT-0001');
    expect(mockGet).toHaveBeenCalledWith('/trazabilidad-lote/LOT-0001/');
    expect(screen.getByText('Cargando trazabilidad…')).toBeInTheDocument();
  });

  it('dado codigo existente cuando carga entonces muestra la trazabilidad de la orden', async () => {
    mockGet.mockResolvedValueOnce({ data: NIVEL });
    renderPagina('LOT-0001');
    await waitFor(() => expect(screen.getByText('OP-0001')).toBeInTheDocument());
  });

  it('dado codigo inexistente cuando falla con 404 entonces muestra mensaje especifico', async () => {
    mockGet.mockRejectedValueOnce({ response: { status: 404 } });
    renderPagina('NO-EXISTE');
    await waitFor(() => expect(
      screen.getByText('No se encontró ningún lote con el código "NO-EXISTE".'),
    ).toBeInTheDocument());
  });

  it('dado error de servidor cuando falla el fetch entonces muestra mensaje generico', async () => {
    mockGet.mockRejectedValueOnce({ response: { status: 500 } });
    renderPagina('LOT-0001');
    await waitFor(() => expect(
      screen.getByText('No se pudo cargar la trazabilidad de este lote.'),
    ).toBeInTheDocument());
  });
});
