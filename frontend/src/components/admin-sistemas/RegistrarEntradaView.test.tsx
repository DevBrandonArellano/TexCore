import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RegistrarEntradaView } from './RegistrarEntradaView';

const mockRegistrar = vi.fn();
vi.mock('../../lib/api/inventarioApi', () => ({
  inventarioApi: { registrarEntradaMateriaPrima: (...a: unknown[]) => mockRegistrar(...a) },
}));

const mockToast = { success: vi.fn(), error: vi.fn() };
vi.mock('sonner', () => ({ toast: { success: (...a: unknown[]) => mockToast.success(...a), error: (...a: unknown[]) => mockToast.error(...a) } }));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));
vi.mock('../ui/product-select', () => ({
  ProductSelect: ({ onValueChange }: any) => (
    <button type="button" onClick={() => onValueChange('1')}>elegir-producto</button>
  ),
}));
vi.mock('../ui/searchable-select', () => ({
  SearchableSelect: ({ id, items, options, onValueChange }: any) => (
    <button type="button" onClick={() => onValueChange(items?.[0]?.value ?? options?.[0])}>elegir-{id}</button>
  ),
}));

const PROPS = {
  productos: [{ id: 1, codigo: 'MP-1', descripcion: 'Algodón', tipo: 'materia_prima' }] as any,
  bodegas: [{ id: 5, nombre: 'Bodega MP', sede: 1 }],
  proveedores: [{ id: 3, nombre: 'Hilos del Sur' }],
  onDataRefresh: vi.fn(),
};

function llenarObligatorios() {
  fireEvent.click(screen.getByText('elegir-recepcion-proveedor'));
  fireEvent.click(screen.getByText('elegir-producto'));
  fireEvent.click(screen.getByText('Bodega MP'));
  fireEvent.change(screen.getByLabelText('Lote del proveedor'), { target: { value: 'LP-2026-07' } });
  fireEvent.change(screen.getByLabelText('Cantidad (kg)'), { target: { value: '100' } });
  fireEvent.change(screen.getByLabelText('Costo unitario'), { target: { value: '2.5' } });
  fireEvent.change(screen.getByLabelText('Fecha de recepción'), { target: { value: '2026-09-30' } });
}

describe('RegistrarEntradaView (recepción F0-001)', () => {
  beforeEach(() => {
    mockRegistrar.mockReset();
    mockToast.success.mockReset();
    mockToast.error.mockReset();
    PROPS.onDataRefresh.mockReset();
  });

  it('dado campos obligatorios vacíos cuando envía entonces avisa y no llama a la API', () => {
    render(<RegistrarEntradaView {...PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: 'Registrar recepción' }));
    expect(mockToast.error).toHaveBeenCalled();
    expect(mockRegistrar).not.toHaveBeenCalled();
  });

  it('dado datos completos y certificado cuando envía entonces registra la recepción y limpia el formulario', async () => {
    mockRegistrar.mockResolvedValue({ id: 9, lote_proveedor: 'LP-2026-07' });
    render(<RegistrarEntradaView {...PROPS} />);
    llenarObligatorios();
    fireEvent.change(screen.getByLabelText('N.º de documento'), { target: { value: 'FAC-123' } });
    fireEvent.click(screen.getByText('elegir-recepcion-pais'));
    fireEvent.click(screen.getByText('Primera'));
    const archivo = new File(['pdf'], 'cert.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByLabelText('Certificado de calidad'), { target: { files: [archivo] } });

    fireEvent.click(screen.getByRole('button', { name: 'Registrar recepción' }));

    await waitFor(() => expect(PROPS.onDataRefresh).toHaveBeenCalled());
    expect(mockRegistrar).toHaveBeenCalledWith(expect.objectContaining({
      proveedor: 3, producto: 1, bodega_recepcion: 5, lote_proveedor: 'LP-2026-07',
      cantidad_kg: '100', costo_unitario: '2.5', fecha_recepcion: '2026-09-30',
      numero_documento_entrada: 'FAC-123', calidad: 'Primera', certificado_calidad: archivo,
    }));
    expect(mockRegistrar.mock.calls[0][0].pais).toBeTruthy();
    expect(mockToast.success).toHaveBeenCalled();
    expect((screen.getByLabelText('Lote del proveedor') as HTMLInputElement).value).toBe('');
  });

  it('dado error del servidor cuando envía entonces lo muestra y no refresca', async () => {
    mockRegistrar.mockRejectedValue({
      response: { status: 400, data: { error: { message: 'bodega_recepcion: No encontrado.' } } },
    });
    render(<RegistrarEntradaView {...PROPS} />);
    llenarObligatorios();
    fireEvent.click(screen.getByRole('button', { name: 'Registrar recepción' }));
    await waitFor(() => expect(mockToast.error).toHaveBeenCalled());
    expect(String(mockToast.error.mock.calls[0][0])).toContain('No encontrado');
    expect(PROPS.onDataRefresh).not.toHaveBeenCalled();
  });
});
