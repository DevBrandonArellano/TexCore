import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FichaLoteDialog } from './FichaLoteDialog';
import { pestanasParaRol } from './pestanasFichaLote';

const mockRole = { current: 'jefe_planta' as string | null };
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({ profile: mockRole.current ? { role: mockRole.current } : null }),
}));

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({ default: { get: (...args: unknown[]) => mockGet(...args) } }));

const FICHA = {
  lote_codigo: 'LOT-1', producto: 'Hilo rojo', peso_neto: 95, peso_merma: 5, tipo_merma: 'Máquina',
  calidad: 'Primera', operario: 'op1', maquina: 'TIN-01',
  fechas: { inicio: '2026-09-29T08:00:00Z', final: '2026-09-29T16:00:00Z' },
  orden_produccion: { codigo: 'OP-1', formula_color: 'Rojo' },
  quimicos_consumidos: [{ quimico: 'Sal', cantidad_total_op_kg: 12.5, fase: 'TINTURA' }],
};
const MOVIMIENTOS = {
  lote_codigo: 'LOT-1', producto: 'Hilo rojo',
  historial: [{ id: 1, fecha: '2026-09-29T16:00:00Z', tipo_movimiento: 'Producción', bodega_origen: '-',
    bodega_destino: 'PT', cantidad: 95, documento_ref: null, usuario: 'Sistema' }],
};
const MATERIAS = {
  lote_final: 'LOT-1', producto_final: 'Hilo rojo', cantidad_producida: 95, costo_total_materias_primas: 120,
  fecha_produccion: null, clasificacion_calidad: 'primera',
  componentes: [{ materia_prima_lote: 'PROV-7', producto: 'Algodón', proveedor: 'Hilados SA', cantidad_kg: 100,
    costo_unitario: 1.2, costo_total: 120, certificado: null, numero_documento: 'FAC-1',
    fecha_recepcion: '2026-09-01', porcentaje_utilizado: 100 }],
};

const CONSUMO = { id: 1, lote_produccion: 3, lote_origen: 8, lote_origen_codigo: 'LOT-ORIGEN-8',
  cantidad_consumida: '40.000', genera_nuevo_lote: true };
const COSTO = {
  id: 1, lote_produccion: 3, lote_codigo: 'LOT-1', costo_materia_prima: '120.000', costo_quimicos: '15.500',
  costo_operario: '8.000', costo_maquina: '6.500', otros_costos: '0.000', total_costo: '150.000',
  precio_venta_esperado: '200.000', margen_bruto: '50.000', margen_bruto_pct: '25.00',
  calculado_en: '2026-10-01T10:00:00Z', recalculado_en: '2026-10-01T10:00:00Z',
};

function responder(url: string) {
  if (url.endsWith('/genealogia/')) return Promise.resolve({ data: FICHA });
  if (url.includes('/movimientos/')) return Promise.resolve({ data: MOVIMIENTOS });
  if (url.startsWith('/trazabilidad/')) return Promise.resolve({ data: MATERIAS });
  if (url.startsWith('/consumo-lote-detalle/')) return Promise.resolve({ data: { count: 1, results: [CONSUMO] } });
  if (url.endsWith('/obtener-costo/')) return Promise.resolve({ data: COSTO });
  return Promise.resolve({ data: { nodo_raiz: null, ancestros: [], descendientes: [], aristas: [] } });
}

const LOTE = { id: 3, codigo_lote: 'LOT-1' };

describe('pestanasParaRol', () => {
  it.each([
    ['operario', ['resumen', 'genealogia', 'consumos']],
    ['empaquetado', ['resumen', 'movimientos', 'consumos']],
    ['bodeguero', ['resumen', 'movimientos', 'consumos', 'materias-primas', 'costo']],
    ['jefe_planta', ['resumen', 'genealogia', 'movimientos', 'consumos', 'materias-primas', 'costo']],
    [null, ['resumen', 'consumos']],
  ])('dado rol %s cuando filtra entonces muestra solo las pestañas que su endpoint permite', (rol, esperado) => {
    expect(pestanasParaRol(rol).map((p) => p.id)).toEqual(esperado);
  });
});

describe('FichaLoteDialog', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockGet.mockImplementation(responder);
    mockRole.current = 'jefe_planta';
  });

  it('dado lote nulo cuando renderiza entonces no abre ni consulta', () => {
    render(<FichaLoteDialog lote={null} onClose={vi.fn()} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado lote cuando abre entonces carga solo la pestaña Resumen', async () => {
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    expect(await screen.findByText('Hilo rojo')).toBeInTheDocument();
    expect(screen.getByText('Sal')).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(1);
    expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/3/genealogia/');
  });

  it('dado cambio a Movimientos cuando se activa entonces carga y muestra el kárdex del lote', async () => {
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    await screen.findByText('Hilo rojo');
    await userEvent.click(screen.getByRole('tab', { name: 'Movimientos' }));
    expect(await screen.findByText('Producción')).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith('/inventory/lotes/LOT-1/movimientos/');
  });

  it('dado cambio a Materias primas cuando se activa entonces muestra proveedores y costo total', async () => {
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    await screen.findByText('Hilo rojo');
    await userEvent.click(screen.getByRole('tab', { name: 'Materias primas y costos' }));
    expect(await screen.findByText('Hilados SA')).toBeInTheDocument();
    expect(screen.getByText('FAC-1')).toBeInTheDocument();
  });

  it('dado cambio a Genealogía cuando se activa entonces consulta el grafo hacia atrás del lote', async () => {
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    await screen.findByText('Hilo rojo');
    await userEvent.click(screen.getByRole('tab', { name: 'Genealogía' }));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/corridas-produccion/trazabilidad-lote/', {
      params: { codigo: 'LOT-1', direccion: 'atras' },
    }));
  });

  it('dado un componente con certificado cuando muestra materias primas entonces enlaza el certificado', async () => {
    const conCertificado = { ...MATERIAS, componentes: [{ ...MATERIAS.componentes[0], certificado: '/media/cert.pdf' }] };
    mockGet.mockImplementation((url: string) =>
      url.startsWith('/trazabilidad/') ? Promise.resolve({ data: conCertificado }) : responder(url));
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    await screen.findByText('Hilo rojo');
    await userEvent.click(screen.getByRole('tab', { name: 'Materias primas y costos' }));
    const enlace = await screen.findByRole('link', { name: 'Ver' });
    expect(enlace).toHaveAttribute('href', '/media/cert.pdf');
    expect(enlace).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('dado movimientos vacíos cuando se activa entonces muestra el mensaje de vacío', async () => {
    mockGet.mockImplementation((url: string) =>
      url.includes('/movimientos/') ? Promise.resolve({ data: { ...MOVIMIENTOS, historial: [] } }) : responder(url));
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    await screen.findByText('Hilo rojo');
    await userEvent.click(screen.getByRole('tab', { name: 'Movimientos' }));
    expect(await screen.findByText(/no tiene movimientos/)).toBeInTheDocument();
  });

  it('dado error del servidor en el resumen cuando abre entonces muestra la alerta', async () => {
    mockGet.mockRejectedValueOnce({ response: { status: 404, data: {} } });
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('dado cierre del diálogo cuando pulsa cerrar entonces avisa al contenedor', async () => {
    const onClose = vi.fn();
    render(<FichaLoteDialog lote={LOTE} onClose={onClose} />);
    await screen.findByText('Hilo rojo');
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('dado cambio a Consumos cuando se activa entonces lista los lotes de origen consumidos', async () => {
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Consumos' }));
    expect(await screen.findByText('LOT-ORIGEN-8')).toBeInTheDocument();
    expect(screen.getByText('40.000')).toBeInTheDocument();
  });

  it('dado cambio a Costo cuando se activa entonces muestra el desglose, el total y el margen', async () => {
    render(<FichaLoteDialog lote={LOTE} onClose={vi.fn()} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Costo' }));
    expect(await screen.findByText('150.000')).toBeInTheDocument();
    expect(screen.getByText('120.000')).toBeInTheDocument();
    expect(screen.getByText(/25\.00 ?%/)).toBeInTheDocument();
  });
});

