import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TransformationView } from './TransformationView';
import { Producto, Bodega } from '../../lib/types';

const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: {
    post: (...args: any[]) => mockPost(...args),
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}>
      <div>{children}</div>
    </SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const PRODUCTOS: Producto[] = [
  { id: 1, codigo: 'LANA-CRUDA', descripcion: 'Lana Cruda', tipo: 'materia_prima', unidad_medida: 'kg', stock_minimo: 0, precio_base: 0 },
  { id: 2, codigo: 'LANA-TINT', descripcion: 'Lana Tinturada', tipo: 'materia_prima', unidad_medida: 'kg', stock_minimo: 0, precio_base: 0 },
];

const BODEGAS: Bodega[] = [
  { id: 10, nombre: 'Bodega Cruda', sede: 1 },
  { id: 20, nombre: 'Bodega Tinturada', sede: 1 },
];

function origenSection() {
  return screen.getByText('Origen').closest('div') as HTMLElement;
}
function destinoSection() {
  return screen.getByText('Destino (Transformado)').closest('div') as HTMLElement;
}

async function seleccionarOrigen(bodegaNombre: string, productoDescripcion: string) {
  await userEvent.click(within(origenSection()).getByText(bodegaNombre));
  await userEvent.click(within(origenSection()).getByText(productoDescripcion));
}

async function seleccionarDestino(bodegaNombre: string, productoDescripcion: string) {
  await userEvent.click(within(destinoSection()).getByText(bodegaNombre));
  await userEvent.click(within(destinoSection()).getByText(productoDescripcion));
}

async function completarFormulario({
  cantidad = '5',
  justificacion = 'Cambio de código por proceso de tinturado',
}: { cantidad?: string; justificacion?: string } = {}) {
  await seleccionarOrigen('Bodega Cruda', 'Lana Cruda');
  await seleccionarDestino('Bodega Tinturada', 'Lana Tinturada');
  await userEvent.type(screen.getByPlaceholderText('0.00'), cantidad);
  await userEvent.type(
    screen.getByPlaceholderText('Ej: Cambio de código por proceso de tinturado Lote #...'),
    justificacion,
  );
}

describe('TransformationView', () => {
  beforeEach(() => {
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado sin productos ni bodegas cuando renderiza entonces muestra los selects vacios y sin stock disponible', () => {
    render(<TransformationView productos={[]} bodegas={[]} stock={[]} />);

    expect(screen.getAllByText('Selecciona bodega')).toHaveLength(2);
    expect(screen.getByText('No hay stock disponible')).toBeInTheDocument();
    expect(screen.getAllByText('Cargando catálogo o sin resultados...')).toHaveLength(2);
  });

  it('dado stock existente cuando se selecciona bodega y producto origen entonces filtra los lotes disponibles', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: 'L1', lote_id: 5, lote_codigo: 'LOTE-5', cantidad: '10.00' },
      { id: 2, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Tinturada', bodega_id: 20, lote: 'L2', lote_id: 6, lote_codigo: 'LOTE-6', cantidad: '20.00' },
      { id: 3, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: null, lote_id: null, lote_codigo: null, cantidad: '0.00' },
    ];
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await seleccionarOrigen('Bodega Cruda', 'Lana Cruda');

    expect(screen.getByText('LOTE-5 (10.00 disp.)')).toBeInTheDocument();
    expect(screen.queryByText('LOTE-6 (20.00 disp.)')).not.toBeInTheDocument();
    expect(screen.getByText('Sin Lote (General)')).toBeInTheDocument();
  });

  it('dado formulario vacio cuando se envia entonces muestra error de campos obligatorios y no llama a la API', async () => {
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={[]} />);

    await userEvent.click(screen.getByText('Registrar Transformación'));

    expect(toastErrorMock).toHaveBeenCalledWith('Todos los campos son obligatorios, incluyendo la justificación.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado producto sin stock disponible cuando se envia entonces muestra error de stock y no llama a la API', async () => {
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={[]} />);

    await completarFormulario();
    await userEvent.click(screen.getByText('Registrar Transformación'));

    expect(toastErrorMock).toHaveBeenCalledWith('No hay stock disponible para el producto/lote seleccionado.');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado cantidad mayor al stock disponible cuando se envia entonces muestra error de stock insuficiente', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: null, lote_id: null, lote_codigo: null, cantidad: '3.00' },
    ];
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await completarFormulario({ cantidad: '5' });
    await userEvent.click(screen.getByText('Registrar Transformación'));

    expect(toastErrorMock).toHaveBeenCalledWith('Stock insuficiente. Disponible: 3.00');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado datos validos sin lote especifico cuando se envia entonces registra la transformacion con lote_origen_id nulo', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: null, lote_id: null, lote_codigo: null, cantidad: '10.00' },
    ];
    mockPost.mockResolvedValueOnce({ data: {} });
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await completarFormulario({ cantidad: '5', justificacion: 'Cambio de código por tinturado' });
    await userEvent.click(screen.getByText('Registrar Transformación'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/inventory/transformaciones/', {
      bodega_origen_id: 10,
      bodega_destino_id: 20,
      producto_origen_id: 1,
      producto_destino_id: 2,
      lote_origen_id: null,
      nuevo_lote_codigo: '',
      cantidad: 5,
      _justificacion_auditoria: 'Cambio de código por tinturado',
    }));
    expect(toastSuccessMock).toHaveBeenCalledWith('Transformación realizada con éxito.');
  });

  it('dado un lote especifico seleccionado cuando se envia entonces envia su id numerico', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: 'L5', lote_id: 5, lote_codigo: 'LOTE-5', cantidad: '10.00' },
    ];
    mockPost.mockResolvedValueOnce({ data: {} });
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await seleccionarOrigen('Bodega Cruda', 'Lana Cruda');
    await userEvent.click(within(origenSection()).getByText('LOTE-5 (10.00 disp.)'));
    await seleccionarDestino('Bodega Tinturada', 'Lana Tinturada');
    await userEvent.type(screen.getByPlaceholderText('0.00'), '4');
    await userEvent.type(
      screen.getByPlaceholderText('Ej: Cambio de código por proceso de tinturado Lote #...'),
      'Cambio con lote especifico',
    );
    await userEvent.click(screen.getByText('Registrar Transformación'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/inventory/transformaciones/', expect.objectContaining({
      lote_origen_id: 5,
      cantidad: 4,
    })));
  });

  it('dado un lote "Sin Lote (General)" seleccionado explicitamente cuando se envia entonces envia lote_origen_id nulo', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: null, lote_id: null, lote_codigo: null, cantidad: '10.00' },
    ];
    mockPost.mockResolvedValueOnce({ data: {} });
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await seleccionarOrigen('Bodega Cruda', 'Lana Cruda');
    await userEvent.click(within(origenSection()).getByText('Sin Lote (General)'));
    await seleccionarDestino('Bodega Tinturada', 'Lana Tinturada');
    await userEvent.type(screen.getByPlaceholderText('0.00'), '4');
    await userEvent.type(
      screen.getByPlaceholderText('Ej: Cambio de código por proceso de tinturado Lote #...'),
      'Cambio sin lote explicito',
    );
    await userEvent.click(screen.getByText('Registrar Transformación'));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/inventory/transformaciones/', expect.objectContaining({
      lote_origen_id: null,
    })));
  });

  it('dado error de la API con mensaje cuando falla el envio entonces muestra el mensaje de error del backend', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: null, lote_id: null, lote_codigo: null, cantidad: '10.00' },
    ];
    mockPost.mockRejectedValueOnce({ response: { data: { error: 'Stock bloqueado por auditoría' } } });
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await completarFormulario();
    await userEvent.click(screen.getByText('Registrar Transformación'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error', { description: 'Stock bloqueado por auditoría' }));
  });

  it('dado error de la API sin mensaje especifico cuando falla el envio entonces muestra el mensaje generico', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: null, lote_id: null, lote_codigo: null, cantidad: '10.00' },
    ];
    mockPost.mockRejectedValueOnce(new Error('network error'));
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await completarFormulario();
    await userEvent.click(screen.getByText('Registrar Transformación'));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error', { description: 'Error al procesar la transformación.' }));
  });

  it('dado envio exitoso cuando termina entonces limpia el formulario', async () => {
    const stock = [
      { id: 1, producto: 'Lana Cruda', producto_id: 1, bodega: 'Bodega Cruda', bodega_id: 10, lote: null, lote_id: null, lote_codigo: null, cantidad: '10.00' },
    ];
    mockPost.mockResolvedValueOnce({ data: {} });
    render(<TransformationView productos={PRODUCTOS} bodegas={BODEGAS} stock={stock} />);

    await completarFormulario();
    await userEvent.click(screen.getByText('Registrar Transformación'));

    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Transformación realizada con éxito.'));
    expect(screen.getByPlaceholderText('0.00')).toHaveValue(null);
    expect(screen.getByPlaceholderText('Ej: Cambio de código por proceso de tinturado Lote #...')).toHaveValue('');
  });
});
