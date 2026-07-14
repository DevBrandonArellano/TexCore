import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TrazabilidadProducto } from './TrazabilidadProducto';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

vi.mock('./RegistrarTransformacion', () => ({
  RegistrarTransformacion: ({ open }: any) => (open ? <div>registrar-transformacion-dialog</div> : null),
}));

const NIVEL_SIN_PASOS = {
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

const NIVEL_CON_PASOS_Y_SIGUIENTE = {
  orden_codigo: 'OP-0001',
  area: 'Tintura',
  merma_total: '15.000',
  merma_porcentaje: '15.00',
  producto_inicial: { codigo: 'HILO-001' },
  producto_final: { codigo: 'TELA-002' },
  peso_inicial: '100.000',
  peso_final: '85.000',
  pasos: [
    {
      numero_secuencia: 1,
      producto_entrada: { codigo: 'HILO-001' },
      producto_salida: { codigo: 'TELA-002' },
      maquina: 'Tintura 1',
      operario: 'Ana Pérez',
      peso_entrada: '100.000',
      peso_salida: '85.000',
      merma: '15.000',
      estado: 'completada',
    },
  ],
  siguiente: {
    orden_codigo: 'OP-0002',
    area: 'Empaque',
    merma_total: '0.000',
    merma_porcentaje: '0.00',
    producto_inicial: { codigo: 'TELA-002' },
    producto_final: { codigo: 'TELA-002' },
    peso_inicial: '85.000',
    peso_final: '85.000',
    pasos: [],
    siguiente: null,
  },
};

describe('TrazabilidadProducto', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('dado carga inicial cuando monta entonces muestra estado de carga', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<TrazabilidadProducto ordenId={1} />);
    expect(screen.getByText('Cargando trazabilidad…')).toBeInTheDocument();
  });

  it('dado error al cargar cuando falla el fetch entonces muestra mensaje de error', async () => {
    mockGet.mockRejectedValue(new Error('500'));
    render(<TrazabilidadProducto ordenId={1} />);
    await waitFor(() => expect(
      screen.getByText('No se pudo cargar la trazabilidad de la orden.'),
    ).toBeInTheDocument());
  });

  it('dado nivel sin pasos cuando carga entonces muestra el mensaje de sin transformaciones', async () => {
    mockGet.mockResolvedValueOnce({ data: NIVEL_SIN_PASOS });
    render(<TrazabilidadProducto ordenId={1} />);
    await waitFor(() => expect(screen.getByText('OP-0001')).toBeInTheDocument());
    expect(screen.getByText('Sin transformaciones registradas todavía.')).toBeInTheDocument();
  });

  it('dado nivel con pasos y siguiente area cuando carga entonces renderiza ambos niveles encadenados', async () => {
    mockGet.mockResolvedValueOnce({ data: NIVEL_CON_PASOS_Y_SIGUIENTE });
    render(<TrazabilidadProducto ordenId={1} />);

    await waitFor(() => expect(screen.getAllByText('OP-0001')[0]).toBeInTheDocument());
    expect(screen.getByText('Tintura 1 · Ana Pérez · 100.000 → 85.000 kg')).toBeInTheDocument();
    expect(screen.getByText('OP-0002')).toBeInTheDocument(); // nivel siguiente encadenado
    expect(screen.getByText(/Merma 15\.000 kg/)).toBeInTheDocument();
  });

  it('dado click en actualizar cuando se presiona entonces vuelve a cargar la trazabilidad', async () => {
    mockGet.mockResolvedValue({ data: NIVEL_SIN_PASOS });
    render(<TrazabilidadProducto ordenId={1} />);
    await waitFor(() => expect(screen.getByText('OP-0001')).toBeInTheDocument());

    mockGet.mockClear();
    await userEvent.click(screen.getByText('Actualizar'));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/ordenes-produccion/1/trazabilidad/'));
  });

  it('dado allowRegister en false cuando renderiza entonces no muestra el boton de registrar', async () => {
    mockGet.mockResolvedValueOnce({ data: NIVEL_SIN_PASOS });
    render(<TrazabilidadProducto ordenId={1} />);
    await waitFor(() => expect(screen.getByText('OP-0001')).toBeInTheDocument());
    expect(screen.queryByText('Registrar transformación')).not.toBeInTheDocument();
  });

  it('dado allowRegister en true cuando carga entonces trae maquinas y productos y muestra el boton', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/trazabilidad/')) return Promise.resolve({ data: NIVEL_SIN_PASOS });
      if (url === '/maquinas/') return Promise.resolve({ data: [{ id: 1, nombre: 'M1' }] });
      if (url === '/productos/') return Promise.resolve({ data: { results: [{ id: 1, codigo: 'P1' }] } });
      return Promise.resolve({ data: {} });
    });

    render(<TrazabilidadProducto ordenId={1} allowRegister />);

    await waitFor(() => expect(screen.getByText('Registrar transformación')).toBeInTheDocument());
  });

  it('dado allowRegister en true cuando se hace click en registrar entonces abre el dialogo', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/trazabilidad/')) return Promise.resolve({ data: NIVEL_SIN_PASOS });
      return Promise.resolve({ data: [] });
    });

    render(<TrazabilidadProducto ordenId={1} allowRegister />);
    await waitFor(() => expect(screen.getByText('Registrar transformación')).toBeInTheDocument());

    await userEvent.click(screen.getByText('Registrar transformación'));

    expect(screen.getByText('registrar-transformacion-dialog')).toBeInTheDocument();
  });
});
