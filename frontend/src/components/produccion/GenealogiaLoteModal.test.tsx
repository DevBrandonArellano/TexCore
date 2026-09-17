import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { GenealogiaLoteModal } from './GenealogiaLoteModal';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
  },
}));

const DATA_ATRAS = {
  nodo_raiz: {
    id: 10,
    codigo_lote: 'LOT-TERM-001',
    producto_codigo: 'TEL-ALGODON',
    producto_descripcion: 'Tela Algodón Jersey',
    producto_tipo: 'producto_terminado',
    peso_neto_producido: '150.000',
    clasificacion_calidad: 'PRIMERA',
    orden_produccion_codigo: 'OP-2026-100',
  },
  ancestros: [
    {
      id: 5,
      codigo_lote: 'LOT-HILO-001',
      producto_codigo: 'HILO-20',
      producto_descripcion: 'Hilo 20/1 Crudo',
      producto_tipo: 'producto_intermedio',
      peso_neto_producido: '160.000',
      clasificacion_calidad: 'PRIMERA',
      orden_produccion_codigo: 'OP-2026-050',
    },
  ],
  aristas: [
    {
      padre_id: 5,
      padre_codigo: 'LOT-HILO-001',
      hijo_id: 10,
      hijo_codigo: 'LOT-TERM-001',
      cantidad_usada: '155.000',
      corrida_codigo: 'CORR-01',
      maquina: 'Telar Circular Mayer',
      operario: 'Juan Perez',
    },
  ],
  materias_primas_origen: [
    {
      id: 1,
      lote_proveedor: 'PROV-MP-99',
      proveedor_nombre: 'Hilandería Central S.A.',
      producto_codigo: 'MP-ALGODON-FIBRA',
      fecha_recepcion: '2026-09-01',
      numero_documento_entrada: 'FAC-8899',
      asociado_a_lote_codigo: 'LOT-HILO-001',
    },
  ],
  total_ancestros: 1,
  total_materias_primas: 1,
};

const DATA_ADELANTE = {
  nodo_raiz: {
    id: 5,
    codigo_lote: 'LOT-HILO-001',
    producto_codigo: 'HILO-20',
    producto_descripcion: 'Hilo 20/1 Crudo',
    producto_tipo: 'producto_intermedio',
    peso_neto_producido: '160.000',
    clasificacion_calidad: 'PRIMERA',
  },
  descendientes: [
    {
      id: 10,
      codigo_lote: 'LOT-TERM-001',
      producto_codigo: 'TEL-ALGODON',
      producto_descripcion: 'Tela Algodón Jersey',
      producto_tipo: 'producto_terminado',
      peso_neto_producido: '150.000',
    },
  ],
  aristas: [],
  despachos_clientes: [
    {
      lote_id: 10,
      lote_codigo: 'LOT-TERM-001',
      pedido_codigo: 'PED-2026-77',
      cliente_nombre: 'Confecciones Textiles S.A.',
      cliente_ruc: '1790011223001',
      peso_despachado: '150.000',
      fecha_despacho: '2026-09-15T14:30:00',
    },
  ],
  total_descendientes: 1,
  total_clientes_afectados: 1,
};

describe('GenealogiaLoteModal', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('dado loteCodigo cuando abre modal entonces consulta api con direccion atras por defecto y muestra ancestros y materias primas', async () => {
    mockGet.mockResolvedValueOnce({ data: DATA_ATRAS });

    render(
      <GenealogiaLoteModal
        open={true}
        loteCodigo="LOT-TERM-001"
        onOpenChange={vi.fn()}
      />
    );

    expect(screen.getByText('Cargando grafo de genealogía...')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/corridas-produccion/trazabilidad-lote/', {
        params: { codigo: 'LOT-TERM-001', direccion: 'atras' },
      });
    });

    await waitFor(() => {
      // Raíz
      expect(screen.getAllByText('LOT-TERM-001').length).toBeGreaterThanOrEqual(1);
      // Ancestros
      expect(screen.getByText('LOT-HILO-001')).toBeInTheDocument();
      expect(screen.getByText('Telar Circular Mayer')).toBeInTheDocument();
      // Materia prima
      expect(screen.getByText('Hilandería Central S.A.')).toBeInTheDocument();
      expect(screen.getByText(/FAC-8899/)).toBeInTheDocument();
    });
  });

  it('dado cambio de tab a adelante cuando cambia direccion entonces consulta api con direccion adelante y muestra recall de clientes', async () => {
    mockGet.mockResolvedValueOnce({ data: DATA_ATRAS });
    mockGet.mockResolvedValueOnce({ data: DATA_ADELANTE });

    render(
      <GenealogiaLoteModal
        open={true}
        loteCodigo="LOT-HILO-001"
        onOpenChange={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getAllByText('LOT-TERM-001').length).toBeGreaterThanOrEqual(1);
    });

    // Cambiar a Trace-Forward (Recall)
    const tabRecall = screen.getByRole('tab', { name: /Trace-Forward/i });
    fireEvent.click(tabRecall);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/corridas-produccion/trazabilidad-lote/', {
        params: { codigo: 'LOT-HILO-001', direccion: 'adelante' },
      });
    });

    await waitFor(() => {
      expect(screen.getByText('Confecciones Textiles S.A.')).toBeInTheDocument();
      expect(screen.getByText(/1790011223001/)).toBeInTheDocument();
      expect(screen.getByText(/Atención Recall:/)).toBeInTheDocument();
    });
  });

  it('dado error de backend cuando falla la consulta entonces muestra mensaje de error', async () => {
    mockGet.mockRejectedValueOnce({
      response: { data: { error: 'No existe un lote de producción con código LOT-ERR.' } },
    });

    render(
      <GenealogiaLoteModal
        open={true}
        loteCodigo="LOT-ERR"
        onOpenChange={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/No existe un lote de producción con código LOT-ERR/)).toBeInTheDocument();
    });
  });
});
